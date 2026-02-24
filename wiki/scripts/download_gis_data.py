#!/usr/bin/env python3
"""
download_gis_data.py - Download and process Solano County GIS data for Benicia.

Downloads the Address Points and Parcels shapefiles from Solano County,
filters to historic downtown Benicia (south of Military Street + Arsenal),
and outputs data/seed/addresses.json.

Requirements: geopandas, fiona, shapely, pyproj, requests
Install: pip install geopandas fiona shapely pyproj requests
Note: geopandas requires GDAL. On macOS: brew install gdal
"""

import json
import os
import sys
import zipfile
from datetime import date
from pathlib import Path

import requests

try:
    import geopandas as gpd
    from shapely.geometry import box
except ImportError:
    print("ERROR: Required packages not installed.")
    print("Run: pip install geopandas fiona shapely pyproj requests")
    print("On macOS, you may also need: brew install gdal")
    sys.exit(1)

# === CONFIGURATION ===
# These are the key parameters. Adjust if the coverage area needs tweaking.

# Military East/West runs roughly east-west at approximately this latitude.
# Everything south of this line is the old town.
MILITARY_LATITUDE = 38.0555

# Arsenal area bounding box (east of downtown)
ARSENAL_BBOX = {
    "west": -122.152,
    "east": -122.135,
    "south": 38.050,
    "north": 38.060,
}

# Southern boundary (waterfront)
SOUTH_LATITUDE = 38.043

# Western boundary (roughly where old town ends)
WEST_LONGITUDE = -122.165

# Eastern boundary for downtown (where Arsenal begins)
EAST_LONGITUDE_DOWNTOWN = -122.148

# Data source URLs
ADDRESS_POINTS_URL = (
    "https://solanocountysftpsa.blob.core.windows.net/"
    "solano-county-ca-gis-public-sftp/root/Address_Pts_GIS/"
    "Address_Pts_Shapefiles.zip"
)
PARCELS_URL = (
    "https://solanocountysftpsa.blob.core.windows.net/"
    "solano-county-ca-gis-public-sftp/root/Parcels_Public_Aumentum_GIS/"
    "Parcels_Public_Aumentum_Shapefiles.zip"
)

# Project paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
SEED_DIR = DATA_DIR / "seed"
DOWNLOAD_DIR = DATA_DIR / "downloads"


def download_file(url: str, dest: Path) -> Path:
    """Download a file with progress reporting."""
    if dest.exists():
        print(f"  Already downloaded: {dest.name}")
        return dest

    print(f"  Downloading {dest.name}...")
    print(f"  URL: {url}")

    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = (downloaded / total) * 100
                print(f"\r  {downloaded:,} / {total:,} bytes ({pct:.1f}%)", end="")
    print()

    return dest


def extract_shapefile(zip_path: Path, extract_dir: Path) -> Path:
    """Extract a shapefile ZIP and return the path to the .shp file."""
    if extract_dir.exists():
        # Look for existing .shp file
        shp_files = list(extract_dir.glob("**/*.shp"))
        if shp_files:
            print(f"  Already extracted: {shp_files[0].name}")
            return shp_files[0]

    print(f"  Extracting {zip_path.name}...")
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    shp_files = list(extract_dir.glob("**/*.shp"))
    if not shp_files:
        print("  ERROR: No .shp file found in the archive!")
        sys.exit(1)

    print(f"  Found shapefile: {shp_files[0].name}")
    return shp_files[0]


def explore_shapefile(shp_path: Path) -> gpd.GeoDataFrame:
    """Load a shapefile and print its schema for exploration."""
    print(f"\n  Loading {shp_path.name}...")
    gdf = gpd.read_file(shp_path)
    print(f"  Total records: {len(gdf):,}")
    print(f"  CRS: {gdf.crs}")
    print(f"  Columns: {list(gdf.columns)}")
    print(f"  Sample row:")
    if len(gdf) > 0:
        for col in gdf.columns:
            if col != "geometry":
                print(f"    {col}: {gdf.iloc[0][col]}")
    return gdf


def find_city_column(gdf: gpd.GeoDataFrame) -> str:
    """Find the column that contains city names."""
    # CalOES schema candidates (check both cases)
    candidates = [
        "inc_muni", "Inc_Muni", "INC_MUNI",
        "CITY", "City", "city",
        "MUNICIPALITY", "Municipality",
        "PLACE", "Place",
        "Inc_Name", "inc_name",
        "JURISDICTI", "Jurisdicti",
        "Post_Comm", "post_comm",
        "MSAGComm", "msagcomm",
    ]
    for col in candidates:
        if col in gdf.columns:
            return col

    # Try to find a column with "Benicia" in it
    for col in gdf.columns:
        if col == "geometry":
            continue
        try:
            vals = gdf[col].dropna().unique()
            str_vals = [str(v) for v in vals[:100]]
            if any("benicia" in v.lower() for v in str_vals):
                print(f"  Found city-like column: {col}")
                sample = [v for v in str_vals if "benicia" in v.lower()]
                print(f"    Benicia values: {sample[:5]}")
                return col
        except (TypeError, AttributeError):
            continue

    return ""


def find_address_columns(gdf: gpd.GeoDataFrame) -> dict:
    """Identify the columns for address components."""
    mapping = {}

    # Full address (street only, no city/state) - prefer fulladdr_1 which has long form
    for col in ["fulladdr_1", "fulladdr_l", "FullAddres", "Full_Addre", "FULLADDRES",
                "FullAddress", "SITUS_ADDR", "FULL_ADDR", "fulladdres"]:
        if col in gdf.columns:
            mapping["full_address"] = col
            break

    # House number
    for col in ["add_number", "Add_Number", "ADD_NUMBER", "HOUSE_NO", "HSE_NBR",
                "STNUMBER", "AddNum"]:
        if col in gdf.columns:
            mapping["house_number"] = col
            break

    # Street prefix direction (N, S, E, W)
    for col in ["st_predir", "St_PreDir", "ST_PREDIR", "PREDIR", "StPreDir"]:
        if col in gdf.columns:
            mapping["street_prefix"] = col
            break

    # Street name
    for col in ["st_name", "St_Name", "ST_NAME", "STREET", "StName"]:
        if col in gdf.columns:
            mapping["street_name"] = col
            break

    # Street type (St, Ave, etc.)
    for col in ["st_postyp", "St_PosTyp", "ST_POSTYP", "SUFFIX", "StPosTyp", "St_Type"]:
        if col in gdf.columns:
            mapping["street_type"] = col
            break

    # APN
    for col in ["apn", "APN", "PARCELID", "ParcelID", "PARCEL_ID", "Parcel_ID"]:
        if col in gdf.columns:
            mapping["apn"] = col
            break

    return mapping


def filter_benicia_historic(gdf: gpd.GeoDataFrame, city_col: str) -> gpd.GeoDataFrame:
    """Filter to historic Benicia: south of Military + Arsenal area."""
    # Ensure we're in WGS84 (lat/lon)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        print(f"  Reprojecting from {gdf.crs} to WGS84...")
        gdf = gdf.to_crs(epsg=4326)

    # Filter to Benicia
    if city_col:
        benicia_mask = gdf[city_col].str.contains("Benicia", case=False, na=False)
        benicia = gdf[benicia_mask].copy()
        print(f"  Benicia addresses (all): {len(benicia):,}")
    else:
        # No city column found - use a broader bounding box for Benicia
        print("  WARNING: No city column found. Using bounding box filter for Benicia area.")
        benicia_bbox = box(-122.17, 38.04, -122.13, 38.07)
        benicia = gdf[gdf.geometry.within(benicia_bbox)].copy()
        print(f"  Addresses in Benicia bounding box: {len(benicia):,}")

    if len(benicia) == 0:
        print("  ERROR: No Benicia addresses found!")
        print("  Unique city values (sample):")
        if city_col:
            print(f"    {gdf[city_col].dropna().unique()[:20]}")
        return benicia

    # Extract lat/lon from geometry
    benicia["lat"] = benicia.geometry.y
    benicia["lon"] = benicia.geometry.x

    # Filter: south of Military Street (downtown)
    downtown_mask = benicia["lat"] < MILITARY_LATITUDE
    downtown = benicia[downtown_mask]
    print(f"  South of Military ({MILITARY_LATITUDE}): {len(downtown):,}")

    # Filter: Arsenal area
    arsenal_box = box(
        ARSENAL_BBOX["west"],
        ARSENAL_BBOX["south"],
        ARSENAL_BBOX["east"],
        ARSENAL_BBOX["north"],
    )
    arsenal_mask = benicia.geometry.within(arsenal_box)
    arsenal = benicia[arsenal_mask]
    print(f"  Arsenal area: {len(arsenal):,}")

    # Combine (union of the two filters)
    combined_mask = downtown_mask | arsenal_mask
    result = benicia[combined_mask].copy()
    print(f"  Combined (downtown + arsenal): {len(result):,}")

    return result


def classify_area(row) -> str:
    """Classify whether an address is in 'downtown' or 'arsenal'."""
    lat, lon = row["lat"], row["lon"]
    if (
        ARSENAL_BBOX["west"] <= lon <= ARSENAL_BBOX["east"]
        and ARSENAL_BBOX["south"] <= lat <= ARSENAL_BBOX["north"]
    ):
        return "arsenal"
    return "downtown"


def normalize_address(full_addr: str) -> str:
    """Normalize an address string to a canonical form for wiki page titles.

    Converts uppercase GIS data like '123 W G STREET' to '123 West G Street'.
    """
    if not full_addr:
        return ""

    addr = str(full_addr).strip()

    # Convert to title case first (handles ALL CAPS from GIS data)
    # But preserve single-letter street names as uppercase
    parts = addr.split()
    normalized_parts = []
    for i, part in enumerate(parts):
        # House number stays as-is
        if i == 0 and part.isdigit():
            normalized_parts.append(part)
        # Single letter street names stay uppercase (B, C, D, etc.)
        elif len(part) == 1 and part.isalpha():
            normalized_parts.append(part.upper())
        # Directional abbreviations get expanded
        elif part.upper() in ("W", "E", "N", "S") and i > 0:
            dir_map = {"W": "West", "E": "East", "N": "North", "S": "South"}
            normalized_parts.append(dir_map[part.upper()])
        # Ordinal numbers: 1ST, 2ND, 3RD, etc.
        elif part.upper().endswith(("ST", "ND", "RD", "TH")) and any(c.isdigit() for c in part):
            normalized_parts.append(part.lower())
        else:
            normalized_parts.append(part.capitalize())

    addr = " ".join(normalized_parts)

    # Expand directional at position after house number
    # e.g., "123 W G Street" -> "123 West G Street"
    for abbr, full in [("W ", "West "), ("E ", "East "), ("N ", "North "), ("S ", "South ")]:
        # Only replace if it follows a number (house number)
        import re
        addr = re.sub(r"(\d+) " + abbr[0] + r" ", r"\1 " + full, addr)

    return addr


def build_address_record(row, addr_cols: dict) -> dict:
    """Build an address record dict from a GeoDataFrame row."""
    import numpy as np

    def get_field(col_key):
        """Safely get a field value, handling None/NaN/numpy types."""
        col_name = addr_cols.get(col_key, "")
        if not col_name:
            return ""
        val = row.get(col_name)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return ""
        # Handle numpy int/float
        if hasattr(val, "item"):
            val = val.item()
        return str(val).strip()

    full_address = get_field("full_address")
    house_number = get_field("house_number")
    street_prefix = get_field("street_prefix")
    street_name = get_field("street_name")
    street_type = get_field("street_type")
    apn = get_field("apn")

    # Skip records without a house number (these are street centerlines, not addresses)
    if not house_number or house_number == "0":
        return None

    # Build full address from components if the full_address field is empty
    if not full_address:
        parts = [house_number, street_prefix, street_name, street_type]
        full_address = " ".join(p for p in parts if p)

    wiki_title = normalize_address(full_address)

    return {
        "full_address": full_address,
        "wiki_title": wiki_title,
        "house_number": house_number,
        "street_prefix": street_prefix,
        "street_name": street_name,
        "street_type": street_type,
        "apn": apn,
        "latitude": round(float(row["lat"]), 6),
        "longitude": round(float(row["lon"]), 6),
        "area": classify_area(row),
        "data_source": "Solano County GIS",
    }


def load_parcels_apn_map(parcels_shp: Path) -> dict:
    """Load parcels shapefile and create a lookup by APN for supplemental data."""
    print("\n[3/5] Loading Parcels shapefile for supplemental APN data...")
    try:
        parcels = gpd.read_file(parcels_shp)
        print(f"  Total parcels: {len(parcels):,}")
        print(f"  Columns: {list(parcels.columns)}")
        # The parcels data mainly gives us geometry (polygon) and APN
        # We'll use it later if needed but for now just note what's available
        return {"loaded": True, "count": len(parcels)}
    except Exception as e:
        print(f"  WARNING: Could not load parcels: {e}")
        return {"loaded": False}


def main():
    print("=" * 60)
    print("Solano County GIS Data Downloader for Benicia Historic Wiki")
    print("=" * 60)

    # Create directories
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SEED_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Download shapefiles
    print("\n[1/5] Downloading GIS data...")

    addr_zip = DOWNLOAD_DIR / "Address_Pts_Shapefiles.zip"
    parcels_zip = DOWNLOAD_DIR / "Parcels_Public_Aumentum_Shapefiles.zip"

    download_file(ADDRESS_POINTS_URL, addr_zip)
    download_file(PARCELS_URL, parcels_zip)

    # Step 2: Extract shapefiles
    print("\n[2/5] Extracting shapefiles...")

    addr_dir = DOWNLOAD_DIR / "address_points"
    parcels_dir = DOWNLOAD_DIR / "parcels"

    addr_shp = extract_shapefile(addr_zip, addr_dir)
    parcels_shp = extract_shapefile(parcels_zip, parcels_dir)

    # Step 3: Explore and load address points
    print("\n[3/5] Loading and exploring Address Points...")
    addr_gdf = explore_shapefile(addr_shp)

    # Find the relevant columns
    city_col = find_city_column(addr_gdf)
    if city_col:
        print(f"  City column: {city_col}")
    else:
        print("  WARNING: Could not identify city column!")

    addr_cols = find_address_columns(addr_gdf)
    print(f"  Address column mapping: {addr_cols}")

    # Also check parcels for supplemental data
    load_parcels_apn_map(parcels_shp)

    # Step 4: Filter to historic Benicia
    print("\n[4/5] Filtering to historic Benicia...")
    filtered = filter_benicia_historic(addr_gdf, city_col)

    if len(filtered) == 0:
        print("\nERROR: No addresses found after filtering!")
        print("Check the MILITARY_LATITUDE and city column settings.")
        sys.exit(1)

    # Build address records
    addresses = []
    seen_titles = set()

    for _, row in filtered.iterrows():
        record = build_address_record(row, addr_cols)
        if record is None or not record["full_address"]:
            continue

        # Deduplicate by wiki title
        title = record["wiki_title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)

        addresses.append(record)

    # Sort by street name then house number
    addresses.sort(key=lambda a: (a["street_name"], a.get("house_number", "").zfill(5)))

    # Print summary
    print(f"\n  Total unique addresses: {len(addresses)}")
    downtown_count = sum(1 for a in addresses if a["area"] == "downtown")
    arsenal_count = sum(1 for a in addresses if a["area"] == "arsenal")
    print(f"  Downtown: {downtown_count}")
    print(f"  Arsenal: {arsenal_count}")

    # Print unique streets
    streets = sorted(set(
        f"{a['street_prefix']} {a['street_name']} {a['street_type']}".strip()
        for a in addresses
    ))
    print(f"\n  Unique streets ({len(streets)}):")
    for s in streets:
        count = sum(1 for a in addresses if
                    f"{a['street_prefix']} {a['street_name']} {a['street_type']}".strip() == s)
        print(f"    {s}: {count} addresses")

    # Step 5: Write output
    print("\n[5/5] Writing addresses.json...")
    output = {
        "metadata": {
            "source": "Solano County Address Points Shapefile",
            "download_date": date.today().isoformat(),
            "filter_method": (
                f"All Benicia addresses south of Military East/West "
                f"(~{MILITARY_LATITUDE} lat) plus Arsenal area"
            ),
            "total_addresses": len(addresses),
            "downtown_count": downtown_count,
            "arsenal_count": arsenal_count,
            "unique_streets": len(streets),
            "military_latitude_cutoff": MILITARY_LATITUDE,
            "arsenal_bbox": ARSENAL_BBOX,
            "notes": (
                "Approximate boundary. Review edge cases manually. "
                "Address normalization applied for wiki page titles."
            ),
        },
        "addresses": addresses,
    }

    output_path = SEED_DIR / "addresses.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Written to: {output_path}")
    print(f"  File size: {output_path.stat().st_size:,} bytes")

    print("\n" + "=" * 60)
    print("DONE. Review the output and adjust MILITARY_LATITUDE if needed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
