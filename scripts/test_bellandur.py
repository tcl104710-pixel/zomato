"""Predict top 5 restaurants in Bellandur with rating >= 4.2 and budget <= 1500."""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000"

body = json.dumps({
    "location": "Bellandur",
    "budget": "medium",
    "min_rating": 4.2,
}).encode("utf-8")

req = urllib.request.Request(
    f"{BASE}/api/recommend",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
r = urllib.request.urlopen(req)
data = json.loads(r.read())

print("=" * 65)
print("  Top 5 Restaurant Recommendations - Bellandur")
print("  Rating >= 4.2 | Budget <= Rs.1500 (medium)")
print("=" * 65)
print()
print(f"  Total matches: {data['total_matches']}")
if data.get("relaxation_notice"):
    print(f"  Note: {data['relaxation_notice']}")
print()

for rec in data["recommendations"]:
    print(f"  #{rec['rank']}  {rec['restaurant_name']}")
    print(f"      Cuisine : {rec['cuisine']}")
    print(f"      Rating  : {rec['rating']}/5")
    print(f"      Cost/2  : Rs.{rec['estimated_cost_for_two']:.0f}")
    print(f"      Why     : {rec['explanation']}")
    print()

print("-" * 65)
print(f"  AI Summary: {data['summary']}")
print("-" * 65)
