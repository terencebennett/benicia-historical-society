#!/usr/bin/env python3
"""
create_parcel_stubs.py - Create wiki stub pages for addresses found in the
Parcels shapefile that don't yet have wiki pages.

Uses the parcel_audit.json output from find_missing_parcels.py.
Creates property pages with assessor data (year built, stories, APN, use).
"""
import json
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SEED_DIR = DATA_DIR / "seed"

WIKI_URL = "http://localhost:8080"
API_URL = f"{WIKI_URL}/api.php"
USERNAME = "Admin"
PASSWORD = "OGMzCLBWhxdJf1B2Lj45"

# Map parcel use descriptions to more human-readable current use values
USE_MAP = {
    "SINGLE FAMILY RESIDENCE": "Residential",
    "SINGLE FAMILY CONDOMINIUM/PUD": "Residential (Condominium)",
    "IMPROVED MULTIPLE RESIDENTIAL": "Multi-Family Residential",
    "GENERAL RETAIL COMMERCIAL": "Commercial (Retail)",
    "GENERAL OFFICE, MED., & DENT.": "Commercial (Office)",
    "RESTAURANT/ LOUNGE": "Commercial (Restaurant)",
    "MIXED USE COMML & RES": "Mixed Use (Commercial/Residential)",
    "FINANCIAL": "Commercial (Financial)",
    "SHOPPING CENTER  ALL TYPES": "Commercial (Shopping Center)",
    "MISCELLANEOUS COMMERCIAL": "Commercial",
    "THEATER/ENTERTAINMENT": "Commercial (Entertainment)",
    "MANUFACTURING AND WAREHOUSING": "Industrial",
    "MISCELLANEOUS INDUSTRIAL": "Industrial",
    "GOVERNMENTAL & MISCELLANEOUS": "Government/Institutional",
    "MANUFACTURED HOME PARK": "Manufactured Home Park",
    "VACANT COMMERCIAL LAND": "Vacant (Commercial)",
    "VACANT RESIDENTIAL LAND < 1 AC": "Vacant (Residential)",
    "SERVICE STATIONS": "Commercial (Service Station)",
}


class WikiClient:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.call_count = 0

    def login(self):
        # Get login token
        r = self.session.get(API_URL, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json"
        })
        login_token = r.json()["query"]["tokens"]["logintoken"]

        # Login
        r = self.session.post(API_URL, data={
            "action": "login", "lgname": USERNAME, "lgpassword": PASSWORD,
            "lgtoken": login_token, "format": "json"
        })
        result = r.json()["login"]["result"]
        if result != "Success":
            raise RuntimeError(f"Login failed: {result}")
        print("Logged in to wiki.")

    def get_csrf_token(self):
        r = self.session.get(API_URL, params={
            "action": "query", "meta": "tokens", "format": "json"
        })
        self.csrf_token = r.json()["query"]["tokens"]["csrftoken"]
        self.call_count = 0

    def page_exists(self, title):
        r = self.session.get(API_URL, params={
            "action": "query", "titles": title, "format": "json"
        })
        pages = r.json()["query"]["pages"]
        return "-1" not in pages

    def create_page(self, title, content, summary=""):
        if self.call_count >= 50:
            self.get_csrf_token()

        data = {
            "action": "edit",
            "title": title,
            "text": content,
            "summary": summary,
            "createonly": True,
            "format": "json",
            "token": self.csrf_token,
        }

        r = self.session.post(API_URL, data=data)
        result = r.json()
        self.call_count += 1

        if "error" in result:
            code = result["error"]["code"]
            if code == "badtoken":
                self.get_csrf_token()
                data["token"] = self.csrf_token
                r = self.session.post(API_URL, data=data)
                result = r.json()
                self.call_count += 1
            elif code == "articleexists":
                return "exists"

        if "edit" in result and result["edit"].get("result") == "Success":
            return "created"
        return f"error: {result}"


def build_page_content(rec):
    """Build wiki page content from a parcel record."""
    title = rec["wiki_title"]
    apn = rec.get("apn", "")
    year_built = rec.get("year_built", 0)
    stories = rec.get("stories", 0)
    use_desc = rec.get("use_desc", "")
    lat = rec.get("latitude", "")
    lon = rec.get("longitude", "")

    # Map use description
    current_use = USE_MAP.get(use_desc, use_desc.title() if use_desc else "")

    # Build template parameters
    params = [f"|Current Address={title}"]

    if apn:
        params.append(f"|APN={apn}")

    if year_built and year_built > 0:
        params.append(f"|Year Built={year_built}")
        params.append("|Year Built Approximate=Yes")  # Assessor data may be approximate

    if stories and stories > 0:
        s = int(stories) if stories == int(stories) else stories
        params.append(f"|Stories={s}")

    if current_use:
        params.append(f"|Current Use={current_use}")

    params.append("|Historic Status=Not Surveyed")

    if lat:
        params.append(f"|Latitude={lat}")
    if lon:
        params.append(f"|Longitude={lon}")

    params.append("|Data Confidence=Stub")

    template_call = "{{Property\n" + "\n".join(params) + "\n}}"

    # Build the page body
    body_parts = [template_call, ""]

    # Add a description line
    if year_built and year_built > 0:
        body_parts.append(
            f"This property at '''{title}''' was built circa {year_built} "
            f"according to Solano County Assessor records."
        )
    else:
        body_parts.append(
            f"This is a property page for '''{title}'''."
        )

    body_parts.append("")
    body_parts.append("== History ==")
    body_parts.append("''No history recorded yet.''")
    body_parts.append("")
    body_parts.append("== Sources ==")
    body_parts.append(
        "* Solano County Assessor parcel data "
        f"(APN: {apn})" if apn else "* Solano County Assessor parcel data"
    )
    body_parts.append("")

    return "\n".join(body_parts)


def main():
    # Load audit data
    audit_path = SEED_DIR / "parcel_audit.json"
    if not audit_path.exists():
        print("ERROR: Run find_missing_parcels.py first to generate parcel_audit.json")
        sys.exit(1)

    with open(audit_path) as f:
        audit = json.load(f)

    missing = audit["missing_addresses"]
    print(f"Found {len(missing)} missing addresses to create.")

    # Filter: skip unit/apt numbers with zero-padded unit numbers (like "Unit 0005")
    # These are condo/office splits that aren't historically meaningful
    meaningful = []
    skipped_units = 0
    for rec in missing:
        title = rec["wiki_title"]
        # Skip zero-padded unit numbers (condo subdivisions)
        if "Unit 0" in title:
            skipped_units += 1
            continue
        meaningful.append(rec)

    print(f"Skipping {skipped_units} zero-padded unit addresses (condo splits)")
    print(f"Creating {len(meaningful)} meaningful address pages.")

    if not meaningful:
        print("Nothing to create.")
        return

    # Connect to wiki
    client = WikiClient()
    client.login()
    client.get_csrf_token()

    created = 0
    existed = 0
    errors = 0

    for i, rec in enumerate(meaningful):
        title = rec["wiki_title"]
        content = build_page_content(rec)
        summary = "Create stub from Solano County Assessor parcel data"

        result = client.create_page(title, content, summary)

        if result == "created":
            created += 1
            yr = rec.get("year_built", 0)
            yr_str = str(yr) if yr > 0 else "?"
            print(f"  [{i+1}/{len(meaningful)}] CREATED: {title} (yr={yr_str})")
        elif result == "exists":
            existed += 1
            print(f"  [{i+1}/{len(meaningful)}] EXISTS:  {title}")
        else:
            errors += 1
            print(f"  [{i+1}/{len(meaningful)}] ERROR:   {title} — {result}")

        # Rate limit
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    print(f"\n=== DONE ===")
    print(f"  Created: {created}")
    print(f"  Already existed: {existed}")
    print(f"  Errors: {errors}")

    # Update addresses.json with new pages
    if created > 0:
        addr_path = SEED_DIR / "addresses.json"
        with open(addr_path) as f:
            addresses = json.load(f)

        for rec in meaningful:
            title = rec["wiki_title"]
            # Check if already in addresses.json
            existing_titles = {a["wiki_title"] for a in addresses["addresses"]}
            if title not in existing_titles:
                addresses["addresses"].append({
                    "wiki_title": title,
                    "latitude": rec.get("latitude", 0),
                    "longitude": rec.get("longitude", 0),
                    "source": "parcels_assessor",
                })

        with open(addr_path, "w") as f:
            json.dump(addresses, f, indent=2)
        print(f"Updated addresses.json ({len(addresses['addresses'])} total)")


if __name__ == "__main__":
    main()
