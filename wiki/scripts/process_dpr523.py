#!/usr/bin/env python3
"""
process_dpr523.py - Download DPR 523 survey PDFs from City of Benicia,
extract structured data, and write to wiki property stubs.

Phase 1: Download and parse PDFs → save to dpr523_data.json
Phase 2: Write extracted data into wiki stubs

Usage:
  python3 scripts/process_dpr523.py --extract    # Download PDFs, extract data
  python3 scripts/process_dpr523.py --write      # Write data to wiki
  python3 scripts/process_dpr523.py --extract --write  # Both
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
PDF_DIR = DATA_DIR / "dpr523_pdfs"
OUTPUT_FILE = DATA_DIR / "dpr523_data.json"

BASE_URL = "https://www.ci.benicia.ca.us"
PDF_PATH_PREFIX = "/vertical/sites/%7BF991A639-AAED-4E1A-9735-86EA195E2C8D%7D/uploads/"

# ──────────────────────────────────────────────────────────────────────
# Master index of all DPR 523 PDFs from the city website
# link_text | pdf_filename | normalized_wiki_address
# ──────────────────────────────────────────────────────────────────────

DPR523_INDEX = [
    # 1st Street
    ("90 First - SP Depot", "90First-SPDepot.PDF", "90 First Street"),
    ("123 First", "123First.PDF", "123 First Street"),
    ("305 First", "305First.PDF", "305 First Street"),
    ("307 First", "307First.PDF", "307 First Street"),
    ("309 First", "309First.PDF", "309 First Street"),
    ("333 First", "333First.PDF", "333 First Street"),
    ("401 First", "401First.PDF", "401 First Street"),
    ("415 First", "415First.PDF", "415 First Street"),
    ("431-439 First", "431-439First.PDF", "431 First Street"),
    ("440 First", "440First.PDF", "440 First Street"),
    ("501 First", "501First.PDF", "501 First Street"),
    ("601 First", "601First.PDF", "601 First Street"),
    ("608 First", "608First.PDF", "608 First Street"),
    ("620 First", "620First.PDF", "620 First Street"),
    ("621-625 First", "621-625First.PDF", "621 First Street"),
    ("622 First", "622First.PDF", "622 First Street"),
    ("627-639 First", "627-639First.PDF", "627 First Street"),
    ("632 First", "632First.PDF", "632 First Street"),
    ("634-636 First", "634-636First.PDF", "634 First Street"),
    ("638 First", "638First.PDF", "638 First Street"),
    ("700 First", "700First.PDF", "700 First Street"),
    ("710 First", "710First.PDF", "710 First Street"),
    ("718 First", "718First.PDF", "718 First Street"),
    ("726-736 First", "726-736First.PDF", "726 First Street"),
    ("727 First", "727First.PDF", "727 First Street"),
    ("733-739 First", "733-739First.PDF", "733 First Street"),
    ("800 First", "800First.PDF", "800 First Street"),
    ("818 First", "818_First_Street.pdf", "818 First Street"),
    ("820 First", "820First.PDF", "820 First Street"),
    ("828 First", "828First.PDF", "828 First Street"),
    ("901-903 First", "901-903First.PDF", "901 First Street"),
    ("905-907 First", "905-907-First.PDF", "905 First Street"),
    ("909-911 First", "909-911First.PDF", "909 First Street"),
    ("915 First", "915First.PDF", "915 First Street"),
    ("917-919 First", "917-919First.PDF", "917 First Street"),
    ("935 First", "935First.PDF", "935 First Street"),
    ("1036 First", "1036First.PDF", "1036 First Street"),
    ("1040 First", "1040First.PDF", "1040 First Street"),
    # 2nd Street
    ("532 East 2nd", "532East2nd.PDF", "532 East 2nd Street"),
    ("600 East 2nd", "600East2nd.PDF", "600 East 2nd Street"),
    ("622 East 2nd", "622East2nd.PDF", "622 East 2nd Street"),
    ("640 East 2nd", "640East2nd.PDF", "640 East 2nd Street"),
    ("900 East 2nd", "900East2nd.PDF", "900 East 2nd Street"),
    ("701 West 2nd", "701West2nd.PDF", "701 West 2nd Street"),
    ("717 West 2nd", "717West2nd.PDF", "717 West 2nd Street"),
    ("735 West 2nd", "735West2nd.PDF", "735 West 2nd Street"),
    ("925 West 2nd", "925West2nd.PDF", "925 West 2nd Street"),
    ("932 West 2nd", "932West2nd.PDF", "932 West 2nd Street"),
    ("1025 West 2nd", "1025West2nd.PDF", "1025 West 2nd Street"),
    ("1029 West 2nd", "1029West2nd.PDF", "1029 West 2nd Street"),
    ("1101 West 2nd", "1101West2nd.PDF", "1101 West 2nd Street"),
    ("1121 West 2nd", "1121West2nd.PDF", "1121 West 2nd Street"),
    ("1135 West 2nd", "1135West2nd.PDF", "1135 West 2nd Street"),
    # 3rd Street
    ("703 West 3rd", "703West3rd.PDF", "703 West 3rd Street"),
    ("715 West 3rd", "715West3rd.PDF", "715 West 3rd Street"),
    ("745 West 3rd", "745West3rd.PDF", "745 West 3rd Street"),
    ("903 West 3rd", "903West3rd.PDF", "903 West 3rd Street"),
    ("916 West 3rd", "916West3rd.PDF", "916 West 3rd Street"),
    # 5th & 6th Street
    ("803-811 East 5th", "803-811East5th.PDF", "803 East 5th Street"),
    ("811 East 6th", "811East6th.PDF", "811 East 6th Street"),
    # D Street
    ("126 East D", "126EastD.PDF", "126 East D Street"),
    ("142-144 East D", "142-144EastD.PDF", "142 East D Street"),
    ("149 East D", "149EastD.PDF", "149 East D Street"),
    ("150 East D", "150EastD.PDF", "150 East D Street"),
    ("159 East D", "159EastD.PDF", "159 East D Street"),
    ("161 East D", "161EastD.PDF", "161 East D Street"),
    ("185 East D", "185EastD.PDF", "185 East D Street"),
    ("195 East D", "195EastD.PDF", "195 East D Street"),
    ("120 West D", "120WestD.PDF", "120 West D Street"),
    ("123 West D", "123WestD.PDF", "123 West D Street"),
    ("131 West D", "131WestD.PDF", "131 West D Street"),
    ("145 West D", "145WestD.PDF", "145 West D Street"),
    # E Street
    ("110 East E", "110EastESurvey.PDF", "110 East E Street"),
    ("125 East E", "125EastESurvey.PDF", "125 East E Street"),
    ("129 East E", "129EastESurvey.PDF", "129 East E Street"),
    ("133-137 East E", "133-137EastESurvey.PDF", "133 East E Street"),
    ("141 East E", "141EastESurvey.PDF", "141 East E Street"),
    ("130 West E", "130WestESurvey.PDF", "130 West E Street"),
    ("133 West E", "133WestESurvey.PDF", "133 West E Street"),
    ("143 West E", "143WestESurvey.PDF", "143 West E Street"),
    ("153 West E", "153WestESurvey.PDF", "153 West E Street"),
    # F Street
    ("117 East F", "117EastFSurvey.PDF", "117 East F Street"),
    ("125 East F", "125EastFSurvey.PDF", "125 East F Street"),
    ("141 East F", "141EastFSurvey.PDF", "141 East F Street"),
    ("157 East F", "157EastFSurvey.PDF", "157 East F Street"),
    ("165 East F", "165EastFSurvey.PDF", "165 East F Street"),
    ("175 East F", "175EastFSurvey.PDF", "175 East F Street"),
    ("185 East F", "185EastFSurvey.PDF", "185 East F Street"),
    ("190 East F", "190EastFSurvey.PDF", "190 East F Street"),
    ("128 West F", "128WestFSurvey.PDF", "128 West F Street"),
    ("138 West F", "138WestFSurvey.PDF", "138 West F Street"),
    ("141 West F", "141WestFSurvey.PDF", "141 West F Street"),
    ("148 West F", "148WestFSurvey.PDF", "148 West F Street"),
    ("149 West F", "149WestFSurvey.PDF", "149 West F Street"),
    ("165 West F", "165WestFSurvey.PDF", "165 West F Street"),
    ("173 West F", "173WestFSurvey.PDF", "173 West F Street"),
    ("179-181 West F", "179-181WestFSurvey.PDF", "179 West F Street"),
    # G Street
    ("133 East G", "133EastGSurvey.PDF", "133 East G Street"),
    ("140-142 East G", "140-142EastGSurvey.PDF", "140 East G Street"),
    ("141 East G", "141EastGSurvey.PDF", "141 East G Street"),
    ("149 East G", "149EastGSurvey.PDF", "149 East G Street"),
    ("150 East G", "150EastGSurvey.PDF", "150 East G Street"),
    ("157 East G", "157EastGSurvey.PDF", "157 East G Street"),
    ("164 East G", "164EastGSurvey.PDF", "164 East G Street"),
    ("172 East G", "172EastGSurvey.PDF", "172 East G Street"),
    ("191 East G", "191EastGSurvey.PDF", "191 East G Street"),
    ("103 West G", "103WestGSurvey.PDF", "103 West G Street"),
    ("110 West G", "110WestGSurvey.PDF", "110 West G Street"),
    ("130 West G", "130WestGSurvey.PDF", "130 West G Street"),
    ("135 West G", "135WestGSurvey.PDF", "135 West G Street"),
    ("140 West G", "140WestGSurvey.PDF", "140 West G Street"),
    ("149 West G", "149WestGSurvey.PDF", "149 West G Street"),
    ("150 West G", "150WestGSurvey.PDF", "150 West G Street"),
    ("153 West G", "153WestGSurvey.PDF", "153 West G Street"),
    ("159 West G", "159WestGSurvey.PDF", "159 West G Street"),
    ("172-182 West G", "172-182WestGSurvey.PDF", "172 West G Street"),
    ("223 West G", "223WestGSurvey.PDF", "223 West G Street"),
    ("241 West G", "241WestGSurvey.PDF", "241 West G Street"),
    ("251 West G", "251WestGSurvey.PDF", "251 West G Street"),
    ("285 West G", "285WestGSurvey.PDF", "285 West G Street"),
    # H Street
    ("132-138 East H", "132-138EastHSurvey.PDF", "132 East H Street"),
    ("141 East H", "141EastHSurvey.PDF", "141 East H Street"),
    ("148 East H", "148EastHSurvey.PDF", "148 East H Street"),
    ("152 East H", "152EastHSurvey.PDF", "152 East H Street"),
    ("164 East H", "164EastHSurvey.PDF", "164 East H Street"),
    ("168 East H", "168EastHSurvey.PDF", "168 East H Street"),
    ("172 East H", "172EastHSurvey.PDF", "172 East H Street"),
    ("180 East H", "180EastHSurvey.PDF", "180 East H Street"),
    ("191 East H", "191EastHSurvey.PDF", "191 East H Street"),
    ("360 East H", "360EastHSurvey.PDF", "360 East H Street"),
    ("368 East H", "368EastHSurvey.PDF", "368 East H Street"),
    ("384 East H", "384EastHSurvey.PDF", "384 East H Street"),
    ("392 East H", "392EastHSurvey.PDF", "392 East H Street"),
    ("400 East H", "400EastHSurvey.PDF", "400 East H Street"),
    ("448 East H", "448EastHSurvey.PDF", "448 East H Street"),
    ("451-455 East H", "451-455EastHSurvey.PDF", "451 East H Street"),
    ("456 East H", "456EastHSurvey.PDF", "456 East H Street"),
    ("464 East H", "464EastHSurvey.PDF", "464 East H Street"),
    ("465 East H", "465EastHSurvey.PDF", "465 East H Street"),
    ("472 East H", "472EastHSurvey.PDF", "472 East H Street"),
    ("480 East H", "480EastHSurvey.PDF", "480 East H Street"),
    ("486 East H", "486EastHSurvey.PDF", "486 East H Street"),
    ("535 East H", "535EastHSurvey.PDF", "535 East H Street"),
    ("551 East H", "551EastHSurvey.PDF", "551 East H Street"),
    ("575 East H", "575EastHSurvey.PDF", "575 East H Street"),
    ("583 East H", "583EastHSurvey.PDF", "583 East H Street"),
    ("120-128 West H", "120-128WestHSurvey.PDF", "120 West H Street"),
    ("131 West H", "131WestHSurvey.PDF", "131 West H Street"),
    ("134 West H", "134WestHSurvey.PDF", "134 West H Street"),
    ("141 West H", "141WestHSurvey.PDF", "141 West H Street"),
    ("150 West H", "150WestHSurvey.PDF", "150 West H Street"),
    ("160 West H", "160WestHSurvey.PDF", "160 West H Street"),
    ("161 West H", "161WestHSurvey.PDF", "161 West H Street"),
    ("166 West H", "166WestHSurvey.PDF", "166 West H Street"),
    ("171 West H", "171WestHSurvey.PDF", "171 West H Street"),
    ("175 West H", "175WestHSurvey.PDF", "175 West H Street"),
    ("176 West H", "176WestHSurvey.PDF", "176 West H Street"),
    ("180 West H", "180WestHSurvey.PDF", "180 West H Street"),
    ("181 West H", "181WestHSurvey.PDF", "181 West H Street"),
    ("185 West H", "185WestHSurvey.PDF", "185 West H Street"),
    ("192 West H", "192WestHSurvey.PDF", "192 West H Street"),
    ("215 West H", "215WestHSurvey.PDF", "215 West H Street"),
    ("225 West H", "225WestHSurvey.PDF", "225 West H Street"),
    ("226 West H", "226WestHSurvey.PDF", "226 West H Street"),
    ("242-248 West H", "242-248WestHSurvey.PDF", "242 West H Street"),
    ("245 West H", "245WestHSurvey.PDF", "245 West H Street"),
    ("250 West H", "250WestHSurvey.PDF", "250 West H Street"),
    ("257 West H", "257WestHSurvey.PDF", "257 West H Street"),
    ("260 West H", "260WestHSurvey.PDF", "260 West H Street"),
    ("267 West H", "267WestHSurvey.PDF", "267 West H Street"),
    ("270 West H", "270WestHSurvey.PDF", "270 West H Street"),
    ("277 West H", "277WestHSurvey.PDF", "277 West H Street"),
    ("283 West H", "283WestHSurvey.PDF", "283 West H Street"),
    # I Street
    ("125 East I", "125EastISurvey.PDF", "125 East I Street"),
    ("145 East I", "145EastISurvey.PDF", "145 East I Street"),
    ("155 East I", "155EastISurvey.PDF", "155 East I Street"),
    ("159 East I", "159EastISurvey.PDF", "159 East I Street"),
    ("160 East I", "160EastISurvey.PDF", "160 East I Street"),
    ("163 East I", "163EastISurvey.PDF", "163 East I Street"),
    ("172 East I", "172EastISurvey.PDF", "172 East I Street"),
    ("182 East I", "182EastISurvey.PDF", "182 East I Street"),
    ("183 East I", "183EastISurvey.PDF", "183 East I Street"),
    ("195 East I", "195EastISurvey.PDF", "195 East I Street"),
    ("475 East I", "475EastISurvey.PDF", "475 East I Street"),
    ("117 West I", "117WestISurvey.PDF", "117 West I Street"),
    ("126 West I", "126WestISurvey.PDF", "126 West I Street"),
    ("140 West I", "140WestISurvey.PDF", "140 West I Street"),
    ("145 West I", "145WestISurvey.PDF", "145 West I Street"),
    ("150 West I", "150WestISurvey.PDF", "150 West I Street"),
    ("153 West I", "153WestISurvey.PDF", "153 West I Street"),
    ("160 West I", "160WestISurvey.PDF", "160 West I Street"),
    ("216 West I", "216WestISurvey.PDF", "216 West I Street"),
    ("224 West I", "224WestISurvey.PDF", "224 West I Street"),
    ("225 West I", "225WestISurvey.PDF", "225 West I Street"),
    ("233 West I", "233WestISurvey.PDF", "233 West I Street"),
    ("241 West I", "241WestISurvey.PDF", "241 West I Street"),
    ("242 West I", "242WestISurvey.PDF", "242 West I Street"),
    ("262 West I", "262WestISurvey.PDF", "262 West I Street"),
    ("281 West I", "281WestISurvey.PDF", "281 West I Street"),
    ("282 West I", "282WestISurvey.PDF", "282 West I Street"),
    ("292 West I", "292WestISurvey.PDF", "292 West I Street"),
    ("293 West I", "293WestISurvey.PDF", "293 West I Street"),
    # J Street
    ("107 East J", "107EastJSurvey.PDF", "107 East J Street"),
    ("120-122 East J Church", "120-122EastJSurvey.PDF", "120 East J Street"),
    ("121 East J", "121EastJSurvey.PDF", "121 East J Street"),
    ("130 East J", "130EastJSurvey.PDF", "130 East J Street"),
    ("135 East J", "135EastJSurvey.PDF", "135 East J Street"),
    ("145 East J", "145EastJSurvey.PDF", "145 East J Street"),
    ("155-157 East J", "155-157EastJSurvey.PDF", "155 East J Street"),
    ("106 West J", "106WestJSurvey.PDF", "106 West J Street"),
    ("119 West J", "119WestJSurvey.PDF", "119 West J Street"),
    ("121 West J", "121WestJSurvey.PDF", "121 West J Street"),
    ("135 West J", "135WestJSurvey.PDF", "135 West J Street"),
    ("140 West J", "140WestJSurvey.PDF", "140 West J Street"),
    ("150 West J", "150WestJSurvey.PDF", "150 West J Street"),
    ("151 West J", "151WestJSurvey.PDF", "151 West J Street"),
    ("155 West J", "155WestJSurvey.PDF", "155 West J Street"),
    ("159 West J", "159WestJSurvey.PDF", "159 West J Street"),
    ("160-164 West J", "160-164WestJSurvey.PDF", "160 West J Street"),
    ("163 West J", "163WestJSurvey.PDF", "163 West J Street"),
    ("175-181 West J", "175-181WestJSurvey.PDF", "175 West J Street"),
    ("185 West J", "185WestJSurvey.PDF", "185 West J Street"),
    ("186 West J", "186WestJSurvey.PDF", "186 West J Street"),
    ("191 West J", "191WestJSurvey.PDF", "191 West J Street"),
    ("201-207 West J", "201-207WestJSurvey.PDF", "201 West J Street"),
    ("225 West J", "225WestJSurvey.PDF", "225 West J Street"),
    ("235 West J", "235WestJSurvey.PDF", "235 West J Street"),
    ("241 West J", "241WestJSurvey.PDF", "241 West J Street"),
    ("251 West J", "251WestJSurvey.PDF", "251 West J Street"),
    ("261 West J", "261WestJSurvey.PDF", "261 West J Street"),
    ("271 West J", "271WestJSurvey.PDF", "271 West J Street"),
    ("280 West J", "280WestJSurvey.PDF", "280 West J Street"),
    ("288 West J", "288WestJSurvey.PDF", "288 West J Street"),
    ("292 West J", "292WestJSurvey.PDF", "292 West J Street"),
    ("303 West J", "303WestJSurvey.PDF", "303 West J Street"),
    ("304 West J", "304WestJSurvey.PDF", "304 West J Street"),
    ("375 West J", "375WestJSurvey.PDF", "375 West J Street"),
    ("385 West J", "385WestJSurvey.PDF", "385 West J Street"),
    ("395 West J", "395WestJSurvey.PDF", "395 West J Street"),
    ("401 West J", "401WestJSurvey.PDF", "401 West J Street"),
    ("402 West J", "402WestJSurvey.PDF", "402 West J Street"),
    ("405 West J", "405WestJSurvey.PDF", "405 West J Street"),
    ("410 West J", "410WestJSurvey.PDF", "410 West J Street"),
    ("419 West J", "419WestJSurvey.PDF", "419 West J Street"),
    ("420 West J", "420WestJSurvey.PDF", "420 West J Street"),
    ("430 West J", "430WestJSurvey.PDF", "430 West J Street"),
    ("440 West J", "440WestJSurvey.PDF", "440 West J Street"),
    ("441 West J", "441WestJSurvey.PDF", "441 West J Street"),
    ("453 West J", "453WestJSurvey.PDF", "453 West J Street"),
    ("470 West J", "470WestJSurvey.PDF", "470 West J Street"),
    # K Street
    ("240 East K", "240EastKSurvey.PDF", "240 East K Street"),
    ("301 East K", "301EastKSurvey.PDF", "301 East K Street"),
    ("315 East K", "315EastKSurvey.PDF", "315 East K Street"),
    ("325 East K", "325EastKSurvey.PDF", "325 East K Street"),
    ("333 East K", "333EastKSurvey.PDF", "333 East K Street"),
    ("350 East K BUSD", "350EastKSurveyBUSD.PDF", "350 East K Street"),
    ("351 East K", "351EastKSurvey.PDF", "351 East K Street"),
    ("361 East K", "361EastKSurvey.PDF", "361 East K Street"),
    ("118 West K", "118WestKSurvey.PDF", "118 West K Street"),
    ("130 West K", "130WestKSurvey.PDF", "130 West K Street"),
    ("140 West K", "140WestKSurvey.PDF", "140 West K Street"),
    ("190 West K", "190WestKSurvey.PDF", "190 West K Street"),
    ("230 West K", "230WestKSurvey.PDF", "230 West K Street"),
    ("245 West K", "245WestKSurvey.PDF", "245 West K Street"),
    ("246 West K", "246WestKSurvey.PDF", "246 West K Street"),
    ("250 West K", "250WestKSurvey.pdf", "250 West K Street"),
    ("255 West K", "255WestKSurvey.PDF", "255 West K Street"),
    ("260 West K", "260WestKSurvey.PDF", "260 West K Street"),
    ("290 West K", "290WestKSurvey.PDF", "290 West K Street"),
    ("410 West K", "410WestKSurvey.PDF", "410 West K Street"),
    ("420 West K", "420WestKSurvey.PDF", "420 West K Street"),
    ("690 West K", "690WestKSurvey.PDF", "690 West K Street"),
    # L Street
    ("190 East L", "190EastLSurvey.PDF", "190 East L Street"),
    ("235 East L", "235EastLSurvey.PDF", "235 East L Street"),
    ("250 East L", "250EastLSurvey.PDF", "250 East L Street"),
    # Miscellaneous
    ("36 Wingfield", "36Wingfield.PDF", "36 Wingfield Way"),
]

# NRHP Status Codes → human-readable status
NRHP_STATUS_MAP = {
    "1S": "Landmark",       # Individually listed
    "1D": "Landmark",       # Listed as contributor to district
    "2S": "Landmark",       # Determined eligible individually
    "2D": "Landmark",       # Determined eligible as contributor
    "3S": "Contributor",    # Appears eligible individually
    "3D": "Contributor",    # Appears eligible as contributor
    "3B": "Contributor",    # Appears eligible both
    "3CB": "Contributor",   # Appears eligible as contributor (local)
    "3CD": "Contributor",   # Appears eligible as contributor (local dist)
    "3CS": "Contributor",   # Appears eligible individually (local)
    "4S": "Not Surveyed",   # Appears NRHP ineligible
    "4D": "Not Surveyed",   # Appears NRHP ineligible
    "5S": "Non-Contributor", # Not eligible individually
    "5D": "Non-Contributor", # Not eligible as contributor
    "5S1": "Non-Contributor",
    "5D1": "Non-Contributor",
    "5S3": "Non-Contributor",
    "5D3": "Non-Contributor",
    "6Z": "Not Surveyed",   # Not evaluated
    "7N": "Not Surveyed",   # Needs reevaluation
}


def extract_field(text: str, field_pattern: str, stop_patterns: list = None) -> str:
    """Extract a field value from DPR 523 text."""
    m = re.search(field_pattern, text, re.IGNORECASE | re.DOTALL)
    if not m:
        return ""
    val = m.group(1).strip()
    # Clean up common artifacts
    val = re.sub(r'\s+', ' ', val)
    val = val.strip()
    return val


def parse_dpr523(text: str, link_text: str) -> dict:
    """Parse extracted text from a DPR 523 PDF into structured data."""
    data = {
        "link_text": link_text,
        "address_on_form": "",
        "apn": "",
        "year_built": "",
        "year_approximate": False,
        "architectural_style": "",
        "stories": "",
        "construction_material": "",
        "original_use": "",
        "present_use": "",
        "historic_name": "",
        "common_name": "",
        "nrhp_status_code": "",
        "historic_status": "",
        "description_excerpt": "",
        "significance_excerpt": "",
        "architect": "",
        "builder": "",
        "surveyor": "",
        "survey_date": "",
        "pdf_url": "",
    }

    # Resource Name / Address
    m = re.search(r'\*Resource Name or #:\s*(.+?)(?:\n|P1\.)', text)
    if m:
        data["address_on_form"] = m.group(1).strip()
    else:
        m = re.search(r'Resource Identifier:\s*(.+?)(?:\n|\*)', text)
        if m:
            data["address_on_form"] = m.group(1).strip()

    # APN
    m = re.search(r'APN\s*#?\)?:?\s*([\d\-]+)', text)
    if m:
        data["apn"] = m.group(1).strip()

    # Date Constructed
    m = re.search(r'Date Constructed/Age:\s*(\S+)', text)
    if m:
        year_str = m.group(1).strip()
        # Handle "ca.", "c.", etc.
        if re.match(r'c\.?a?\.?\s*\d{4}', year_str):
            data["year_approximate"] = True
            year_match = re.search(r'(\d{4})', year_str)
            if year_match:
                data["year_built"] = year_match.group(1)
        elif re.match(r'\d{4}', year_str):
            data["year_built"] = year_str[:4]
        elif re.match(r'\d{4}s', year_str):
            data["year_built"] = year_str[:4]
            data["year_approximate"] = True

    # NRHP Status Code
    m = re.search(r'NRHP Status Code:\s*(\w+)', text)
    if m:
        code = m.group(1).strip()
        data["nrhp_status_code"] = code
        data["historic_status"] = NRHP_STATUS_MAP.get(code, "Not Surveyed")

    # Architectural Style (B5)
    m = re.search(r'Architectural Style:\s*(.+?)(?:\n|\*B6)', text, re.DOTALL)
    if m:
        style = m.group(1).strip()
        style = re.sub(r'\s+', ' ', style)
        # Clean up "Vernacular" → more specific if possible
        data["architectural_style"] = style

    # Original Use (B3)
    m = re.search(r'Original Use:\s*(.+?)(?:\n|B4)', text)
    if m:
        data["original_use"] = m.group(1).strip()

    # Present Use (B4)
    m = re.search(r'Present Use:\s*(.+?)(?:\n|\*B5)', text)
    if m:
        data["present_use"] = m.group(1).strip()

    # Historic Name (B1)
    m = re.search(r'Historic Name:\s*(.+?)(?:\n|B2)', text)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ("n/a", "none", "unknown", ""):
            data["historic_name"] = name

    # Common Name (B2)
    m = re.search(r'Common Name:\s*(.+?)(?:\n|B3)', text)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ("n/a", "none", "unknown", ""):
            data["common_name"] = name

    # Architect (B9a)
    m = re.search(r'Architect:\s*(.+?)(?:\n|B9b)', text)
    if m:
        val = m.group(1).strip()
        if val.lower() not in ("unknown", "n/a", "none", ""):
            data["architect"] = val

    # Builder (B9b)
    m = re.search(r'Builder:\s*(.+?)(?:\n|\*B10)', text)
    if m:
        val = m.group(1).strip()
        if val.lower() not in ("unknown", "n/a", "none", ""):
            data["builder"] = val

    # Description (P3a) - first 500 chars
    m = re.search(r'Description\s*\n(.+?)(?:\*P3b|\*P4|Resource Attributes)', text, re.DOTALL)
    if m:
        desc = m.group(1).strip()
        desc = re.sub(r'\s+', ' ', desc)
        data["description_excerpt"] = desc[:500]

    # Significance (B10)
    m = re.search(r'Applicable Criteria:?\s*.+?\n(.+?)(?:B11|Additional Resource)', text, re.DOTALL)
    if m:
        sig = m.group(1).strip()
        sig = re.sub(r'\s+', ' ', sig)
        data["significance_excerpt"] = sig[:500]

    # Surveyor
    m = re.search(r'Recorded by:\s*\n?\s*(.+?)(?:\n\s*\n|\*P9)', text, re.DOTALL)
    if m:
        data["surveyor"] = re.sub(r'\s+', ' ', m.group(1).strip())[:100]

    # Survey Date
    m = re.search(r'Date Recorded:\s*(\S+)', text)
    if m:
        data["survey_date"] = m.group(1).strip()

    # Try to get number of stories from description
    m = re.search(r'(\w+)[- ]stor(?:y|ies)', text, re.IGNORECASE)
    if m:
        stories_word = m.group(1).lower()
        stories_map = {"one": "1", "two": "2", "three": "3", "1": "1", "2": "2", "3": "3",
                       "single": "1", "1½": "1.5", "1-1/2": "1.5", "1.5": "1.5",
                       "2½": "2.5", "2-1/2": "2.5", "2.5": "2.5"}
        data["stories"] = stories_map.get(stories_word, stories_word)

    return data


def download_and_parse(entry: tuple) -> dict:
    """Download a DPR 523 PDF and extract structured data."""
    link_text, filename, wiki_address = entry
    url = BASE_URL + PDF_PATH_PREFIX + filename

    try:
        import fitz
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
        sys.exit(1)

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] Download failed for {filename}: {e}")
        return None

    try:
        doc = fitz.open(stream=r.content, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"  [ERROR] PDF parse failed for {filename}: {e}")
        return None

    data = parse_dpr523(full_text, link_text)
    data["wiki_address"] = wiki_address
    data["pdf_url"] = url
    data["pdf_filename"] = filename

    return data


def extract_all():
    """Download and parse all DPR 523 PDFs."""
    print(f"=== Extracting data from {len(DPR523_INDEX)} DPR 523 PDFs ===\n")

    results = []
    errors = 0

    for i, entry in enumerate(DPR523_INDEX):
        link_text, filename, wiki_address = entry
        print(f"  [{i+1}/{len(DPR523_INDEX)}] {link_text}...", end=" ", flush=True)

        data = download_and_parse(entry)
        if data:
            results.append(data)
            year = data.get("year_built", "?")
            style = data.get("architectural_style", "?")
            status = data.get("historic_status", "?")
            print(f"OK (built {year}, {style}, {status})")
        else:
            errors += 1
            print("FAILED")

        # Be polite to city servers
        time.sleep(0.3)

    # Save results
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n=== Extraction Complete ===")
    print(f"  Parsed: {len(results)}")
    print(f"  Errors: {errors}")
    print(f"  Saved to: {OUTPUT_FILE}")

    return results


def write_to_wiki(data_file: str = None):
    """Write extracted DPR 523 data into wiki property stubs."""
    data_path = Path(data_file) if data_file else OUTPUT_FILE
    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print("Run with --extract first.")
        sys.exit(1)

    with open(data_path) as f:
        records = json.load(f)

    print(f"Loaded {len(records)} DPR 523 records.")

    # Load env
    env_path = PROJECT_DIR / ".env"
    env_vars = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip('"')

    api_url = env_vars.get("WIKI_SERVER", "http://localhost:8080") + "/api.php"
    username = env_vars.get("WIKI_ADMIN_USER", "Admin")
    password = env_vars.get("WIKI_ADMIN_PASSWORD", "")

    if not password:
        print("ERROR: No password.")
        sys.exit(1)

    wiki = WikiClient(api_url, username, password)
    print(f"Wiki API: {api_url}")
    print("Authenticated.\n")

    updated = 0
    skipped = 0
    errors = 0

    for rec in records:
        wiki_addr = rec.get("wiki_address", "")
        if not wiki_addr:
            continue

        # Get existing page
        existing = wiki.get_page_content(wiki_addr)
        if existing is None:
            # Page doesn't exist in wiki — skip (we only update existing stubs)
            print(f"  [SKIP] {wiki_addr} — no wiki page")
            skipped += 1
            continue

        # Check if already enriched (has Data Confidence=High)
        if "|Data Confidence=High" in existing:
            print(f"  [SKIP] {wiki_addr} — already enriched")
            skipped += 1
            continue

        # Build updated page content
        content = build_enriched_page(rec, existing)
        if not content:
            skipped += 1
            continue

        pdf_url = rec.get("pdf_url", "")
        summary = f"Enrich with DPR 523 survey data (Roland-Nawi Associates, 2004)"

        ok = wiki.edit_page(wiki_addr, content, summary)
        if ok:
            updated += 1
            year = rec.get("year_built", "?")
            style = rec.get("architectural_style", "?")
            print(f"  [OK] {wiki_addr} (built {year}, {style})")
        else:
            errors += 1
            print(f"  [FAIL] {wiki_addr}")

        time.sleep(0.1)

    print(f"\n=== Write Complete ===")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")


def build_enriched_page(rec: dict, existing: str) -> str:
    """Build enriched wiki page content from DPR 523 data + existing stub."""
    # Extract existing fields we want to preserve
    apn = ""
    lat = ""
    lng = ""
    for line in existing.split("\n"):
        if "|APN=" in line:
            apn = line.split("=", 1)[1].strip()
        if "|Latitude=" in line:
            lat = line.split("=", 1)[1].strip()
        if "|Longitude=" in line:
            lng = line.split("=", 1)[1].strip()

    wiki_addr = rec["wiki_address"]
    year = rec.get("year_built", "")
    approx = "Yes" if rec.get("year_approximate") else "No" if year else ""
    style = rec.get("architectural_style", "")
    stories = rec.get("stories", "")
    original_use = rec.get("original_use", "")
    present_use = rec.get("present_use", "")
    historic_status = rec.get("historic_status", "")
    architect = rec.get("architect", "")
    builder = rec.get("builder", "")
    desc = rec.get("description_excerpt", "")
    significance = rec.get("significance_excerpt", "")
    historic_name = rec.get("historic_name", "")
    common_name = rec.get("common_name", "")
    survey_date = rec.get("survey_date", "")
    nrhp_code = rec.get("nrhp_status_code", "")
    pdf_url = rec.get("pdf_url", "")
    form_apn = rec.get("apn", "")

    # Use APN from form if we don't have one from GIS, or if GIS one looks different format
    if form_apn and not apn:
        apn = form_apn

    # Build template
    fields = {"Current Address": wiki_addr}
    if apn:
        fields["APN"] = apn
    if year:
        fields["Year Built"] = year
    if approx:
        fields["Year Built Approximate"] = approx
    if style:
        fields["Architectural Style"] = style
    if stories:
        fields["Stories"] = stories
    if historic_status:
        fields["Historic Status"] = historic_status
    if present_use:
        fields["Current Use"] = present_use
    if original_use:
        fields["Original Use"] = original_use
    if architect:
        fields["Architect"] = architect
    if builder:
        fields["Builder"] = builder
    if lat:
        fields["Latitude"] = lat
    if lng:
        fields["Longitude"] = lng
    if survey_date:
        fields["Survey Date"] = survey_date
    fields["Data Confidence"] = "Medium"

    template_parts = []
    for key in [
        "Current Address", "APN", "Block Number", "Lot Number",
        "Year Built", "Year Built Approximate", "Architectural Style",
        "Stories", "Construction Material", "Historic Status",
        "Current Use", "Original Use", "Builder", "Architect",
        "Latitude", "Longitude", "Survey Date", "Data Confidence",
    ]:
        if key in fields and fields[key]:
            template_parts.append(f"|{key}={fields[key]}")

    template_call = "{{Property\n" + "\n".join(template_parts) + "\n}}"

    # Build page sections
    name_line = ""
    if historic_name:
        name_line = f"Also known as: '''{historic_name}'''\n\n"
    elif common_name:
        name_line = f"Also known as: '''{common_name}'''\n\n"

    summary_text = ""
    if desc:
        summary_text = desc
    else:
        summary_text = f"Property at '''{wiki_addr}'''."

    significance_text = ""
    if significance:
        significance_text = significance
    if nrhp_code:
        significance_text += f"\n\nNRHP Status Code from DPR 523 survey: '''{nrhp_code}'''."
    if not significance_text.strip():
        significance_text = "''Not yet researched.''"

    # Source citations
    sources = []
    if pdf_url:
        sources.append(
            f"DPR 523 Historic Property Survey Form, Roland-Nawi Associates "
            f"({survey_date or '2004'}), [{pdf_url} City of Benicia website]"
        )
    sources.append("Solano County GIS Address Points Shapefile (address and coordinates)")
    if apn:
        sources.append(f"APN: {apn}")

    sources_text = "\n".join(f"* {s}" for s in sources)

    addr_parts = wiki_addr.split(" ", 1)
    street_cat = addr_parts[1].upper() if len(addr_parts) > 1 else ""

    content = f"""{template_call}

{name_line}== Summary ==
{summary_text}

== Historical Significance ==
{significance_text}

== Historical Addresses ==
{{| class="wikitable"
! Period !! Address !! Source
|-
| Current || {wiki_addr} || Solano County GIS Address Points
|}}

== Physical Description ==
''Detailed physical description to be added. See the [DPR 523 survey form] linked in Sources for photographs and architectural details.''

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
{sources_text}

== Notes ==
''Add researcher notes, questions, or contradictions to investigate.''

[[Category:Properties]]
[[Category:Properties on {street_cat}]]"""

    return content


class WikiClient:
    """Wiki client with token refresh."""

    def __init__(self, api_url, username, password):
        self.api_url = api_url
        self.session = requests.Session()
        self.csrf_token = None
        self.calls_since_refresh = 0
        self._login(username, password)

    def _login(self, username, password):
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

    def edit_page(self, title, content, summary):
        if self.calls_since_refresh >= 100:
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
            print(f"  ERROR: {result['error']}")
            return False
        return result.get("edit", {}).get("result") == "Success"

    def get_page_content(self, title):
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
    parser = argparse.ArgumentParser(description="Process DPR 523 survey forms")
    parser.add_argument("--extract", action="store_true", help="Download and parse PDFs")
    parser.add_argument("--write", action="store_true", help="Write data to wiki")
    parser.add_argument("--wiki-url", default=None)
    args = parser.parse_args()

    if not args.extract and not args.write:
        print("Specify --extract and/or --write")
        sys.exit(1)

    if args.extract:
        extract_all()

    if args.write:
        write_to_wiki()


if __name__ == "__main__":
    main()
