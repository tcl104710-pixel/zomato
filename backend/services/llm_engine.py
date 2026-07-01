"""
Groq LLM recommendation engine.

Constructs prompts from user preferences and filtered restaurants,
calls the Groq API, and parses ranked recommendations.

Includes retry logic and graceful fallback to sorted results when
the LLM is unavailable or returns malformed output.
"""

import json
import logging
import time
from typing import Optional

import pandas as pd
from groq import Groq, APIError, APIConnectionError, RateLimitError

from backend.config import settings
from backend.models.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RestaurantRecommendation,
)

logger = logging.getLogger(__name__)

# Maximum retries for transient failures
_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2

# System prompt for the LLM
_SYSTEM_PROMPT = (
    "You are a strict JSON data formatter. You rank restaurants based on how well they match user preferences. "
    "Respond ONLY in valid JSON. The 'restaurant_name' field MUST contain ONLY the exact name of the restaurant from the provided list, with NO conversational text. "
    "Put all conversational explanations in the 'explanation' and 'summary' fields."
)


def _build_prompt(
    request: RecommendationRequest,
    filtered_df: pd.DataFrame,
    top_n: int,
) -> str:
    """
    Build the user prompt from preferences and the filtered restaurant list.

    Formats each restaurant as a numbered entry with all relevant details
    so the LLM has sufficient context for ranking.
    """
    # Format the restaurant shortlist
    restaurant_lines = []
    for idx, row in filtered_df.iterrows():
        entry = (
            f"{idx + 1}. {row['restaurant_name']} "
            f"| Location: {row['location']} "
            f"| Cuisines: {row['cuisines']} "
            f"| Rating: {row['aggregate_rating']}/5 "
            f"| Cost for Two: Rs.{row['average_cost_for_two']:.0f} "
            f"| Votes: {row['votes']}"
        )
        # Include optional fields if available
        if pd.notna(row.get("restaurant_type")) and row["restaurant_type"]:
            entry += f" | Type: {row['restaurant_type']}"
        if pd.notna(row.get("online_order")) and row["online_order"]:
            entry += f" | Online Order: {row['online_order']}"
        if pd.notna(row.get("book_table")) and row["book_table"]:
            entry += f" | Table Booking: {row['book_table']}"
        restaurant_lines.append(entry)

    formatted_restaurants = "\n".join(restaurant_lines)

    # Build the user prompt
    prompt = f"""The user is looking for a restaurant with the following preferences:
- Location: {request.location}
- Budget: {request.budget}
- Cuisine: {request.cuisine or "Any"}
- Minimum Rating: {request.min_rating}
- Additional Preferences: {request.additional_preferences or "None"}

Here are the {len(filtered_df)} matching restaurants:
{formatted_restaurants}

Please:
1. Rank the top {top_n} restaurants that best match the user's preferences.
2. For each restaurant, explain WHY it is a good fit in 1-2 sentences.
3. Provide a brief summary at the end comparing the top picks.

Respond ONLY in this exact JSON format:
{{
  "recommendations": [
    {{
      "rank": 1,
      "restaurant_name": "...",
      "cuisine": "...",
      "rating": 4.5,
      "estimated_cost_for_two": 1200.0,
      "explanation": "..."
    }}
  ],
  "summary": "..."
}}"""
    return prompt


def _parse_llm_response(
    raw_content: str,
    filtered_df: pd.DataFrame,
    top_n: int,
) -> tuple[list[RestaurantRecommendation], str]:
    """
    Parse the LLM's JSON response into structured recommendations.

    Returns (recommendations_list, summary_string).
    Raises ValueError if the JSON is malformed or missing required fields.
    """
    data = json.loads(raw_content)

    recommendations = []
    raw_recs = data.get("recommendations", [])

    for rec_data in raw_recs[:top_n]:
        # Validate that the restaurant exists in our filtered set
        name = rec_data.get("restaurant_name", "Unknown")

        recommendations.append(
            RestaurantRecommendation(
                rank=rec_data.get("rank", len(recommendations) + 1),
                restaurant_name=name,
                cuisine=rec_data.get("cuisine", "Unknown"),
                rating=float(rec_data.get("rating", 0.0)),
                estimated_cost_for_two=float(
                    rec_data.get("estimated_cost_for_two", 0.0)
                ),
                explanation=rec_data.get(
                    "explanation", "Recommended based on your preferences."
                ),
            )
        )

    summary = data.get(
        "summary",
        f"Here are the top {len(recommendations)} restaurants matching your preferences.",
    )

    if not recommendations:
        raise ValueError("LLM returned empty recommendations list.")

    return recommendations, summary


def _build_fallback_response(
    filtered_df: pd.DataFrame,
    top_n: int,
) -> tuple[list[RestaurantRecommendation], str]:
    """
    Build a fallback response from the filtered DataFrame when the LLM
    is unavailable or returns unusable output.

    Returns restaurants sorted by rating descending (already sorted
    by the filter engine).
    """
    recommendations = []
    for idx, row in filtered_df.head(top_n).iterrows():
        recommendations.append(
            RestaurantRecommendation(
                rank=len(recommendations) + 1,
                restaurant_name=row["restaurant_name"],
                cuisine=row.get("cuisines", "Unknown"),
                rating=row.get("aggregate_rating", 0.0),
                estimated_cost_for_two=row.get("average_cost_for_two", 0.0),
                explanation=(
                    f"{row['restaurant_name']} in {row['location']} offers "
                    f"{row.get('cuisines', 'various')} cuisine with a rating of "
                    f"{row.get('aggregate_rating', 0.0)}/5."
                ),
            )
        )

    summary = (
        f"Showing top {len(recommendations)} restaurants sorted by rating. "
        "(AI ranking was unavailable; results are based on ratings only.)"
    )

    return recommendations, summary


def _call_groq_api(prompt: str, retry: int = 0) -> str:
    """
    Call the Groq chat completions API with retry logic.

    Returns the raw response content string.
    Raises on permanent failures after exhausting retries.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=settings.GROQ_API_KEY)

    try:
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        content = completion.choices[0].message.content
        if not content or not content.strip():
            raise ValueError("LLM returned empty content.")
        return content

    except RateLimitError as e:
        if retry < _MAX_RETRIES:
            delay = _RETRY_DELAY_SECONDS * (retry + 1)
            logger.warning(
                f"Groq rate limited (429). Retrying in {delay}s "
                f"(attempt {retry + 1}/{_MAX_RETRIES})..."
            )
            time.sleep(delay)
            return _call_groq_api(prompt, retry=retry + 1)
        logger.error(f"Groq rate limit exceeded after {_MAX_RETRIES} retries: {e}")
        raise

    except APIConnectionError as e:
        if retry < _MAX_RETRIES:
            delay = _RETRY_DELAY_SECONDS * (retry + 1)
            logger.warning(
                f"Groq connection error. Retrying in {delay}s "
                f"(attempt {retry + 1}/{_MAX_RETRIES})..."
            )
            time.sleep(delay)
            return _call_groq_api(prompt, retry=retry + 1)
        logger.error(f"Groq API connection failed after {_MAX_RETRIES} retries: {e}")
        raise

    except APIError as e:
        logger.error(f"Groq API error: {e}")
        raise


def get_recommendations(
    request: RecommendationRequest,
    filtered_df: pd.DataFrame,
    top_n: Optional[int] = None,
) -> tuple[list[RestaurantRecommendation], str]:
    """
    Get LLM-ranked restaurant recommendations.

    Builds a prompt from user preferences and the filtered shortlist,
    calls the Groq API, and parses the response. Falls back to
    rating-sorted results if the LLM fails.

    Args:
        request: The user's recommendation request.
        filtered_df: Pre-filtered DataFrame from the filter engine.
        top_n: Number of recommendations to return (defaults to settings.TOP_N_RESULTS).

    Returns:
        Tuple of (recommendations_list, summary_string).
    """
    if top_n is None:
        top_n = settings.TOP_N_RESULTS

    # Build the prompt
    prompt = _build_prompt(request, filtered_df, top_n)
    logger.info(
        f"Built LLM prompt: {len(filtered_df)} restaurants, "
        f"requesting top {top_n}"
    )

    try:
        # Call the Groq API
        raw_response = _call_groq_api(prompt)
        logger.info("Groq API response received, parsing...")

        # Parse the JSON response
        try:
            recommendations, summary = _parse_llm_response(
                raw_response, filtered_df, top_n
            )
            logger.info(
                f"LLM returned {len(recommendations)} ranked recommendations"
            )
            return recommendations, summary

        except (json.JSONDecodeError, ValueError, KeyError) as parse_err:
            logger.warning(
                f"Failed to parse LLM response: {parse_err}. "
                "Retrying with stricter prompt..."
            )
            # Retry once with a stricter prompt suffix
            strict_prompt = (
                prompt + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Respond with ONLY a valid JSON object, no other text."
            )
            try:
                raw_retry = _call_groq_api(strict_prompt)
                recommendations, summary = _parse_llm_response(
                    raw_retry, filtered_df, top_n
                )
                logger.info(
                    f"Retry succeeded: {len(recommendations)} recommendations"
                )
                return recommendations, summary
            except Exception as retry_err:
                logger.error(
                    f"Retry also failed: {retry_err}. Falling back to sorted list."
                )

    except ValueError as e:
        # GROQ_API_KEY not configured
        logger.error(f"LLM service not configured: {e}")

    except (APIError, APIConnectionError, RateLimitError) as e:
        logger.error(f"Groq API unavailable: {e}. Falling back to sorted list.")

    except Exception as e:
        logger.error(f"Unexpected error in LLM engine: {e}. Using fallback.")

    # Fallback: return sorted results without LLM ranking
    logger.info("Using fallback: returning restaurants sorted by rating.")
    return _build_fallback_response(filtered_df, top_n)
