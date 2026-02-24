#!/usr/bin/env python3
"""
find_missing_parcels.py - Find addresses in the Solano County Parcels shapefile
that are missing from the wiki.

The Address Points layer only has ~4,043 addresses for historic Benicia.
The Parcels layer has assessor data for every taxable lot, including year built,
stories, and use description. This script finds the gap.

The tricky part is address normalization: the Parcels shapefile uses a different
format than Address Points. E.g. parcels have "WEST J" while wiki pages use
"West J Street". This script maps between the two.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import geopandas as gpd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SEED_DIR = DATA_DIR / "seed"

MILITARY_LAT = 38.0555
ARSENAL_BBOX = {"west": -122.152, "east": -122.135, "south": 38.050, "north": 38.060}

# ─── Siteroad → Wiki street name mapping ────────────────────────────────
# Built by comparing Address Points (st_name + st_postyp + st_posdir) against
# Parcels (siteroad). This is the definitive mapping for all siteroad values
# found in the historic area.
#
# Format: "SITEROAD_VALUE": "Wiki Street Format"
# The wiki format includes the full suffix (Street, Avenue, Drive, etc.)

SITEROAD_MAP = {
    # Letter streets (direction prefix + single letter → add "Street")
    "EAST A": "East A Street",
    "EAST B": "East B Street",
    "EAST D": "East D Street",
    "EAST E": "East E Street",
    "EAST F": "East F Street",
    "EAST G": "East G Street",
    "EAST H": "East H Street",
    "EAST I": "East I Street",
    "EAST J": "East J Street",
    "EAST K": "East K Street",
    "EAST L": "East L Street",
    "EAST N": "East N Street",
    "EAST O": "East O Street",
    "EAST S": "East S Street",
    "EAST T": "East T Street",
    "WEST C": "West C Street",
    "WEST D": "West D Street",
    "WEST E": "West E Street",
    "WEST F": "West F Street",
    "WEST G": "West G Street",
    "WEST H": "West H Street",
    "WEST I": "West I Street",
    "WEST J": "West J Street",
    "WEST K": "West K Street",
    "WEST N": "West N Street",

    # Numbered streets (spelled-out → ordinal + "Street")
    "FIRST": "First Street",
    "EAST SECOND": "East 2nd Street",
    "WEST SECOND": "West 2nd Street",
    "EAST THIRD": "East 3rd Street",
    "WEST THIRD": "West 3rd Street",
    "EAST FOURTH": "East 4th Street",
    "WEST FOURTH": "West 4th Street",
    "EAST FIFTH": "East 5th Street",
    "WEST FIFTH": "West 5th Street",
    "EAST SIXTH": "East 6th Street",
    "WEST SIXTH": "West 6th Street",
    "EAST SEVENTH": "East 7th Street",

    # Military (direction goes AFTER the name in wiki)
    "EAST MILITARY": "Military East",
    "WEST MILITARY": "Military West",
    "MILITARY EAST": "Military East",
    "MILITARY WEST": "Military West",
    "MILITARY EAST-H": "Military East",  # special case — intersection notation

    # Named streets with known suffixes (from Address Points st_postyp)
    "ADAMS": "Adams Street",
    "ANDERSON": "Anderson Lane",
    "BAYSHORE": "Bayshore Road",
    "BUCHANAN": "Buchanan Street",
    "BUENA TIERRA": "Buena Tierra Street",
    "CAMEL": "Camel Road",
    "CASA GRANDE": "Casa Grande Street",
    "CLOS DUVALL": "Clos Duvall Court",
    "COMMANDANT'S": "Commandant's Lane",  # Arsenal area
    "CORTE DEL SOL": "Corte Del Sol",     # No suffix in wiki
    "CORTE DORADO": "Corte Dorado",       # No suffix in wiki
    "COVE": "Cove Way",
    "DEL CENTRO": "Del Centro",           # No suffix in wiki
    "EL BONITO": "El Bonito Way",
    "ELANE": "Elane Way",
    "ELM": "Elm Street",
    "FRANCISCA": "Francisca Court",
    "GOLDENSLOPES": "Goldenslopes Court",
    "GRANT": "Grant Street",
    "GULL POINT": "Gull Point Court",
    "HARBOR VISTA": "Harbor Vista Court",
    "HAYES": "Hayes Street",
    "HILLCREST": "Hillcrest Avenue",
    "HOSPITAL": "Hospital Road",
    "JACKSON": "Jackson Street",
    "JEFFERSON": "Jefferson Street",
    "JOHNS": "Johns Place",
    "KUHNLAND": "Kuhland Alley",  # Note: parcels spell it "KUHNLAND", wiki uses "Kuhland"
    "LA CRUZ": "La Cruz Avenue",
    "LA PRENDA": "La Prenda Avenue",
    "LINCOLN": "Lincoln Street",
    "LINDA VISTA": "Linda Vista Avenue",
    "LINDO": "Lindo Street",
    "MADISON": "Madison Street",  # Inferred from Benicia grid
    "MARINA VILLAGE": "Marina Village Way",
    "MCKAY": "Mckay Way",
    "MCKINNEY": "Mckinney Place",
    "MONROE": "Monroe Court",
    "MOUNTVIEW": "Mountview Terrace",
    "OAK": "Oak Road",
    "PACIFICA": "Pacifica Court",
    "PARK": "Park Road",
    "POLK": "Polk Street",
    "RINCONADA": "Rinconada Court",
    "RIVERHILL": "Riverhill Drive",
    "RIVERVIEW": "Riverview Terrace",
    "SEMPLE": "Semple Court",
    "SEMPLES CROSSING": "Semple Crossing",  # Note: parcels say "SEMPLES", wiki says "Semple"
    "SOLANO": "Solano Drive",  # Could also be Solano Square — will check by address
    "ST. AUGUSTINE": "Saint Augustine Drive",  # Address Points use "SAINT AUGUSTINE"
    "ST. CATHERINE'S": "Saint Catherines Lane",  # Address Points use "SAINT CATHERINES"
    "ST. FRANCIS": "St Francis Court",     # Address Points use "ST FRANCIS"
    "TYLER": "Tyler Street",
    "VARNI": "Varni Court",
    "VECINO": "Vecino Street",
    "VIA ALTA": "Via Alta",               # No suffix in wiki
    "VIA MEDIA": "Via Media",             # No suffix in wiki
    "VIEWMONT": "Viewmont Street",
    "VISTA GRANDE": "Vista Grande Avenue",
    "WINGFIELD": "Wingfield Way",
}


def normalize_parcel_address(row):
    """Normalize a parcel situs address to wiki page title format.

    Uses the SITEROAD_MAP for exact siteroad→wiki mapping.
    Falls back to heuristic normalization for unmapped roads.
    """
    num = str(int(row["sitenum"]))
    road = str(row["siteroad"]).strip()
    unit = str(row.get("unitbldg", "")).strip() if row.get("unitbldg") else ""

    # Try exact siteroad mapping first
    if road in SITEROAD_MAP:
        road_norm = SITEROAD_MAP[road]
    else:
        # Fallback: heuristic normalization
        road_parts = road.split()
        normalized = []

        type_map = {
            "ST": "Street", "AVE": "Avenue", "DR": "Drive", "CT": "Court",
            "LN": "Lane", "WAY": "Way", "PL": "Place", "CIR": "Circle",
            "BLVD": "Boulevard", "TER": "Terrace", "RD": "Road",
        }
        dir_map = {
            "W": "West", "WEST": "West", "E": "East", "EAST": "East",
            "N": "North", "NORTH": "North", "S": "South", "SOUTH": "South",
        }

        for part in road_parts:
            up = part.upper()
            if up in dir_map:
                normalized.append(dir_map[up])
            elif up in type_map:
                normalized.append(type_map[up])
            elif len(part) == 1 and part.isalpha():
                normalized.append(part.upper())
            else:
                normalized.append(part.capitalize())

        road_norm = " ".join(normalized)

    title = f"{num} {road_norm}"
    if unit and unit != "None" and unit.strip():
        title += f" {unit.title()}"
    return title


def main():
    # Load parcels shapefile
    parcels_dir = DATA_DIR / "downloads" / "parcels"
    shp_files = list(parcels_dir.glob("**/*.shp"))
    if not shp_files:
        print("ERROR: No parcels shapefile found.")
        sys.exit(1)

    print(f"Loading parcels: {shp_files[0]}")
    p = gpd.read_file(shp_files[0])
    print(f"Total parcels in county: {len(p):,}")

    # Filter to Benicia
    benicia = p[p["sitecity"] == "BENICIA"].copy()
    print(f"Benicia parcels: {len(benicia):,}")

    # Reproject to WGS84
    benicia = benicia.to_crs(epsg=4326)
    benicia["lat"] = benicia.geometry.centroid.y
    benicia["lon"] = benicia.geometry.centroid.x

    # Filter to historic area
    downtown_mask = benicia["lat"] < MILITARY_LAT
    arsenal_mask = (
        (benicia["lon"] >= ARSENAL_BBOX["west"]) &
        (benicia["lon"] <= ARSENAL_BBOX["east"]) &
        (benicia["lat"] >= ARSENAL_BBOX["south"]) &
        (benicia["lat"] <= ARSENAL_BBOX["north"])
    )
    combined = benicia[downtown_mask | arsenal_mask].copy()
    print(f"Historic area parcels: {len(combined):,}")

    # Filter to parcels with actual addresses
    has_addr = combined[
        (combined["sitenum"] > 0) &
        (combined["siteroad"].notna()) &
        (combined["siteroad"] != "")
    ].copy()
    print(f"Parcels with addresses: {len(has_addr):,}")

    # Check for unmapped siteroad values
    unmapped = set()
    for _, row in has_addr.iterrows():
        road = str(row["siteroad"]).strip()
        if road and road not in SITEROAD_MAP:
            unmapped.add(road)
    if unmapped:
        print(f"\nWARNING: {len(unmapped)} unmapped siteroad values (using fallback):")
        for road in sorted(unmapped):
            count = len(has_addr[has_addr["siteroad"].str.strip() == road])
            print(f"  {road:30s} ({count} parcels)")

    # Load existing wiki addresses
    with open(SEED_DIR / "addresses.json") as f:
        existing = json.load(f)
    existing_titles = set(a["wiki_title"] for a in existing["addresses"])
    print(f"\nExisting wiki pages: {len(existing_titles):,}")

    # Build parcel addresses and compare
    parcel_records = {}
    for _, row in has_addr.iterrows():
        try:
            title = normalize_parcel_address(row)
        except (ValueError, TypeError):
            continue

        apn = str(row["parcelid"]).strip()
        yr = int(row["yrbuilt"]) if row["yrbuilt"] and row["yrbuilt"] > 0 else 0
        stories = float(row["stories"]) if row["stories"] and row["stories"] > 0 else 0
        use = str(row["use_desc"]).strip() if row["use_desc"] else ""
        total_area = float(row["total_area"]) if row["total_area"] and row["total_area"] > 0 else 0

        if title not in parcel_records:
            parcel_records[title] = {
                "wiki_title": title,
                "apn": apn,
                "year_built": yr,
                "stories": stories,
                "use_desc": use,
                "total_area": total_area,
                "latitude": round(float(row["lat"]), 6),
                "longitude": round(float(row["lon"]), 6),
            }

    print(f"Unique parcel addresses: {len(parcel_records):,}")

    # Find what's missing from wiki
    missing = []
    for title, data in parcel_records.items():
        if title not in existing_titles:
            missing.append(data)

    # Find existing wiki pages that match parcels (for enrichment)
    enrichable = []
    for title in existing_titles:
        if title in parcel_records:
            rec = parcel_records[title]
            if rec["year_built"] > 0:
                enrichable.append(rec)

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Parcel addresses matched to wiki: {len(parcel_records) - len(missing):,}")
    print(f"  MISSING FROM WIKI: {len(missing):,}")
    print(f"  Existing pages enrichable with year_built: {len(enrichable):,}")
    print(f"{'='*60}")

    # Show missing by street
    missing_streets = Counter()
    for rec in missing:
        parts = rec["wiki_title"].split(" ", 1)
        if len(parts) > 1:
            missing_streets[parts[1]] += 1

    print("\nMissing by street (top 40):")
    for street, count in missing_streets.most_common(40):
        print(f"  {street}: {count}")

    # Check specific addresses the user asked about
    print("\n=== Checking specific addresses ===")
    for addr in ["445 West J Street", "441 West J Street", "453 West J Street",
                  "500 West J Street", "600 First Street", "700 First Street",
                  "100 West J Street", "200 West J Street", "300 West J Street"]:
        if addr in parcel_records:
            d = parcel_records[addr]
            status = "IN WIKI" if addr in existing_titles else "MISSING"
            print(f"  [{status}] {addr} — APN={d['apn']}, yr={d['year_built']}, use={d['use_desc']}")
        else:
            print(f"  [NOT IN PARCELS] {addr}")

    # Save results
    output = {
        "metadata": {
            "source": "Solano County Parcels (Assessor) Shapefile",
            "total_historic_parcels": len(combined),
            "parcels_with_addresses": len(has_addr),
            "unique_parcel_addresses": len(parcel_records),
            "matched_to_wiki": len(parcel_records) - len(missing),
            "missing_from_wiki": len(missing),
            "enrichable_with_year_built": len(enrichable),
        },
        "missing_addresses": sorted(missing, key=lambda x: x["wiki_title"]),
        "enrichable_addresses": sorted(enrichable, key=lambda x: x["wiki_title"]),
        "all_parcel_data": parcel_records,
    }

    output_path = SEED_DIR / "parcel_audit.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nSaved audit to: {output_path}")


if __name__ == "__main__":
    main()
