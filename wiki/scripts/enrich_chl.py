#!/usr/bin/env python3
"""
enrich_chl.py - Write California Historical Landmark data into wiki.

Handles:
1. Benicia Capitol (115 West G Street) - update existing stub with NRHP + CHL data
2. Site/landmark pages for CHLs without standard street addresses

Sources: NPS National Register database, California OHP, Library of Congress HABS.
"""
import json
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

# ──────────────────────────────────────────────────────────────────────
# Property-based CHL (has a GIS stub to update)
# ──────────────────────────────────────────────────────────────────────

CAPITOL = {
    "page_title": "115 West G Street",
    "fields": {
        "Current Address": "115 West G Street",
        "Year Built": "1852",
        "Year Built Approximate": "No",
        "Architectural Style": "Greek Revival",
        "Stories": "2",
        "Construction Material": "Brick",
        "Historic Status": "Landmark",
        "Current Use": "Museum (Benicia Capitol State Historic Park)",
        "Original Use": "State Capitol of California",
        "Data Confidence": "High",
    },
    "common_name": "Benicia Capitol (State Capitol of California, 1853–1854)",
    "nrhp_ref": "71000204",
    "nrhp_date": "February 12, 1971",
    "chl_number": "153",
    "summary": (
        "The '''Benicia Capitol''' at 115 West G Street (corner of First and West G Streets) "
        "served as California's third state capitol. The legislature convened here from "
        "February 4, 1853 to February 25, 1854, before moving to Sacramento. It is the only "
        "surviving pre-Sacramento capitol building in California.\n\n"
        "Built in 1852, the two-story brick building in the Greek Revival style has served "
        "many roles over the years: county courthouse, justice court, school, library, theatre, "
        "church, police station, and city hall. The State of California acquired the building "
        "in 1949 and completed a restoration in 1956–1957. It is now the centerpiece of "
        "Benicia Capitol State Historic Park."
    ),
    "significance": (
        "Listed on the '''National Register of Historic Places''' on February 12, 1971 "
        "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/71000204 71000204]) — "
        "one of the earliest NRHP listings in California. "
        "Also designated '''California Historical Landmark #153''' on January 11, 1935. "
        "The building has HABS documentation at the Library of Congress "
        "([https://www.loc.gov/item/ca1081/ HABS CA-1081])."
    ),
    "sources": [
        "National Register of Historic Places nomination, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/71000204 71000204] (February 12, 1971)",
        "California Historical Landmark #153, California Office of Historic Preservation (designated January 11, 1935)",
        "Historic American Buildings Survey, [https://www.loc.gov/item/ca1081/ HABS CA-1081], Library of Congress",
        "Solano County GIS Address Points Shapefile (address and coordinates)",
    ],
}

# ──────────────────────────────────────────────────────────────────────
# Site/Landmark CHLs (no standard street address — create new pages)
# ──────────────────────────────────────────────────────────────────────

SITE_LANDMARKS = [
    {
        "page_title": "California Historical Landmark 175: First Protestant Church in California",
        "chl_number": "175",
        "location": "Benicia City Park, K Street between 1st and 2nd Streets",
        "summary": (
            "'''California Historical Landmark #175''' marks the site where the First "
            "Presbyterian Church of Benicia was organized in 1849, making it the first "
            "Protestant church established in California. The original church building no "
            "longer stands; the site is now part of Benicia City Park on K Street between "
            "First and Second Streets."
        ),
        "sources": [
            "California Historical Landmark #175, California Office of Historic Preservation",
        ],
    },
    {
        "page_title": "California Historical Landmark 176: Benicia Arsenal",
        "chl_number": "176",
        "location": "Intersection of Adams and Jefferson Streets (main gate of port area)",
        "summary": (
            "'''California Historical Landmark #176''' recognizes the Benicia Arsenal, a "
            "440-acre military reservation established in 1849. Captain Charles P. Stone "
            "established it as an ordnance depot in August 1851. The Arsenal is also listed "
            "on the '''National Register of Historic Places''' as a historic district "
            "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/76000534 76000534], "
            "listed November 7, 1976) with 23 contributing buildings.\n\n"
            "Key structures within the Arsenal include:\n"
            "* '''Post Hospital''' (1856) — First U.S. military hospital on the Pacific Coast\n"
            "* '''Storehouse / Clock Tower''' (1859)\n"
            "* '''Camel Barn''' (1854/1863) — Originally built to house camels imported by "
            "the U.S. Army for desert transport experiments\n"
            "* '''Commanding Officer's Quarters''' (1860) — A 20-room Greek Revival mansion\n"
            "* '''Lieutenant's Quarters''' (1861)\n"
            "* '''Duplex Officers' Quarters''' (1872)\n\n"
            "Four buildings along Jefferson Ridge form what has been called the most impressive "
            "ensemble of mid-19th century military architecture still largely intact on the "
            "Pacific Coast. The Arsenal was deactivated in 1964 and transferred to the City "
            "of Benicia in 1965."
        ),
        "sources": [
            "National Register of Historic Places nomination (Historic District), Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/76000534 76000534] (November 7, 1976)",
            "California Historical Landmark #176, California Office of Historic Preservation",
            "Historic American Buildings Survey records: [https://www.loc.gov/item/ca1059/ HABS CA-1059] (Commanding Officer's Quarters), [https://www.loc.gov/item/ca1062/ HABS CA-1062] (Duplex Officers' Quarters), [https://www.loc.gov/item/ca1058/ HABS CA-1058] (Shop Buildings), [https://www.loc.gov/item/ca1076/ HABS CA-1076] (Dock), Library of Congress",
        ],
    },
    {
        "page_title": "California Historical Landmark 177: Benicia Barracks",
        "chl_number": "177",
        "location": "Francesca Terrace Park, 711 Hillcrest Avenue",
        "summary": (
            "'''California Historical Landmark #177''' marks the site of the Benicia Barracks, "
            "established in 1849. The Barracks served as headquarters for the U.S. Army's "
            "Department of the Pacific from 1851 to 1857. A commemorative plaque is located "
            "at Francesca Terrace Park, 711 Hillcrest Avenue."
        ),
        "sources": [
            "California Historical Landmark #177, California Office of Historic Preservation",
        ],
    },
    {
        "page_title": "California Historical Landmark 795: Benicia Seminary",
        "chl_number": "795",
        "location": "City park, Military West Street between 1st and 2nd Streets",
        "summary": (
            "'''California Historical Landmark #795''' marks the birthplace of Mills College. "
            "The Young Ladies' Seminary of Benicia was founded here in 1852. Cyrus and Susan "
            "Mills acquired the seminary in 1865 and relocated it to Oakland in 1871, where "
            "it became Mills College. The original seminary site is now a city park on Military "
            "West Street between First and Second Streets.\n\n"
            "As CHL #795 (designated after #770), this site is automatically listed on the "
            "'''California Register of Historical Resources'''."
        ),
        "sources": [
            "California Historical Landmark #795, California Office of Historic Preservation",
        ],
    },
    {
        "page_title": "California Historical Landmark 973: Turner-Robertson Shipyard",
        "chl_number": "973",
        "location": "Matthew Turner Shipyard Park, foot of West 12th Street",
        "summary": (
            "'''California Historical Landmark #973''' marks the site of the Turner/Robertson "
            "Shipyard (1883–1918) at the foot of West 12th Street. Matthew Turner relocated his "
            "shipyard from San Francisco to Benicia in 1882. Turner was the most prolific wooden "
            "shipbuilder in North America, constructing 228 vessels in his career, 169 of which "
            "were launched from this Benicia yard.\n\n"
            "James Robertson purchased the shipyard from Turner in 1913 and operated it until "
            "1918. The site is now Matthew Turner Shipyard Park.\n\n"
            "The nearby archaeological site of the whaling bark '''Stamboul''' (NRHP Reference "
            "#[https://npgallery.nps.gov/AssetDetail/NRIS/88002030 88002030]) is located at "
            "this shipyard. Turner grounded the three-masted bark (built 1843, Medford, "
            "Massachusetts) here circa 1882 for use as a work platform; the vessel's skeleton "
            "is visible at ebb tide.\n\n"
            "As CHL #973 (designated after #770), this site is automatically listed on the "
            "'''California Register of Historical Resources'''."
        ),
        "sources": [
            "California Historical Landmark #973, California Office of Historic Preservation",
            "National Register of Historic Places nomination for Stamboul (Whaling Bark) Site, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/88002030 88002030] (November 2, 1988)",
        ],
    },
]


def build_property_page(prop: dict, existing_apn: str = "", existing_lat: str = "", existing_lng: str = "") -> str:
    """Build enriched property page content (for properties with street addresses)."""
    f = prop["fields"].copy()
    if existing_apn:
        f["APN"] = existing_apn
    if existing_lat and "Latitude" not in f:
        f["Latitude"] = existing_lat
    if existing_lng and "Longitude" not in f:
        f["Longitude"] = existing_lng

    template_parts = []
    for key in [
        "Current Address", "APN", "Block Number", "Lot Number",
        "Year Built", "Year Built Approximate", "Architectural Style",
        "Stories", "Construction Material", "Historic Status",
        "Current Use", "Original Use", "Builder", "Architect",
        "Latitude", "Longitude", "Survey Date", "Data Confidence",
    ]:
        if key in f and f[key]:
            template_parts.append(f"|{key}={f[key]}")

    template_call = "{{Property\n" + "\n".join(template_parts) + "\n}}"
    sources_list = "\n".join(f"* {s}" for s in prop.get("sources", []))

    # Designations
    designations = []
    if prop.get("nrhp_ref"):
        designations.append(
            f"* '''National Register of Historic Places''' — Reference "
            f"#[https://npgallery.nps.gov/AssetDetail/NRIS/{prop['nrhp_ref']} "
            f"{prop['nrhp_ref']}] (listed {prop.get('nrhp_date', 'date unknown')})"
        )
    if prop.get("chl_number"):
        designations.append(
            f"* '''California Historical Landmark #{prop['chl_number']}'''"
        )

    designation_section = ""
    if designations:
        designation_section = "== Designations ==\n" + "\n".join(designations) + "\n\n"

    addr = f["Current Address"]
    parts = addr.split(" ", 1)
    street_cat = parts[1].upper() if len(parts) > 1 else ""

    content = f"""{template_call}

Also known as: '''{prop['common_name']}'''

== Summary ==
{prop['summary']}

{designation_section}== Historical Significance ==
{prop['significance']}

== Historical Addresses ==
{{| class="wikitable"
! Period !! Address !! Source
|-
| Current || {addr} || Solano County GIS Address Points
|}}

== Physical Description ==
''Detailed physical description to be added from DPR 523 survey forms and HABS documentation.''

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
{sources_list}

== Notes ==
''Add researcher notes, questions, or contradictions to investigate.''

[[Category:Properties]]
[[Category:Properties on {street_cat}]]"""
    return content


def build_site_page(landmark: dict) -> str:
    """Build a wiki page for a CHL site (not a standard property)."""
    sources_list = "\n".join(f"* {s}" for s in landmark.get("sources", []))

    content = f"""= California Historical Landmark #{landmark['chl_number']} =

'''Location:''' {landmark['location']}

== Summary ==
{landmark['summary']}

== Location ==
{landmark['location']}

== Sources ==
{sources_list}

== Notes ==
''Add researcher notes, questions, or contradictions to investigate.''

[[Category:California Historical Landmarks]]
[[Category:Landmarks]]"""
    return content


class WikiClient:
    """Minimal wiki client with token refresh."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url
        self.session = requests.Session()
        self.csrf_token = None
        self.calls_since_refresh = 0
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

        self._refresh_token()

    def _refresh_token(self):
        resp = self.session.get(self.api_url, params={
            "action": "query", "meta": "tokens", "format": "json",
        })
        resp.raise_for_status()
        self.csrf_token = resp.json()["query"]["tokens"]["csrftoken"]
        self.calls_since_refresh = 0

    def edit_page(self, title: str, content: str, summary: str) -> bool:
        if self.calls_since_refresh >= 50:
            self._refresh_token()

        resp = self.session.post(self.api_url, data={
            "action": "edit", "title": title, "text": content,
            "token": self.csrf_token, "format": "json",
            "summary": summary, "bot": True,
        })
        resp.raise_for_status()
        self.calls_since_refresh += 1

        result = resp.json()
        if "error" in result:
            code = result["error"].get("code", "")
            if code == "badtoken":
                self._refresh_token()
                return self.edit_page(title, content, summary)
            print(f"  ERROR on {title}: {result['error']}")
            return False

        return result.get("edit", {}).get("result") == "Success"

    def get_page_content(self, title: str):
        resp = self.session.get(self.api_url, params={
            "action": "query", "titles": title,
            "prop": "revisions", "rvprop": "content", "rvslots": "main",
            "format": "json",
        })
        resp.raise_for_status()
        pages = resp.json()["query"]["pages"]
        for pid, pdata in pages.items():
            if int(pid) < 0:
                return None
            return pdata["revisions"][0]["slots"]["main"]["*"]
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Write CHL data into wiki")
    parser.add_argument("--wiki-url", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    env_path = PROJECT_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip('"')

    api_url = args.wiki_url or env_vars.get("WIKI_SERVER", "http://localhost:8080") + "/api.php"
    username = args.user or env_vars.get("WIKI_ADMIN_USER", "Admin")
    password = args.password or env_vars.get("WIKI_ADMIN_PASSWORD", "")

    if not password:
        print("ERROR: No password provided.")
        sys.exit(1)

    print(f"Wiki API: {api_url}")

    if args.dry_run:
        print("\n=== DRY RUN ===\n")
        content = build_property_page(CAPITOL, "SAMPLE_APN", "38.0501", "-122.1588")
        print(f"--- {CAPITOL['page_title']} ---")
        print(f"  Length: {len(content)} chars")
        for lm in SITE_LANDMARKS:
            content = build_site_page(lm)
            print(f"--- {lm['page_title']} ---")
            print(f"  Length: {len(content)} chars")
        return

    wiki = WikiClient(api_url, username, password)
    print("Authenticated.\n")

    updated = 0
    created = 0
    errors = 0

    # 1. Update Benicia Capitol stub
    print("=== Updating Benicia Capitol ===")
    existing = wiki.get_page_content(CAPITOL["page_title"])
    apn = lat = lng = ""
    if existing:
        for line in existing.split("\n"):
            if "|APN=" in line:
                apn = line.split("=", 1)[1].strip()
            if "|Latitude=" in line:
                lat = line.split("=", 1)[1].strip()
            if "|Longitude=" in line:
                lng = line.split("=", 1)[1].strip()

    content = build_property_page(CAPITOL, apn, lat, lng)
    ok = wiki.edit_page(
        CAPITOL["page_title"], content,
        f"Update with NRHP/CHL data: {CAPITOL['common_name']}"
    )
    if ok:
        updated += 1
        print(f"  [OK] Updated: {CAPITOL['page_title']} ({CAPITOL['common_name']})")
    else:
        errors += 1
        print(f"  [FAIL] {CAPITOL['page_title']}")

    # 2. Create CHL site pages
    print("\n=== Creating CHL Site Pages ===")
    for lm in SITE_LANDMARKS:
        content = build_site_page(lm)
        ok = wiki.edit_page(
            lm["page_title"], content,
            f"Create CHL #{lm['chl_number']} page"
        )
        if ok:
            created += 1
            print(f"  [OK] Created: {lm['page_title']}")
        else:
            errors += 1
            print(f"  [FAIL] {lm['page_title']}")
        time.sleep(0.2)

    # 3. Create the "California Historical Landmarks" category page if it doesn't exist
    cat_content = wiki.get_page_content("Category:California Historical Landmarks")
    if not cat_content:
        cat_text = (
            "This category lists all '''California Historical Landmarks''' located in Benicia.\n\n"
            "California Historical Landmarks are sites, buildings, features, or events that are "
            "of statewide significance and have anthropological, cultural, military, political, "
            "architectural, economic, scientific or technical, religious, experimental, or other value. "
            "Properties designated CHL #770 and above are automatically listed on the California "
            "Register of Historical Resources.\n\n"
            "[[Category:Historic Designations]]"
        )
        ok = wiki.edit_page(
            "Category:California Historical Landmarks", cat_text,
            "Create California Historical Landmarks category"
        )
        if ok:
            created += 1
            print(f"  [OK] Created: Category:California Historical Landmarks")

    print(f"\n=== Complete ===")
    print(f"  Updated: {updated}")
    print(f"  Created: {created}")
    print(f"  Errors:  {errors}")


if __name__ == "__main__":
    main()
