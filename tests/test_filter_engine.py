"""
Unit tests for the filter engine service.

Tests the filter pipeline, progressive relaxation, and edge cases.
"""

import pytest
import pandas as pd

from backend.services.filter_engine import (
    filter_restaurants,
    _filter_location,
    _filter_budget,
    _filter_cuisine,
    _filter_rating,
)
from backend.models.schemas import RecommendationRequest


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Create a small test DataFrame mimicking the Zomato dataset."""
    return pd.DataFrame({
        "restaurant_name": [
            "Pizza Palace", "Curry House", "Sushi Bar",
            "Burger Joint", "Taco Bell", "Pasta Point",
            "Dosa Corner", "Noodle Box", "Steak Place",
        ],
        "location": [
            "Koramangala", "Koramangala", "Indiranagar",
            "Bellandur", "Bellandur", "Koramangala",
            "Whitefield", "Indiranagar", "Koramangala",
        ],
        "cuisines": [
            "italian, pizza", "north indian, chinese", "japanese, sushi",
            "american, burgers", "mexican", "italian, continental",
            "south indian", "chinese, thai", "continental, steak",
        ],
        "average_cost_for_two": [
            800, 500, 1500, 400, 300, 1200, 200, 600, 2000,
        ],
        "aggregate_rating": [
            4.2, 4.5, 4.0, 3.8, 3.5, 4.3, 4.1, 3.9, 4.6,
        ],
        "votes": [
            300, 500, 200, 150, 100, 400, 250, 180, 350,
        ],
        "restaurant_type": [
            "Casual Dining", "Casual Dining", "Fine Dining",
            "Quick Bites", "Quick Bites", "Casual Dining",
            "Quick Bites", "Casual Dining", "Fine Dining",
        ],
        "online_order": [
            "Yes", "Yes", "No", "Yes", "Yes", "No", "Yes", "Yes", "No",
        ],
        "book_table": [
            "Yes", "No", "Yes", "No", "No", "Yes", "No", "No", "Yes",
        ],
    })


# ── Helper Filter Tests ───────────────────────────────────────────

class TestFilterLocation:
    def test_exact_match(self, sample_df):
        result = _filter_location(sample_df, "Koramangala")
        assert len(result) == 4  # Pizza Palace, Curry House, Pasta Point, Steak Place

    def test_case_insensitive(self, sample_df):
        result = _filter_location(sample_df, "koramangala")
        assert len(result) == 4

    def test_partial_match(self, sample_df):
        result = _filter_location(sample_df, "Bellandu")
        assert len(result) == 2  # Bellandur partial match

    def test_no_match(self, sample_df):
        result = _filter_location(sample_df, "Timbuktu")
        assert len(result) == 0


class TestFilterBudget:
    def test_low_budget(self, sample_df):
        result = _filter_budget(sample_df, (0, 500))
        # 500, 400, 300, 200 → 4 restaurants
        assert len(result) == 4

    def test_medium_budget(self, sample_df):
        result = _filter_budget(sample_df, (501, 1500))
        # 800, 1500, 1200, 600 → 4 restaurants
        assert len(result) == 4

    def test_high_budget(self, sample_df):
        result = _filter_budget(sample_df, (1501, 50000))
        # 2000 → 1 restaurant
        assert len(result) == 1


class TestFilterCuisine:
    def test_single_cuisine(self, sample_df):
        result = _filter_cuisine(sample_df, "italian")
        assert len(result) == 2  # Pizza Palace, Pasta Point

    def test_multi_cuisine_or(self, sample_df):
        result = _filter_cuisine(sample_df, "italian, chinese")
        # Pizza Palace, Curry House, Pasta Point, Noodle Box
        assert len(result) == 4

    def test_case_insensitive(self, sample_df):
        result = _filter_cuisine(sample_df, "JAPANESE")
        assert len(result) == 1

    def test_empty_cuisine(self, sample_df):
        result = _filter_cuisine(sample_df, "")
        assert len(result) == len(sample_df)

    def test_no_match(self, sample_df):
        result = _filter_cuisine(sample_df, "ethiopian")
        assert len(result) == 0


class TestFilterRating:
    def test_high_threshold(self, sample_df):
        result = _filter_rating(sample_df, 4.5)
        assert len(result) == 2  # Curry House (4.5), Steak Place (4.6)

    def test_low_threshold(self, sample_df):
        result = _filter_rating(sample_df, 3.0)
        assert len(result) == len(sample_df)

    def test_zero_threshold(self, sample_df):
        result = _filter_rating(sample_df, 0.0)
        assert len(result) == len(sample_df)


# ── Integration Filter Tests ─────────────────────────────────────

class TestFilterRestaurants:
    """Test the full filter_restaurants pipeline with the real dataset."""

    def test_basic_filter(self):
        """Test that filter_restaurants returns a FilterResult with valid data."""
        request = RecommendationRequest(
            location="Koramangala",
            budget="medium",
            min_rating=3.0,
        )
        result = filter_restaurants(request)
        assert result.total_matches >= 0
        assert isinstance(result.filters_applied, dict)
        assert "location" in result.filters_applied
        assert "budget" in result.filters_applied

    def test_bellandur_medium(self):
        """Test the Bellandur + medium budget filter (known good query)."""
        request = RecommendationRequest(
            location="Bellandur",
            budget="medium",
            min_rating=4.0,
        )
        result = filter_restaurants(request)
        assert result.total_matches > 0
        assert all(result.df["aggregate_rating"] >= 4.0)

    def test_nonexistent_location(self):
        """Test that a nonexistent location triggers relaxation."""
        request = RecommendationRequest(
            location="Timbuktu",
            budget="medium",
            min_rating=3.0,
        )
        result = filter_restaurants(request)
        # Should either have 0 results or have a relaxation notice
        assert result.total_matches == 0 or result.relaxation_notice is not None

    def test_results_sorted_by_rating(self):
        """Verify that results are sorted by rating descending."""
        request = RecommendationRequest(
            location="Koramangala",
            budget="medium",
            min_rating=3.0,
        )
        result = filter_restaurants(request)
        if result.total_matches > 1:
            ratings = result.df["aggregate_rating"].tolist()
            assert ratings == sorted(ratings, reverse=True)

    def test_max_shortlist_cap(self):
        """Verify results are capped at MAX_SHORTLIST."""
        from backend.config import settings
        request = RecommendationRequest(
            location="Koramangala",
            budget="medium",
            min_rating=0.0,  # Very low to get many results
        )
        result = filter_restaurants(request)
        assert result.total_matches <= settings.MAX_SHORTLIST
