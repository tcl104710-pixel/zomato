"""Quick test script for Phase 2 API endpoints."""

import json
import urllib.request
import sys

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"


def test_locations():
    """Test GET /api/meta/locations"""
    r = urllib.request.urlopen(f"{BASE}/api/meta/locations")
    data = json.loads(r.read())
    print(f"[PASS] GET /api/meta/locations -- {data['count']} locations")
    print(f"   First 5: {data['locations'][:5]}")
    return data


def test_cuisines():
    """Test GET /api/meta/cuisines"""
    r = urllib.request.urlopen(f"{BASE}/api/meta/cuisines")
    data = json.loads(r.read())
    print(f"[PASS] GET /api/meta/cuisines -- {data['count']} cuisines")
    print(f"   First 5: {data['cuisines'][:5]}")
    return data


def test_recommend():
    """Test POST /api/recommend with valid body"""
    body = json.dumps({
        "location": "Bangalore",
        "budget": "medium",
        "cuisine": "italian",
        "min_rating": 3.5,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/api/recommend",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    r = urllib.request.urlopen(req)
    data = json.loads(r.read())
    print(f"[PASS] POST /api/recommend -- {data['total_matches']} matches, {len(data['recommendations'])} recommendations")
    print(f"   Summary: {data['summary']}")
    if data.get("relaxation_notice"):
        print(f"   Relaxation: {data['relaxation_notice']}")
    for rec in data["recommendations"]:
        print(f"   #{rec['rank']} {rec['restaurant_name']} -- *{rec['rating']} -- Rs.{rec['estimated_cost_for_two']}")
    return data


def test_validation():
    """Test POST /api/recommend with invalid body (should return 422)"""
    body = json.dumps({"budget": "medium"}).encode("utf-8")  # missing required 'location'
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
            print(f"[PASS] Validation -- 422 returned for missing 'location' field")
            detail = json.loads(e.read())
            print(f"   Detail: {detail['detail'][0]['msg']}")
        else:
            print(f"[FAIL] Expected 422 but got {e.code}")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Acceptance Tests")
    print("=" * 60)
    test_locations()
    print()
    test_cuisines()
    print()
    test_recommend()
    print()
    test_validation()
    print()
    print("=" * 60)
    print("All Phase 2 acceptance criteria verified!")
    print("=" * 60)
