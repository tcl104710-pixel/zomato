"""
Tests for the LLM engine service.

Tests prompt construction, response parsing, and fallback behavior.
Uses mocked Groq API calls to avoid real API dependencies.
"""

import json
import pytest
import pandas as pd

from backend.services.llm_engine import (
    _build_prompt,
    _parse_llm_response,
    _build_fallback_response,
    get_recommendations,
)
from backend.models.schemas import RecommendationRequest, RestaurantRecommendation


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def sample_request():
    """Create a sample recommendation request."""
    return RecommendationRequest(
        location="Bellandur",
        budget="medium",
        cuisine="north indian",
        min_rating=4.0,
        additional_preferences="family-friendly",
    )


@pytest.fixture
def sample_request_minimal():
    """Create a minimal recommendation request (no cuisine, no prefs)."""
    return RecommendationRequest(
        location="Koramangala",
        budget="low",
    )


@pytest.fixture
def sample_df():
    """Create a sample filtered DataFrame."""
    return pd.DataFrame({
        "restaurant_name": ["Curry House", "Spice Garden", "Tandoor Express"],
        "location": ["Bellandur", "Bellandur", "Bellandur"],
        "cuisines": ["north indian, chinese", "north indian", "north indian, mughlai"],
        "average_cost_for_two": [800.0, 1200.0, 600.0],
        "aggregate_rating": [4.5, 4.2, 4.0],
        "votes": [500, 300, 200],
        "restaurant_type": ["Casual Dining", "Casual Dining", "Quick Bites"],
        "online_order": ["Yes", "No", "Yes"],
        "book_table": ["Yes", "Yes", "No"],
    })


@pytest.fixture
def valid_llm_response():
    """Create a valid LLM JSON response string."""
    return json.dumps({
        "recommendations": [
            {
                "rank": 1,
                "restaurant_name": "Curry House",
                "cuisine": "north indian, chinese",
                "rating": 4.5,
                "estimated_cost_for_two": 800.0,
                "explanation": "Highest rated with diverse cuisine options."
            },
            {
                "rank": 2,
                "restaurant_name": "Spice Garden",
                "cuisine": "north indian",
                "rating": 4.2,
                "estimated_cost_for_two": 1200.0,
                "explanation": "Great north Indian cuisine with table booking."
            },
        ],
        "summary": "Curry House leads with highest rating. Spice Garden is a solid alternative."
    })


# ── Prompt Building Tests ─────────────────────────────────────────

class TestBuildPrompt:
    def test_prompt_contains_location(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "Bellandur" in prompt

    def test_prompt_contains_budget(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "medium" in prompt

    def test_prompt_contains_cuisine(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "north indian" in prompt

    def test_prompt_contains_restaurants(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "Curry House" in prompt
        assert "Spice Garden" in prompt
        assert "Tandoor Express" in prompt

    def test_prompt_contains_restaurant_count(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "3 matching restaurants" in prompt

    def test_prompt_contains_additional_preferences(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "family-friendly" in prompt

    def test_prompt_any_cuisine_when_none(self, sample_request_minimal, sample_df):
        prompt = _build_prompt(sample_request_minimal, sample_df, top_n=5)
        assert "Any" in prompt

    def test_prompt_contains_json_format(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "JSON" in prompt
        assert "recommendations" in prompt

    def test_prompt_contains_ratings(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "4.5" in prompt
        assert "4.2" in prompt

    def test_prompt_contains_costs(self, sample_request, sample_df):
        prompt = _build_prompt(sample_request, sample_df, top_n=5)
        assert "800" in prompt
        assert "1200" in prompt


# ── Response Parsing Tests ────────────────────────────────────────

class TestParseResponse:
    def test_parse_valid_response(self, valid_llm_response, sample_df):
        recs, summary = _parse_llm_response(valid_llm_response, sample_df, top_n=5)
        assert len(recs) == 2
        assert isinstance(recs[0], RestaurantRecommendation)
        assert recs[0].rank == 1
        assert recs[0].restaurant_name == "Curry House"
        assert "Curry House leads" in summary

    def test_parse_respects_top_n(self, sample_df):
        response = json.dumps({
            "recommendations": [
                {"rank": i, "restaurant_name": f"R{i}", "cuisine": "x",
                 "rating": 4.0, "estimated_cost_for_two": 500, "explanation": "ok"}
                for i in range(1, 11)
            ],
            "summary": "Many options."
        })
        recs, _ = _parse_llm_response(response, sample_df, top_n=3)
        assert len(recs) == 3

    def test_parse_empty_recommendations_raises(self, sample_df):
        response = json.dumps({"recommendations": [], "summary": "None."})
        with pytest.raises(ValueError, match="empty"):
            _parse_llm_response(response, sample_df, top_n=5)

    def test_parse_invalid_json_raises(self, sample_df):
        with pytest.raises(json.JSONDecodeError):
            _parse_llm_response("not valid json", sample_df, top_n=5)

    def test_parse_missing_fields_uses_defaults(self, sample_df):
        response = json.dumps({
            "recommendations": [
                {"restaurant_name": "TestR"}  # Missing most fields
            ],
            "summary": "Test."
        })
        recs, _ = _parse_llm_response(response, sample_df, top_n=5)
        assert len(recs) == 1
        assert recs[0].restaurant_name == "TestR"
        assert recs[0].rating == 0.0  # Default
        assert recs[0].rank == 1  # Default

    def test_parse_default_summary(self, sample_df):
        response = json.dumps({
            "recommendations": [
                {"rank": 1, "restaurant_name": "R1", "cuisine": "x",
                 "rating": 4.0, "estimated_cost_for_two": 500, "explanation": "ok"}
            ]
            # No "summary" key
        })
        _, summary = _parse_llm_response(response, sample_df, top_n=5)
        assert "top 1" in summary.lower()


# ── Fallback Response Tests ───────────────────────────────────────

class TestFallbackResponse:
    def test_fallback_returns_sorted_by_rating(self, sample_df):
        recs, summary = _build_fallback_response(sample_df, top_n=3)
        assert len(recs) == 3
        assert recs[0].restaurant_name == "Curry House"  # Highest rating 4.5
        assert recs[1].restaurant_name == "Spice Garden"  # 4.2
        assert recs[2].restaurant_name == "Tandoor Express"  # 4.0

    def test_fallback_respects_top_n(self, sample_df):
        recs, _ = _build_fallback_response(sample_df, top_n=1)
        assert len(recs) == 1
        assert recs[0].restaurant_name == "Curry House"

    def test_fallback_summary_mentions_unavailable(self, sample_df):
        _, summary = _build_fallback_response(sample_df, top_n=3)
        assert "unavailable" in summary.lower()

    def test_fallback_ranks_sequential(self, sample_df):
        recs, _ = _build_fallback_response(sample_df, top_n=3)
        for i, rec in enumerate(recs):
            assert rec.rank == i + 1

    def test_fallback_includes_explanation(self, sample_df):
        recs, _ = _build_fallback_response(sample_df, top_n=3)
        for rec in recs:
            assert len(rec.explanation) > 0
            assert rec.restaurant_name in rec.explanation
