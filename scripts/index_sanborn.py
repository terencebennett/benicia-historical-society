#!/usr/bin/env python3
"""
index_sanborn.py - Create Sanborn map index pages in MediaWiki.

Queries the Library of Congress API for Benicia Sanborn maps and creates
index pages for each edition year with links to individual sheets.

Usage: python3 scripts/index_sanborn.py [--wiki-url URL] [--user USER] [--password PASS]
       python3 scripts/index_sanborn.py --fetch-only  # Just download LOC metadata
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

# Known Sanborn map editions for Benicia
# LOC item IDs from https://www.loc.gov/collections/sanborn-maps/?q=benicia
BENICIA_SANBORN_EDITIONS = [
    {
        "year": 1886,
        "loc_item_id": "sanborn00417_001",
        "loc_url": "https://www.loc.gov/item/sanborn00417_001/",
        "sheets": 3,
        "notes": "First Sanborn survey of Benicia. 3 sheets covering the core downtown.",
    },
    {
        "year": 1891,
        "loc_item_id": "sanborn00417_002",
        "loc_url": "https://www.loc.gov/item/sanborn00417_002/",
        "sheets": 5,
        "notes": "Expanded coverage of downtown Benicia. 5 sheets.",
    },
    {
        "year": 1899,
        "loc_item_id": "sanborn00417_003",
        "loc_url": "https://www.loc.gov/item/sanborn00417_003/",
        "sheets": 17,
        "notes": "Most detailed 19th century survey. 17 sheets covering the full town.",
    },
    {
        "year": 1913,
        "loc_item_id": "sanborn00417_004",
        "loc_url": "https://www.loc.gov/item/sanborn00417_004/",
        "sheets": 17,
        "notes": "Aligns with the 1910 census. 17 sheets.",
    },
    {
        "year": 1942,
        "loc_item_id": "sanborn00417_005",
        "loc_url": "https://www.loc.gov/item/sanborn00417_005/",
        "sheets": 17,
        "notes": "Last Sanborn survey. Aligns with WWII era and Arsenal activity.",
    },
]


def fetch_loc_metadata(edition: dict) -> dict:
    """Fetch metadata from the Library of Congress API for a Sanborn edition."""
    item_id = edition["loc_item_id"]
    api_url = f"https://www.loc.gov/item/{item_id}/?fo=json"

    print(f"  Fetching LOC metadata for {edition['year']}...")
    try:
        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  WARNING: Could not fetch LOC data for {item_id}: {e}")
        return {}


def build_edition_page(edition: dict, loc_data: dict) -> str:
    """Build the main index page for a Sanborn map year."""
    year = edition["year"]
    sheets = edition["sheets"]
    loc_url = edition["loc_url"]
    notes = edition["notes"]

    # Try to extract additional info from LOC metadata
    title_from_loc = ""
    if loc_data:
        item = loc_data.get("item", {})
        title_from_loc = item.get("title", "")

    content = f"""= Sanborn Fire Insurance Map of Benicia, {year} =

{{{{SanbornSheet
|Map Year={year}
|Sheet Number=Index
|Coverage Area=All of Benicia
|LOC URL={loc_url}
}}}}

== Overview ==
{notes}

{f"''LOC catalog title: {title_from_loc}''" if title_from_loc else ""}

This edition contains '''{sheets} sheets''' covering Benicia, Solano County, California.

All pre-1926 Sanborn maps are '''public domain''' and freely downloadable from the Library of Congress.

'''[{loc_url} View all sheets at the Library of Congress]'''

== Sheet Index ==
{{| class="wikitable sortable" style="width:100%;"
! Sheet !! Coverage Area !! Wiki Page
"""

    for i in range(1, sheets + 1):
        page_title = f"Sanborn {year} Sheet {i}"
        content += f"|-\n| {i} || ''Coverage area to be determined'' || [[{page_title}]]\n"

    content += f"""|}}

== How to Use These Maps ==
Sanborn Fire Insurance Maps show detailed building information for the date surveyed:
* '''Building footprints''' showing the shape and size of every structure
* '''Construction materials''': yellow/buff = wood frame, pink/red = brick, blue = stone
* '''Number of stories''' (shown as numbers inside buildings)
* '''Building use''': D = dwelling, S = store, Off = office
* '''Street names and house numbers''' as they were at the time of the survey
* '''Block numbers''' used by the city at the time

=== Comparing Across Years ===
By comparing the same area across the {", ".join(str(e["year"]) for e in BENICIA_SANBORN_EDITIONS)} editions, you can track:
* When buildings were constructed or demolished
* Additions and modifications to existing buildings
* Changes in building use
* Street and address renumbering

== Related Resources ==
* [[Category:Sanborn {year}|All sheets from this edition]]
* [[Category:Sanborn Maps|All Benicia Sanborn Maps]]
* [{loc_url} Library of Congress catalog entry]

[[Category:Sanborn {year}]]
[[Category:Sanborn Maps]]
"""
    return content


def build_sheet_page(edition: dict, sheet_num: int) -> str:
    """Build a wiki page for an individual Sanborn map sheet."""
    year = edition["year"]
    loc_url = edition["loc_url"]

    content = f"""{{{{SanbornSheet
|Map Year={year}
|Sheet Number={sheet_num}
|Coverage Area=To be determined
|LOC URL={loc_url}
}}}}

== Description ==
This is '''Sheet {sheet_num}''' from the '''{year} Sanborn Fire Insurance Map of Benicia, California'''.

'''[{loc_url} View this map at the Library of Congress]'''

== Coverage ==
''The specific streets and blocks shown on this sheet have not yet been documented. Volunteers can help by examining the map image and listing the coverage area here.''

== Properties Visible on This Sheet ==
''As researchers identify buildings on this map sheet, they should be listed here with links to their property pages.''

{{| class="wikitable"
! Address (on map) !! Modern Address !! Description !! Notes
|}}

== Comparison with Other Years ==
Compare this area across other Sanborn editions:
"""

    for ed in BENICIA_SANBORN_EDITIONS:
        if ed["year"] != year:
            content += f"* [[Sanborn {ed['year']} Sheet {sheet_num}|{ed['year']} Sheet {sheet_num}]]\n"

    content += f"""
== Notes ==
''Add observations about this map sheet.''

[[Category:Sanborn {year}]]
"""
    return content


def save_sanborn_index(editions: list, loc_metadata: dict):
    """Save Sanborn index data to seed directory."""
    index = {
        "editions": [],
    }
    for ed in editions:
        entry = {
            "year": ed["year"],
            "loc_item_id": ed["loc_item_id"],
            "loc_url": ed["loc_url"],
            "sheets": ed["sheets"],
            "notes": ed["notes"],
        }
        if ed["loc_item_id"] in loc_metadata:
            meta = loc_metadata[ed["loc_item_id"]]
            item = meta.get("item", {})
            entry["loc_title"] = item.get("title", "")
        index["editions"].append(entry)

    output_path = SEED_DIR / "sanborn_index.json"
    with open(output_path, "w") as f:
        json.dump(index, f, indent=2)
    print(f"\nSaved Sanborn index to {output_path}")


class WikiClient:
    """Minimal wiki client for page creation."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url
        self.session = requests.Session()
        self.csrf_token = None
        self._login(username, password)

    def _login(self, username: str, password: str):
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

        resp = self.session.get(self.api_url, params={
            "action": "query", "meta": "tokens", "format": "json",
        })
        resp.raise_for_status()
        self.csrf_token = resp.json()["query"]["tokens"]["csrftoken"]

    def create_page(self, title: str, content: str, summary: str) -> bool:
        resp = self.session.post(self.api_url, data={
            "action": "edit", "title": title, "text": content,
            "token": self.csrf_token, "format": "json",
            "summary": summary, "bot": True,
        })
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            print(f"  ERROR: {result['error']}")
            return False
        return result.get("edit", {}).get("result") == "Success"


def main():
    parser = argparse.ArgumentParser(description="Create Sanborn map index pages")
    parser.add_argument("--wiki-url", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--fetch-only", action="store_true",
                        help="Only fetch LOC metadata, don't create wiki pages")
    args = parser.parse_args()

    SEED_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch LOC metadata for each edition
    print("=== Fetching Library of Congress Metadata ===")
    loc_metadata = {}
    for edition in BENICIA_SANBORN_EDITIONS:
        metadata = fetch_loc_metadata(edition)
        if metadata:
            loc_metadata[edition["loc_item_id"]] = metadata
        time.sleep(1)  # Be polite to LOC servers

    save_sanborn_index(BENICIA_SANBORN_EDITIONS, loc_metadata)

    if args.fetch_only:
        print("\nFetch-only mode. Sanborn index saved. Exiting.")
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

    print(f"\nWiki API: {api_url}")
    wiki = WikiClient(api_url, username, password)
    print("Authenticated.\n")

    # Create edition index pages
    print("=== Creating Sanborn Edition Pages ===")
    for edition in BENICIA_SANBORN_EDITIONS:
        year = edition["year"]
        loc_data = loc_metadata.get(edition["loc_item_id"], {})
        content = build_edition_page(edition, loc_data)
        title = f"Sanborn Maps {year}"
        ok = wiki.create_page(title, content, f"Create Sanborn {year} index page")
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {title}")

    # Create individual sheet pages
    print("\n=== Creating Individual Sheet Pages ===")
    total_sheets = sum(ed["sheets"] for ed in BENICIA_SANBORN_EDITIONS)
    created = 0

    for edition in BENICIA_SANBORN_EDITIONS:
        year = edition["year"]
        for sheet_num in range(1, edition["sheets"] + 1):
            content = build_sheet_page(edition, sheet_num)
            title = f"Sanborn {year} Sheet {sheet_num}"
            ok = wiki.create_page(title, content, f"Create Sanborn {year} sheet {sheet_num}")
            if ok:
                created += 1
            time.sleep(0.05)

        print(f"  Sanborn {year}: {edition['sheets']} sheet pages created")

    print(f"\n=== Complete ===")
    print(f"  Edition pages: {len(BENICIA_SANBORN_EDITIONS)}")
    print(f"  Sheet pages: {created} / {total_sheets}")


if __name__ == "__main__":
    main()
