"""Quick API test script."""
import requests

BASE = "http://localhost:8000"

# Test 1: Locations
print("--- Test 1: GET /api/meta/locations ---")
r = requests.get(f"{BASE}/api/meta/locations")
print(f"Status: {r.status_code}")
data = r.json()
print(f"Count: {data['count']}")
print(f"First 10: {data['locations'][:10]}")

# Test 2: Cuisines
print("\n--- Test 2: GET /api/meta/cuisines ---")
r = requests.get(f"{BASE}/api/meta/cuisines")
print(f"Status: {r.status_code}")
data = r.json()
print(f"Count: {data['count']}")
print(f"First 10: {data['cuisines'][:10]}")

# Test 3: Recommend (happy path)
print("\n--- Test 3: POST /api/recommend (Indiranagar, medium, north indian) ---")
r = requests.post(f"{BASE}/api/recommend", json={
    "location": "Indiranagar",
    "budget": "medium",
    "cuisine": "north indian",
    "min_rating": 3.5,
})
print(f"Status: {r.status_code}")
data = r.json()
print(f"Total matches: {data['total_matches']}")
print(f"Summary: {data['summary']}")
for rec in data["recommendations"]:
    print(f"  #{rec['rank']} {rec['restaurant_name']} - {rec['cuisine']} - {rec['rating']}/5 - Rs {rec['estimated_cost_for_two']}")

# Test 4: Recommend (no cuisine)
print("\n--- Test 4: POST /api/recommend (Whitefield, low, no cuisine) ---")
r = requests.post(f"{BASE}/api/recommend", json={
    "location": "Whitefield",
    "budget": "low",
    "min_rating": 3.0,
})
print(f"Status: {r.status_code}")
data = r.json()
print(f"Total matches: {data['total_matches']}")
for rec in data["recommendations"]:
    print(f"  #{rec['rank']} {rec['restaurant_name']} - Rs {rec['estimated_cost_for_two']}")

# Test 5: Invalid input
print("\n--- Test 5: POST /api/recommend (invalid - empty location) ---")
r = requests.post(f"{BASE}/api/recommend", json={
    "location": "",
    "budget": "medium",
})
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n--- All tests complete ---")
