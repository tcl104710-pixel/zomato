"""
Pydantic request/response schemas for the recommendation API.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """User preferences for restaurant recommendations."""

    location: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="City area or locality (e.g., 'Indiranagar', 'Whitefield')",
    )
    budget: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Budget tier: low (0-500), medium (501-1500), high (1501+)",
    )
    cuisine: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Preferred cuisine (e.g., 'italian', 'chinese'). Optional.",
    )
    min_rating: float = Field(
        default=3.0,
        ge=0.0,
        le=5.0,
        description="Minimum acceptable rating (0.0 to 5.0)",
    )
    additional_preferences: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Free-text preferences (e.g., 'family-friendly, outdoor seating')",
    )


class RestaurantRecommendation(BaseModel):
    """A single restaurant recommendation from the LLM."""

    rank: int
    restaurant_name: str
    cuisine: str
    rating: float
    estimated_cost_for_two: float
    explanation: str


class RecommendationResponse(BaseModel):
    """Full response with ranked recommendations and metadata."""

    recommendations: list[RestaurantRecommendation]
    summary: str
    filters_applied: dict
    total_matches: int
    relaxation_notice: Optional[str] = None


class FilteredRestaurant(BaseModel):
    """A restaurant from the filtered dataset (before LLM ranking)."""

    restaurant_name: str
    location: str
    cuisines: str
    average_cost_for_two: float
    aggregate_rating: float
    votes: int
    restaurant_type: Optional[str] = None
    online_order: Optional[str] = None
    book_table: Optional[str] = None
