#!/usr/bin/env python3
"""Find wiki pages matching NRHP property addresses."""
import requests
import json

API = "http://localhost:8080/api.php"

# NRHP properties to find
addresses = [
    "120 East J Street",
    "165 East D Street",
    "90 First Street",
    "110 West J Street",
    "135 West G Street",
    "285 West G Street",
]

print("=== Checking exact page titles ===")
for addr in addresses:
    r = requests.get(API, params={"action": "query", "titles": addr, "format": "json"})
    pages = r.json()["query"]["pages"]
    exists = all(int(k) > 0 for k in pages.keys())
    status = "EXISTS" if exists else "MISSING"
    print(f"  [{status}] {addr}")

# Search for any East J Street or East D Street pages
print("\n=== Searching for East J Street pages ===")
r = requests.get(API, params={
    "action": "query", "list": "search",
    "srsearch": "East J Street", "srlimit": "10", "format": "json"
})
for item in r.json()["query"]["search"]:
    print(f"  {item['title']}")

print("\n=== Searching for East D Street pages ===")
r = requests.get(API, params={
    "action": "query", "list": "search",
    "srsearch": "East D Street", "srlimit": "10", "format": "json"
})
for item in r.json()["query"]["search"]:
    print(f"  {item['title']}")

print("\n=== Searching for West 12th Street pages ===")
r = requests.get(API, params={
    "action": "query", "list": "search",
    "srsearch": "West 12th Street", "srlimit": "10", "format": "json"
})
for item in r.json()["query"]["search"]:
    print(f"  {item['title']}")

# Also check what the current stub content looks like
print("\n=== Sample stub content (90 First Street) ===")
r = requests.get(API, params={
    "action": "query", "titles": "90 First Street",
    "prop": "revisions", "rvprop": "content", "rvslots": "main", "format": "json"
})
pages = r.json()["query"]["pages"]
for pid, pdata in pages.items():
    if int(pid) > 0:
        content = pdata["revisions"][0]["slots"]["main"]["*"]
        print(content)
