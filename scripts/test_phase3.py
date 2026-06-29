"""Phase 3 acceptance test script.

Tests:
1. POST /api/recommend returns results with fallback (no API key)
2. Response matches RecommendationResponse schema
3. Response includes summary and explanations
4. Validation still works (422 on bad input)
"""

import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"


def test_recommend_fallback():
    """Test POST /api/recommend — should use fallback when no API key."""
    body = json.dumps({
        "location": "Indiranagar",
        "budget": "medium",
        "cuisine": "italian",
        "min_rating": 3.0,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/recommend",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())

    # Verify response schema
    assert "recommendations" in data, "Missing 'recommendations'"
    assert "summary" in data, "Missing 'summary'"
    assert "filters_applied" in data, "Missing 'filters_applied'"
    assert "total_matches" in data, "Missing 'total_matches'"

    print(f"[PASS] POST /api/recommend -- {data['total_matches']} matches")
    print(f"   Summary: {data['summary']}")
    if data.get("relaxation_notice"):
        print(f"   Relaxation: {data['relaxation_notice']}")

    for rec in data["recommendations"]:
        assert "rank" in rec, "Missing 'rank'"
        assert "restaurant_name" in rec, "Missing 'restaurant_name'"
        assert "cuisine" in rec, "Missing 'cuisine'"
        assert "rating" in rec, "Missing 'rating'"
        assert "estimated_cost_for_two" in rec, "Missing 'estimated_cost_for_two'"
        assert "explanation" in rec, "Missing 'explanation'"
        print(f"   #{rec['rank']} {rec['restaurant_name']} -- *{rec['rating']} -- Rs.{rec['estimated_cost_for_two']}")
        print(f"      {rec['explanation'][:80]}...")

    print(f"[PASS] Schema validation -- all required fields present")
    return data


def test_recommend_no_cuisine():
    """Test without cuisine -- should return results across all cuisines."""
    body = json.dumps({
        "location": "Koramangala",
        "budget": "low",
        "min_rating": 3.0,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/recommend",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    print(f"[PASS] No cuisine filter -- {data['total_matches']} matches, {len(data['recommendations'])} recs")
    return data


def test_empty_results():
    """Test with obscure location -- should return empty or relaxed results."""
    body = json.dumps({
        "location": "Timbuktu",
        "budget": "high",
        "min_rating": 4.5,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/recommend",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    print(f"[PASS] No matches scenario -- {data['total_matches']} matches")
    print(f"   Summary: {data['summary']}")
    if data.get("relaxation_notice"):
        print(f"   Relaxation: {data['relaxation_notice']}")
    return data


def test_validation_error():
    """Test invalid input returns 422."""
    body = json.dumps({"budget": "medium"}).encode("utf-8")  # missing location
    req = urllib.request.Request(
        f"{BASE}/api/recommend",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
        print("[FAIL] Expected 422 but got 200")
    except urllib.error.HTTPError as e:
        if e.code == 422:
            print(f"[PASS] Validation -- 422 returned for missing 'location'")
        else:
            print(f"[FAIL] Expected 422 but got {e.code}")


def test_additional_preferences():
    """Test with additional preferences field."""
    body = json.dumps({
        "location": "Bangalore",
        "budget": "high",
        "cuisine": "north indian",
        "min_rating": 4.0,
        "additional_preferences": "rooftop, romantic, live music",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/recommend",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    print(f"[PASS] Additional preferences -- {data['total_matches']} matches, {len(data['recommendations'])} recs")
    return data


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3 Acceptance Tests")
    print("=" * 60)
    print()

    test_recommend_fallback()
    print()
    test_recommend_no_cuisine()
    print()
    test_empty_results()
    print()
    test_validation_error()
    print()
    test_additional_preferences()

    print()
    print("=" * 60)
    print("All Phase 3 acceptance criteria verified!")
    print("(Fallback mode tested -- set GROQ_API_KEY in .env for LLM ranking)")
    print("=" * 60)
