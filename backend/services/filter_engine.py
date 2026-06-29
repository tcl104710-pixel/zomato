"""
Filter engine service.

Applies user preference filters (location, budget, cuisine, rating)
to the restaurant dataset and returns a shortlisted DataFrame.

Implements progressive relaxation when too few results are found.
"""

import logging
from dataclasses import dataclass, field

import pandas as pd

from backend.config import settings
from backend.models.schemas import RecommendationRequest
from backend.services.data_loader import get_dataframe

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of the filter pipeline."""

    df: pd.DataFrame
    filters_applied: dict = field(default_factory=dict)
    total_matches: int = 0
    relaxation_notice: str | None = None


def filter_restaurants(request: RecommendationRequest) -> FilterResult:
    """
    Apply sequential filters to the dataset based on user preferences.

    Filter order: location -> budget -> cuisine -> rating
    If fewer than 3 results remain, progressively relax constraints.

    Returns a FilterResult containing the shortlisted DataFrame and metadata.
    """
    df = get_dataframe().copy()
    budget_range = settings.BUDGET_RANGES.get(request.budget, (0, 50000))

    filters_applied = {
        "location": request.location,
        "budget": request.budget,
        "budget_range": list(budget_range),
        "cuisine": request.cuisine,
        "min_rating": request.min_rating,
    }

    # --- Apply filters sequentially ---
    result_df = _apply_all_filters(df, request, budget_range)

    relaxation_notice = None

    # --- Progressive relaxation if too few results ---
    if len(result_df) < 3:
        logger.info(
            f"Only {len(result_df)} results found. Attempting progressive relaxation."
        )
        result_df, relaxation_notice = _relax_filters(
            df, request, budget_range
        )

    # Sort by rating descending, then by votes descending
    result_df = result_df.sort_values(
        by=["aggregate_rating", "votes"],
        ascending=[False, False],
    )

    # Ensure unique restaurants in the final result
    result_df = result_df.drop_duplicates(subset=["restaurant_name"], keep="first")

    # Cap at MAX_SHORTLIST
    if len(result_df) > settings.MAX_SHORTLIST:
        result_df = result_df.head(settings.MAX_SHORTLIST)

    total_matches = len(result_df)
    logger.info(f"Filter result: {total_matches} restaurants shortlisted")

    return FilterResult(
        df=result_df.reset_index(drop=True),
        filters_applied=filters_applied,
        total_matches=total_matches,
        relaxation_notice=relaxation_notice,
    )


def _apply_all_filters(
    df: pd.DataFrame,
    request: RecommendationRequest,
    budget_range: tuple[int, int],
) -> pd.DataFrame:
    """Apply all four filters sequentially."""
    df = _filter_location(df, request.location)
    df = _filter_budget(df, budget_range)
    if request.cuisine:
        df = _filter_cuisine(df, request.cuisine)
    df = _filter_rating(df, request.min_rating)
    return df


def _relax_filters(
    df: pd.DataFrame,
    request: RecommendationRequest,
    budget_range: tuple[int, int],
) -> tuple[pd.DataFrame, str]:
    """
    Progressively relax constraints to find more results.

    Relaxation order:
        1. Drop cuisine filter
        2. Widen budget by one tier
        3. Lower min_rating by 0.5
    """
    notices = []

    # Step 1: Drop cuisine filter
    result = _filter_location(df, request.location)
    result = _filter_budget(result, budget_range)
    result = _filter_rating(result, request.min_rating)

    if len(result) >= 3:
        if request.cuisine:
            notices.append(
                f"Cuisine '{request.cuisine}' filter was relaxed to show more results."
            )
        return result, " ".join(notices) if notices else None

    # Step 2: Widen budget (use full range)
    notices.append("Budget filter was relaxed to show more results.")
    result = _filter_location(df, request.location)
    result = _filter_rating(result, request.min_rating)

    if len(result) >= 3:
        return result, " ".join(notices)

    # Step 3: Lower rating threshold
    relaxed_rating = max(0.0, request.min_rating - 0.5)
    notices.append(
        f"Minimum rating was lowered from {request.min_rating} to {relaxed_rating}."
    )
    result = _filter_location(df, request.location)
    result = _filter_rating(result, relaxed_rating)

    if len(result) >= 3:
        return result, " ".join(notices)

    # Step 4: Location only (last resort)
    result = _filter_location(df, request.location)
    if len(result) == 0:
        notices.append(
            f"No restaurants found in '{request.location}'. "
            "The dataset may not cover this area."
        )
    return result, " ".join(notices)


def _filter_location(df: pd.DataFrame, location: str) -> pd.DataFrame:
    """Filter by location using case-insensitive partial match."""
    location_lower = location.strip().lower()
    mask = df["location"].str.lower().str.contains(location_lower, na=False)
    filtered = df[mask]
    logger.debug(f"Location filter '{location}': {len(filtered)} results")
    return filtered


def _filter_budget(
    df: pd.DataFrame, budget_range: tuple[int, int]
) -> pd.DataFrame:
    """Filter by cost range (inclusive boundaries)."""
    low, high = budget_range
    mask = (df["average_cost_for_two"] >= low) & (df["average_cost_for_two"] <= high)
    filtered = df[mask]
    logger.debug(f"Budget filter [{low}-{high}]: {len(filtered)} results")
    return filtered


def _filter_cuisine(df: pd.DataFrame, cuisine: str) -> pd.DataFrame:
    """
    Filter by cuisine using case-insensitive substring match.

    Supports multi-cuisine queries like "italian, chinese" (OR logic).
    """
    cuisines_requested = [c.strip().lower() for c in cuisine.split(",") if c.strip()]

    if not cuisines_requested:
        return df

    # Match any of the requested cuisines (OR logic)
    mask = pd.Series(False, index=df.index)
    for c in cuisines_requested:
        mask = mask | df["cuisines"].str.lower().str.contains(c, na=False)

    filtered = df[mask]
    logger.debug(f"Cuisine filter '{cuisine}': {len(filtered)} results")
    return filtered


def _filter_rating(df: pd.DataFrame, min_rating: float) -> pd.DataFrame:
    """Filter restaurants with rating >= min_rating."""
    mask = df["aggregate_rating"] >= min_rating
    filtered = df[mask]
    logger.debug(f"Rating filter >= {min_rating}: {len(filtered)} results")
    return filtered
