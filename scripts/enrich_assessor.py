#!/usr/bin/env python3
"""
enrich_assessor.py - Enrich existing wiki stubs with Solano County Assessor data.

For wiki pages that were created from Address Points (GIS data), this script
adds assessor information from the Parcels shapefile:
  - Year Built (if not already set)
  - APN (if not already set)
  - Stories (if not already set)
  - Current Use (if not already set)

Only updates Stub-confidence pages. Skips pages already enriched by DPR 523
or NRHP data (which have higher confidence levels).
"""
import json
import re
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
        r = self.session.get(API_URL, params={
            "action": "query", "meta": "tokens", "type": "login", "format": "json"
        })
        login_token = r.json()["query"]["tokens"]["logintoken"]

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

    def get_page_content(self, title):
        r = self.session.get(API_URL, params={
            "action": "query", "titles": title, "prop": "revisions",
            "rvprop": "content", "format": "json"
        })
        pages = r.json()["query"]["pages"]
        for pid, page in pages.items():
            if pid == "-1":
                return None
            revs = page.get("revisions", [])
            if revs:
                return revs[0].get("*", "")
        return None

    def edit_page(self, title, content, summary=""):
        if self.call_count >= 50:
            self.get_csrf_token()

        data = {
            "action": "edit",
            "title": title,
            "text": content,
            "summary": summary,
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

        if "edit" in result and result["edit"].get("result") == "Success":
            return "updated"
        return f"error: {result}"


def parse_template_param(content, param_name):
    """Extract a template parameter value from wiki content."""
    escaped = re.escape(param_name)
    pattern = r'\|' + escaped + r'\s*=\s*([^\n|}{]*)'
    m = re.search(pattern, content)
    if m:
        return m.group(1).strip()
    return ""


def set_template_param(content, param_name, new_value):
    """Set a template parameter value in wiki content.

    If the parameter exists but is empty, fill it in.
    If it doesn't exist, add it before the closing }}.
    """
    # Check if param already exists
    escaped = re.escape(param_name)
    pattern = r'(\|' + escaped + r'\s*=\s*)([^\n|}{]*)'
    m = re.search(pattern, content)

    if m:
        # Parameter exists — only update if currently empty
        current = m.group(2).strip()
        if current:
            return content, False  # Already has a value, don't overwrite
        # Replace empty value
        content = content[:m.start(2)] + new_value + content[m.end(2):]
        return content, True
    else:
        # Parameter doesn't exist — add it before the closing }}
        # Find the template closing
        tmpl_end = content.find("}}")
        if tmpl_end == -1:
            return content, False

        # Find the last parameter line before }}
        before = content[:tmpl_end]
        insert_pos = before.rfind("\n")
        if insert_pos == -1:
            insert_pos = tmpl_end

        new_line = f"\n|{param_name}={new_value}"
        content = content[:insert_pos] + new_line + content[insert_pos:]
        return content, True


def main():
    # Load audit data
    audit_path = SEED_DIR / "parcel_audit.json"
    if not audit_path.exists():
        print("ERROR: Run find_missing_parcels.py first to generate parcel_audit.json")
        sys.exit(1)

    with open(audit_path) as f:
        audit = json.load(f)

    enrichable = audit.get("enrichable_addresses", [])
    all_parcels = audit.get("all_parcel_data", {})

    print(f"Found {len(enrichable)} pages that could get assessor year_built.")
    print(f"Total parcel records: {len(all_parcels)}")

    # Connect to wiki
    client = WikiClient()
    client.login()
    client.get_csrf_token()

    updated = 0
    skipped_enriched = 0
    skipped_has_year = 0
    skipped_no_page = 0
    errors = 0
    total = len(all_parcels)

    for i, (title, rec) in enumerate(sorted(all_parcels.items())):
        # Get current page content
        content = client.get_page_content(title)

        if content is None:
            skipped_no_page += 1
            continue

        # Skip if already enriched (not a Stub)
        confidence = parse_template_param(content, "Data Confidence")
        if confidence and confidence not in ("Stub", ""):
            skipped_enriched += 1
            continue

        # Track what we changed
        changes = []
        modified = False

        # Add Year Built if missing and we have it
        yr = rec.get("year_built", 0)
        if yr and yr > 0:
            current_yr = parse_template_param(content, "Year Built")
            if not current_yr:
                content, changed = set_template_param(content, "Year Built", str(yr))
                if changed:
                    changes.append(f"yr={yr}")
                    modified = True
                # Also mark as approximate since assessor data isn't exact
                content, _ = set_template_param(content, "Year Built Approximate", "Yes")

        # Add APN if missing
        apn = rec.get("apn", "")
        if apn:
            current_apn = parse_template_param(content, "APN")
            if not current_apn:
                content, changed = set_template_param(content, "APN", apn)
                if changed:
                    changes.append(f"apn={apn}")
                    modified = True

        # Add Stories if missing
        stories = rec.get("stories", 0)
        if stories and stories > 0:
            current_stories = parse_template_param(content, "Stories")
            if not current_stories:
                s = int(stories) if stories == int(stories) else stories
                content, changed = set_template_param(content, "Stories", str(s))
                if changed:
                    changes.append(f"stories={s}")
                    modified = True

        # Add Current Use if missing
        use_desc = rec.get("use_desc", "")
        if use_desc:
            current_use = parse_template_param(content, "Current Use")
            if not current_use:
                mapped_use = USE_MAP.get(use_desc, use_desc.title())
                content, changed = set_template_param(content, "Current Use", mapped_use)
                if changed:
                    changes.append(f"use={mapped_use}")
                    modified = True

        if not modified:
            skipped_has_year += 1
            continue

        # Update the page
        summary = "Add assessor data: " + ", ".join(changes)
        result = client.edit_page(title, content, summary)

        if result == "updated":
            updated += 1
            if updated <= 20 or updated % 100 == 0:
                print(f"  [{updated}] {title}: {', '.join(changes)}")
        else:
            errors += 1
            print(f"  ERROR: {title} — {result}")

        # Rate limit
        if (i + 1) % 20 == 0:
            time.sleep(0.5)

        # Progress
        if (i + 1) % 200 == 0:
            print(f"  ... processed {i+1}/{total} parcels "
                  f"({updated} updated, {skipped_enriched} enriched, "
                  f"{skipped_has_year} already have data)")

    print(f"\n=== DONE ===")
    print(f"  Updated with assessor data: {updated}")
    print(f"  Skipped (already enriched/High confidence): {skipped_enriched}")
    print(f"  Skipped (already has year_built/data): {skipped_has_year}")
    print(f"  Skipped (no wiki page): {skipped_no_page}")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    main()
