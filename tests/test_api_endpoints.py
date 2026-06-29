"""
Integration tests for FastAPI endpoints.

Tests health check, metadata endpoints, and the recommendation API.
Uses httpx.AsyncClient with the FastAPI test client.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health Endpoint ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_check(client):
    """Test that /api/health returns valid health status."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert "dataset" in data
    assert "llm" in data
    assert "version" in data


@pytest.mark.anyio
async def test_health_dataset_info(client):
    """Test that health check includes dataset details."""
    response = await client.get("/api/health")
    data = response.json()

    dataset = data["dataset"]
    assert "loaded" in dataset
    assert "total_restaurants" in dataset
    assert "total_locations" in dataset
    assert "total_cuisines" in dataset

    if dataset["loaded"]:
        assert dataset["total_restaurants"] > 0
        assert dataset["total_locations"] > 0


@pytest.mark.anyio
async def test_health_llm_info(client):
    """Test that health check includes LLM configuration."""
    response = await client.get("/api/health")
    data = response.json()

    llm = data["llm"]
    assert "configured" in llm
    assert "model" in llm
    assert "provider" in llm
    assert llm["provider"] == "groq"


# ── Stats Endpoint ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_stats_endpoint(client):
    """Test that /api/stats returns valid analytics."""
    response = await client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()

    assert "total_requests" in data
    assert isinstance(data["total_requests"], int)
    assert "average_response_time_ms" in data
    assert "requests_today" in data
    assert "top_locations" in data
    assert "top_cuisines" in data
    assert "llm_stats" in data


@pytest.mark.anyio
async def test_stats_reset(client):
    """Test that /api/stats/reset clears analytics."""
    # Reset
    response = await client.post("/api/stats/reset")
    assert response.status_code == 200

    # Verify reset
    response = await client.get("/api/stats")
    data = response.json()
    assert data["total_requests"] == 0
    assert data["top_locations"] == []
    assert data["top_cuisines"] == []


# ── Meta Endpoints ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_locations(client):
    """Test that /api/meta/locations returns valid location list."""
    response = await client.get("/api/meta/locations")
    assert response.status_code == 200
    data = response.json()

    assert "locations" in data
    assert "count" in data
    assert isinstance(data["locations"], list)
    assert data["count"] == len(data["locations"])
    assert data["count"] > 0


@pytest.mark.anyio
async def test_get_cuisines(client):
    """Test that /api/meta/cuisines returns valid cuisine list."""
    response = await client.get("/api/meta/cuisines")
    assert response.status_code == 200
    data = response.json()

    assert "cuisines" in data
    assert "count" in data
    assert isinstance(data["cuisines"], list)
    assert data["count"] == len(data["cuisines"])
    assert data["count"] > 0


@pytest.mark.anyio
async def test_locations_sorted(client):
    """Verify locations are returned in sorted order."""
    response = await client.get("/api/meta/locations")
    locations = response.json()["locations"]
    assert locations == sorted(locations)


@pytest.mark.anyio
async def test_cuisines_sorted(client):
    """Verify cuisines are returned in sorted order."""
    response = await client.get("/api/meta/cuisines")
    cuisines = response.json()["cuisines"]
    assert cuisines == sorted(cuisines)


# ── Recommend Endpoint ────────────────────────────────────────────

@pytest.mark.anyio
async def test_recommend_valid_request(client):
    """Test a valid recommendation request returns proper response."""
    payload = {
        "location": "Koramangala",
        "budget": "medium",
        "min_rating": 3.0,
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "recommendations" in data
    assert "summary" in data
    assert "filters_applied" in data
    assert "total_matches" in data
    assert isinstance(data["recommendations"], list)


@pytest.mark.anyio
async def test_recommend_with_cuisine(client):
    """Test recommendation with a specific cuisine filter."""
    payload = {
        "location": "Koramangala",
        "budget": "medium",
        "cuisine": "north indian",
        "min_rating": 3.0,
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data


@pytest.mark.anyio
async def test_recommend_invalid_budget(client):
    """Test that an invalid budget returns 422."""
    payload = {
        "location": "Koramangala",
        "budget": "super_expensive",  # Invalid
        "min_rating": 3.0,
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_recommend_missing_location(client):
    """Test that missing location returns 422."""
    payload = {
        "budget": "medium",
        "min_rating": 3.0,
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_recommend_invalid_rating(client):
    """Test that out-of-range rating returns 422."""
    payload = {
        "location": "Koramangala",
        "budget": "medium",
        "min_rating": 6.0,  # Over 5.0
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_recommend_nonexistent_location(client):
    """Test recommendation for a location with no restaurants."""
    payload = {
        "location": "Timbuktu",
        "budget": "medium",
        "min_rating": 3.0,
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Should return empty results or relaxed results
    assert isinstance(data["recommendations"], list)


@pytest.mark.anyio
async def test_recommend_response_structure(client):
    """Verify the full response structure of a recommendation."""
    payload = {
        "location": "Bellandur",
        "budget": "medium",
        "min_rating": 4.0,
    }
    response = await client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "rank" in rec
        assert "restaurant_name" in rec
        assert "cuisine" in rec
        assert "rating" in rec
        assert "estimated_cost_for_two" in rec
        assert "explanation" in rec
        assert isinstance(rec["rank"], int)
        assert isinstance(rec["rating"], (int, float))


@pytest.mark.anyio
async def test_analytics_tracked_after_request(client):
    """Verify that analytics are updated after a recommendation request."""
    # Reset analytics first
    await client.post("/api/stats/reset")

    # Make a request
    payload = {
        "location": "Koramangala",
        "budget": "medium",
        "min_rating": 3.0,
    }
    await client.post("/api/recommend", json=payload)

    # Check analytics
    stats_response = await client.get("/api/stats")
    stats = stats_response.json()
    assert stats["total_requests"] >= 1
    assert len(stats["top_locations"]) > 0
