#!/usr/bin/env python3
"""
create_stubs.py - Create property stub pages in MediaWiki from addresses.json.

Reads data/seed/addresses.json and creates a wiki page for each address
using the Property template. Each page is a stub with basic GIS data.

Usage: python3 scripts/create_stubs.py [--wiki-url URL] [--user USER] [--password PASS]
       python3 scripts/create_stubs.py --dry-run  # Preview without creating pages
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SEED_DIR = DATA_DIR / "seed"

# Map street names to category-friendly versions
STREET_CATEGORY_MAP = {}  # Built dynamically


def street_to_category(addr: dict) -> str:
    """Convert address components to a street category name."""
    prefix = addr.get("street_prefix", "").strip()
    name = addr.get("street_name", "").strip()
    stype = addr.get("street_type", "").strip()

    if not name:
        return ""

    # Map abbreviations to full names
    prefix_map = {"W": "West", "E": "East", "N": "North", "S": "South"}
    prefix_full = prefix_map.get(prefix, prefix)

    type_map = {"St": "Street", "Ave": "Avenue", "Blvd": "Boulevard",
                "Dr": "Drive", "Ct": "Court", "Pl": "Place", "Ln": "Lane",
                "Rd": "Road", "Cir": "Circle", "Ter": "Terrace", "Way": "Way"}
    type_full = type_map.get(stype, stype)

    parts = [prefix_full, name, type_full]
    street = " ".join(p for p in parts if p)

    return f"Properties on {street}"


def build_page_content(addr: dict) -> str:
    """Build the wiki page content for a property stub."""
    wiki_title = addr.get("wiki_title", addr["full_address"])
    apn = addr.get("apn", "")
    lat = addr.get("latitude", "")
    lon = addr.get("longitude", "")
    area = addr.get("area", "downtown")

    # Build template call
    template_params = [
        f"|Current Address={wiki_title}",
    ]
    if apn:
        template_params.append(f"|APN={apn}")
    if lat:
        template_params.append(f"|Latitude={lat}")
    if lon:
        template_params.append(f"|Longitude={lon}")

    template_params.extend([
        "|Historic Status=Not Surveyed",
        "|Data Confidence=Stub",
    ])

    template_call = "{{Property\n" + "\n".join(template_params) + "\n}}"

    # Build the full page content with section stubs
    street_cat = street_to_category(addr)
    categories = ["[[Category:Properties]]"]
    if street_cat:
        categories.append(f"[[Category:{street_cat}]]")
    if area == "arsenal":
        categories.append("[[Category:Arsenal Properties]]")

    page = f"""{template_call}

== Summary ==
This is a stub page for '''{wiki_title}'''. It was auto-generated from Solano County GIS data and contains only basic address information. Researchers are invited to add historical data.

== Historical Addresses ==
{{| class="wikitable"
! Period !! Address !! Source
|-
| Current || {wiki_title} || Solano County GIS Address Points
|}}

== Physical Description ==
''No physical description available. Add information from DPR 523 survey forms, personal observation, or other sources.''

== Historical Significance ==
''Not yet researched.''

== Ownership History ==
=== Census Records ===
{{| class="wikitable"
! Year !! Head of Household !! Occupation !! Other Residents !! Source
|}}

''Use [[Form:CensusEntry]] to add census records for this address.''

=== Deed Records ===
''To be populated as records are researched.''

== On the Maps ==
=== Sanborn Maps ===
''Check the [[Category:Sanborn Maps|Sanborn Map index]] for sheets covering this address.''

== Newspaper References ==
''Reserved for future Benicia Herald integration.''

== Gallery ==
''Add photographs and historical images.''

== Sources ==
* Solano County GIS Address Points Shapefile (address and coordinates)
{f"* APN: {apn}" if apn else ""}

== Notes ==
''Add researcher notes, questions, or contradictions to investigate.''

{chr(10).join(categories)}
"""
    return page


class WikiClient:
    """Handles authenticated page creation via the MediaWiki API."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.csrf_token = None
        self.calls_since_refresh = 0
        self._login(username, password)

    def _login(self, username: str, password: str):
        """Login and get CSRF token."""
        resp = self.session.get(self.api_url, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json",
        })
        resp.raise_for_status()
        login_token = resp.json()["query"]["tokens"]["logintoken"]

        resp = self.session.post(self.api_url, data={
            "action": "login", "lgname": username, "lgpassword": password,
            "lgtoken": login_token, "format": "json",
        })
        resp.raise_for_status()
        result = resp.json()
        if result.get("login", {}).get("result") != "Success":
            print(f"ERROR: Login failed: {result}")
            sys.exit(1)

        self._refresh_token()

    def _refresh_token(self):
        """Refresh the CSRF token."""
        resp = self.session.get(self.api_url, params={
            "action": "query", "meta": "tokens", "format": "json",
        })
        resp.raise_for_status()
        self.csrf_token = resp.json()["query"]["tokens"]["csrftoken"]
        self.calls_since_refresh = 0

    def create_page(self, title: str, content: str, summary: str) -> bool:
        """Create a new wiki page. Returns True on success."""
        # Refresh token every 200 calls to prevent expiry
        if self.calls_since_refresh >= 200:
            self._refresh_token()

        resp = self.session.post(self.api_url, data={
            "action": "edit",
            "title": title,
            "text": content,
            "token": self.csrf_token,
            "format": "json",
            "createonly": True,
            "summary": summary,
            "bot": True,
        })
        resp.raise_for_status()
        result = resp.json()
        self.calls_since_refresh += 1

        if "error" in result:
            code = result["error"].get("code", "")
            if code == "articleexists":
                return False  # Already exists, skip
            if code == "badtoken":
                # Token expired, refresh and retry once
                self._refresh_token()
                return self.create_page(title, content, summary)
            print(f"  ERROR: {result['error']}")
            return False

        return result.get("edit", {}).get("result") == "Success"


def main():
    parser = argparse.ArgumentParser(description="Create property stub pages")
    parser.add_argument("--wiki-url", default=None, help="MediaWiki API URL")
    parser.add_argument("--user", default=None, help="Wiki admin username")
    parser.add_argument("--password", default=None, help="Wiki admin password")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating pages")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of pages to create (0=all)")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between API calls (seconds)")
    args = parser.parse_args()

    # Load addresses
    addresses_file = SEED_DIR / "addresses.json"
    if not addresses_file.exists():
        print("ERROR: data/seed/addresses.json not found.")
        print("Run download_gis_data.py first to generate the address list.")
        sys.exit(1)

    with open(addresses_file) as f:
        data = json.load(f)

    addresses = data.get("addresses", [])
    metadata = data.get("metadata", {})

    print(f"Loaded {len(addresses)} addresses from {addresses_file.name}")
    print(f"Source: {metadata.get('source', 'unknown')}")
    print(f"Download date: {metadata.get('download_date', 'unknown')}")
    print()

    if args.limit > 0:
        addresses = addresses[:args.limit]
        print(f"Limited to first {args.limit} addresses")

    if args.dry_run:
        print("=== DRY RUN MODE ===")
        print("Previewing first 3 pages:\n")
        for addr in addresses[:3]:
            title = addr.get("wiki_title", addr["full_address"])
            content = build_page_content(addr)
            print(f"--- Page: {title} ---")
            print(content[:500])
            print("...\n")
        print(f"Would create {len(addresses)} stub pages.")
        return

    # Load env
    env_path = PROJECT_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()

    api_url = args.wiki_url or env_vars.get("WIKI_SERVER", "http://localhost:8080") + "/api.php"
    username = args.user or env_vars.get("WIKI_ADMIN_USER", "Admin")
    password = args.password or env_vars.get("WIKI_ADMIN_PASSWORD", "")

    if not password:
        print("ERROR: No password provided.")
        sys.exit(1)

    print(f"Wiki API: {api_url}")
    wiki = WikiClient(api_url, username, password)
    print("Authenticated successfully.\n")

    created = 0
    skipped = 0
    errors = 0

    for i, addr in enumerate(addresses):
        title = addr.get("wiki_title", addr["full_address"])
        if not title:
            skipped += 1
            continue

        content = build_page_content(addr)
        ok = wiki.create_page(title, content, "Auto-generated property stub from GIS data")

        if ok:
            created += 1
            status = "CREATED"
        else:
            skipped += 1
            status = "SKIPPED"

        # Progress reporting
        if (i + 1) % 50 == 0 or (i + 1) == len(addresses):
            print(f"  [{i+1}/{len(addresses)}] {status}: {title}")

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\n=== Complete ===")
    print(f"  Created: {created}")
    print(f"  Skipped: {skipped} (already exist or empty)")
    print(f"  Errors:  {errors}")


if __name__ == "__main__":
    main()
