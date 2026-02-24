#!/usr/bin/env python3
"""
enrich_nrhp.py - Enrich wiki property stubs with NRHP data.

Writes verified National Register of Historic Places data into existing
property stub pages, and creates new pages for NRHP properties that lack
GIS stubs.

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
# NRHP Property Data — verified from NPS NPGallery, California OHP,
# Library of Congress HABS records, and City of Benicia documents.
# ──────────────────────────────────────────────────────────────────────

NRHP_PROPERTIES = [
    {
        "page_title": "90 First Street",
        "exists": True,
        "fields": {
            "Current Address": "90 First Street",
            "Year Built": "1897",
            "Year Built Approximate": "No",
            "Architectural Style": "Western Stick",
            "Stories": "1",
            "Construction Material": "Wood frame",
            "Historic Status": "Landmark",
            "Current Use": "Museum / Community use",
            "Original Use": "Railroad passenger depot",
            "Data Confidence": "High",
        },
        "common_name": "Benicia Southern Pacific Railroad Passenger Depot",
        "nrhp_ref": "100001664",
        "nrhp_date": "September 28, 2017",
        "summary": (
            "The '''Benicia Southern Pacific Railroad Passenger Depot''' at 90 First Street "
            "was constructed in Banta, California in 1897 following the Southern Pacific No. 18 "
            "standard depot plan. It was relocated to Benicia in 1902 and served as the city's "
            "primary passenger and freight station from 1902 to 1930. The building is an example "
            "of the Western Stick style as applied to railroad architecture. The station agent "
            "and family resided in the depot until 1958. The City of Benicia purchased the "
            "building in 1974, and it was rehabilitated between 1999 and 2001."
        ),
        "significance": (
            "Listed on the '''National Register of Historic Places''' on September 28, 2017 "
            "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/100001664 100001664]). "
            "The depot is significant under NRHP Criterion A for its association with Benicia's "
            "transportation history, and Criterion C as an intact example of the Southern Pacific "
            "No. 18 standard depot plan in the Western Stick style."
        ),
        "sources": [
            "National Register of Historic Places nomination, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/100001664 100001664] (September 28, 2017)",
            "Solano County GIS Address Points Shapefile (address and coordinates)",
        ],
    },
    {
        "page_title": "110 West J Street",
        "exists": True,
        "fields": {
            "Current Address": "110 West J Street",
            "Year Built": "1850",
            "Year Built Approximate": "No",
            "Architectural Style": "Vernacular frame",
            "Stories": "2",
            "Construction Material": "Wood frame",
            "Historic Status": "Landmark",
            "Current Use": "Fraternal lodge (Masonic)",
            "Original Use": "Masonic hall",
            "Data Confidence": "High",
        },
        "common_name": "Old Masonic Hall (Benicia Lodge No. 5, F. & A. M.)",
        "nrhp_ref": "72000259",
        "nrhp_date": "March 16, 1972",
        "chl_number": "174",
        "summary": (
            "The '''Old Masonic Hall''' at 110 West J Street is the first purpose-built "
            "Masonic hall erected in California. Construction began in the summer of 1850, "
            "and Benicia Lodge No. 5, F. & A. M. occupied the building on October 14, 1850. "
            "It was formally dedicated on December 27, 1850. The lower floor served as a "
            "courtroom for the Court of Sessions for two years. The lodge sold the building "
            "in 1888 for community use, then reacquired it in 1950 and renovated it. It "
            "remains one of three locations in California where any Masonic lodge may conduct "
            "degree conferral ceremonies."
        ),
        "significance": (
            "Listed on the '''National Register of Historic Places''' on March 16, 1972 "
            "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/72000259 72000259]). "
            "Also designated '''California Historical Landmark #174''': \"First Building "
            "Erected in California by Masonic Lodge for Use as a Hall.\" "
            "The building has HABS documentation at the Library of Congress "
            "([https://www.loc.gov/item/ca1087/ HABS CA-1087])."
        ),
        "sources": [
            "National Register of Historic Places nomination, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/72000259 72000259] (March 16, 1972)",
            "California Historical Landmark #174, California Office of Historic Preservation",
            "Historic American Buildings Survey, [https://www.loc.gov/item/ca1087/ HABS CA-1087], Library of Congress",
            "Solano County GIS Address Points Shapefile (address and coordinates)",
        ],
    },
    {
        "page_title": "135 West G Street",
        "exists": True,
        "fields": {
            "Current Address": "135 West G Street",
            "Year Built": "1850",
            "Year Built Approximate": "Yes",
            "Architectural Style": "Federal",
            "Stories": "2",
            "Construction Material": "Heavy timber frame (mortise and tenon)",
            "Historic Status": "Landmark",
            "Current Use": "Museum (Benicia Capitol State Historic Park)",
            "Original Use": "Residence (converted from hotel section)",
            "Data Confidence": "High",
        },
        "common_name": "Fischer-Hanlon House",
        "nrhp_ref": "79000556",
        "nrhp_date": "1979",
        "chl_number": "880",
        "summary": (
            "The '''Fischer-Hanlon House''' at 135 West G Street was originally part of a "
            "Gold Rush-era hotel. Joseph Fischer, a Swiss-born businessman, purchased a "
            "salvageable portion of the fire-damaged hotel and moved it to this site in 1858. "
            "The building is one of the few surviving examples of heavy timber frame construction "
            "using mortise and tenon joinery, a technique predating balloon framing in California. "
            "Its East Coast Federal styling illustrates the architectural diffusion that occurred "
            "during the Gold Rush as settlers brought building traditions from the eastern states. "
            "Three generations of the Fischer family occupied the home. In 1968, the granddaughters "
            "deeded the house — with its original artifacts and furnishings — to California State "
            "Parks. It is now part of Benicia Capitol State Historic Park."
        ),
        "significance": (
            "Listed on the '''National Register of Historic Places''' in 1979 "
            "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/79000556 79000556]). "
            "Also designated '''California Historical Landmark #880''', cited as an "
            "\"outstanding example of East Coast Federalist styling illustrating architectural "
            "diffusion during the Gold Rush.\" "
            "The building has HABS documentation at the Library of Congress "
            "([https://www.loc.gov/item/ca3635/ HABS CA-3635])."
        ),
        "sources": [
            "National Register of Historic Places nomination, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/79000556 79000556] (1979)",
            "California Historical Landmark #880, California Office of Historic Preservation",
            "Historic American Buildings Survey, [https://www.loc.gov/item/ca3635/ HABS CA-3635], Library of Congress",
            "Solano County GIS Address Points Shapefile (address and coordinates)",
        ],
    },
    {
        "page_title": "285 West G Street",
        "exists": True,
        "fields": {
            "Current Address": "285 West G Street",
            "Year Built": "1890",
            "Year Built Approximate": "Yes",
            "Architectural Style": "Stick/Eastlake",
            "Stories": "2",
            "Construction Material": "Wood frame",
            "Historic Status": "Landmark",
            "Original Use": "Residence",
            "Data Confidence": "High",
        },
        "common_name": "Crooks Mansion",
        "nrhp_ref": "78000795",
        "nrhp_date": "1978",
        "summary": (
            "The '''Crooks Mansion''' at 285 West G Street was built circa 1890 by John E. "
            "Crooks and later acquired by his brother William L. Crooks. William Crooks served "
            "as Mayor of Benicia from 1898 to 1918 and again from 1924 to 1940, and was president "
            "of the People's Bank of Benicia for thirty years. The house is one of the only "
            "remaining examples of the Stick/Eastlake style in Benicia, distinguished by its "
            "waterfront-facing site on West G Street. The Crooks family occupied the house "
            "until 1970."
        ),
        "significance": (
            "Listed on the '''National Register of Historic Places''' in 1978 "
            "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/78000795 78000795]). "
            "The building has HABS documentation at the Library of Congress "
            "([https://www.loc.gov/item/ca1077/ HABS CA-1077])."
        ),
        "sources": [
            "National Register of Historic Places nomination, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/78000795 78000795] (1978)",
            "Historic American Buildings Survey, [https://www.loc.gov/item/ca1077/ HABS CA-1077], Library of Congress",
            "Solano County GIS Address Points Shapefile (address and coordinates)",
        ],
    },
    {
        "page_title": "120 East J Street",
        "exists": False,
        "fields": {
            "Current Address": "120 East J Street",
            "Year Built": "1859",
            "Year Built Approximate": "No",
            "Architectural Style": "Gothic Revival (Carpenter Gothic)",
            "Stories": "1",
            "Construction Material": "Wood frame",
            "Historic Status": "Landmark",
            "Current Use": "Church (Episcopal)",
            "Original Use": "Church (Episcopal)",
            "Architect": "Julian McAllister",
            "Latitude": "38.0492",
            "Longitude": "-122.1578",
            "Data Confidence": "High",
        },
        "common_name": "St. Paul's Episcopal Church",
        "chl_number": "862",
        "summary": (
            "'''St. Paul's Episcopal Church''' at 120 East J Street was designed in 1859 "
            "by Lt. Julian McAllister of the U.S. Army and built by shipwrights of the "
            "Pacific Mail and Steamship Company. The church is an outstanding example of "
            "early California Gothic ecclesiastical architecture, with a notable interior "
            "ceiling that resembles an inverted ship's hull — reflecting the craftsmanship "
            "of its shipwright builders. St. Paul's served as the Cathedral of the Missionary "
            "District of Northern California from 1874 to 1899."
        ),
        "significance": (
            "Designated '''California Historical Landmark #862''' on July 20, 1973, "
            "recognized as an outstanding example of early California Gothic ecclesiastical "
            "architecture. Properties designated CHL #770 and above are automatically listed "
            "on the California Register of Historical Resources. "
            "The building has HABS documentation at the Library of Congress "
            "([https://www.loc.gov/item/ca1072/ HABS CA-1072])."
        ),
        "sources": [
            "California Historical Landmark #862, California Office of Historic Preservation (designated July 20, 1973)",
            "Historic American Buildings Survey, [https://www.loc.gov/item/ca1072/ HABS CA-1072], Library of Congress",
        ],
    },
    {
        "page_title": "165 East D Street",
        "exists": False,
        "fields": {
            "Current Address": "165 East D Street",
            "Year Built": "1855",
            "Year Built Approximate": "Yes",
            "Architectural Style": "Federal",
            "Stories": "1",
            "Construction Material": "Brick",
            "Historic Status": "Landmark",
            "Original Use": "Residence",
            "Latitude": "38.0467",
            "Longitude": "-122.1570",
            "Data Confidence": "High",
        },
        "common_name": "Carr House",
        "nrhp_ref": "79000555",
        "nrhp_date": "September 13, 1979",
        "summary": (
            "The '''Carr House''' at 165 East D Street was one of the very few early masonry "
            "structures in Benicia. It was a one-story brick building with a steep gable roof, "
            "featuring a Federal-style fanlight over the front door. A vaulted brick cistern lay "
            "partly beneath the building. The house was well-documented in Robert Bruegmann's "
            "architectural history of Benicia and by the Historic American Buildings Survey.\n\n"
            "'''Note:''' This building was '''demolished circa 2000''' but remains listed on "
            "the National Register of Historic Places."
        ),
        "significance": (
            "Listed on the '''National Register of Historic Places''' on September 13, 1979 "
            "(Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/79000555 79000555]). "
            "The building had HABS documentation at the Library of Congress "
            "([https://www.loc.gov/item/ca1079/ HABS CA-1079]). "
            "'''Status: Demolished circa 2000.'''"
        ),
        "sources": [
            "National Register of Historic Places nomination, Reference #[https://npgallery.nps.gov/AssetDetail/NRIS/79000555 79000555] (September 13, 1979)",
            "Historic American Buildings Survey, [https://www.loc.gov/item/ca1079/ HABS CA-1079], Library of Congress",
        ],
    },
]


def build_page_content(prop: dict) -> str:
    """Build full wiki page content for an NRHP property."""
    f = prop["fields"]

    # Build the template call
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

    # Common name line
    common_name = prop.get("common_name", "")
    name_line = ""
    if common_name:
        name_line = f"Also known as: '''{common_name}'''\n\n"

    # NRHP / CHL designation box
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
        designation_section = (
            "== Designations ==\n"
            + "\n".join(designations)
            + "\n\n"
        )

    # Sources
    sources_list = "\n".join(f"* {s}" for s in prop.get("sources", []))

    content = f"""{template_call}

{name_line}== Summary ==
{prop['summary']}

{designation_section}== Historical Significance ==
{prop['significance']}

== Historical Addresses ==
{{| class="wikitable"
! Period !! Address !! Source
|-
| Current || {f['Current Address']} || Solano County GIS Address Points
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

[[Category:Properties]]"""

    # Add street category
    addr = f["Current Address"]
    parts = addr.split(" ", 1)
    if len(parts) > 1:
        street = parts[1].upper()
        content += f"\n[[Category:Properties on {street}]]"

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
        """Create or overwrite a page."""
        if self.calls_since_refresh >= 50:
            self._refresh_token()

        resp = self.session.post(self.api_url, data={
            "action": "edit",
            "title": title,
            "text": content,
            "token": self.csrf_token,
            "format": "json",
            "summary": summary,
            "bot": True,
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

    def get_page_content(self, title: str) -> str | None:
        """Get current page content, or None if page doesn't exist."""
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
    parser = argparse.ArgumentParser(description="Enrich wiki stubs with NRHP data")
    parser.add_argument("--wiki-url", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print content but don't write to wiki")
    args = parser.parse_args()

    # Load env
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
    print(f"Properties to enrich: {len(NRHP_PROPERTIES)}")
    print()

    if args.dry_run:
        for prop in NRHP_PROPERTIES:
            content = build_page_content(prop)
            print(f"=== {prop['page_title']} ===")
            print(f"  Common name: {prop.get('common_name', 'N/A')}")
            print(f"  NRHP: {prop.get('nrhp_ref', 'N/A')}")
            print(f"  Exists: {prop['exists']}")
            print(f"  Content length: {len(content)} chars")
            print()
        return

    wiki = WikiClient(api_url, username, password)
    print("Authenticated.\n")

    updated = 0
    created = 0
    errors = 0

    for prop in NRHP_PROPERTIES:
        title = prop["page_title"]
        common_name = prop.get("common_name", "")

        # Preserve APN and coordinates from existing stub if page exists
        if prop["exists"]:
            existing = wiki.get_page_content(title)
            if existing:
                # Extract APN from existing content
                for line in existing.split("\n"):
                    if "|APN=" in line and "APN" not in prop["fields"]:
                        apn = line.split("=", 1)[1].strip()
                        if apn:
                            prop["fields"]["APN"] = apn
                    if "|Latitude=" in line and "Latitude" not in prop["fields"]:
                        lat = line.split("=", 1)[1].strip()
                        if lat:
                            prop["fields"]["Latitude"] = lat
                    if "|Longitude=" in line and "Longitude" not in prop["fields"]:
                        lng = line.split("=", 1)[1].strip()
                        if lng:
                            prop["fields"]["Longitude"] = lng

        content = build_page_content(prop)
        action = "Update" if prop["exists"] else "Create"
        summary = f"{action} with NRHP data: {common_name}"

        ok = wiki.edit_page(title, content, summary)
        if ok:
            if prop["exists"]:
                updated += 1
            else:
                created += 1
            print(f"  [OK] {action}: {title} ({common_name})")
        else:
            errors += 1
            print(f"  [FAIL] {action}: {title}")

        time.sleep(0.2)

    print(f"\n=== Complete ===")
    print(f"  Updated: {updated}")
    print(f"  Created: {created}")
    print(f"  Errors:  {errors}")


if __name__ == "__main__":
    main()
