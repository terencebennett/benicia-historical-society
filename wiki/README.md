# Benicia Historic Homes Wiki

A MediaWiki instance documenting every historic property in downtown Benicia, California. Built as a community research platform where homeowners can find their address and discover its full history.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.9+ (for data processing scripts)
- GDAL library (for GIS processing): `brew install gdal` on macOS

### 1. Configure Environment

```bash
cp .env .env.backup  # Optional: backup defaults
# Edit .env to set secure passwords
```

### 2. Start the Wiki

```bash
bash scripts/setup_wiki.sh
```

This will:
- Start MediaWiki and MariaDB containers
- Install Semantic MediaWiki, Page Forms, and Maps extensions
- Configure the wiki for the project

The wiki will be available at **http://localhost:8080**.

### 3. Download GIS Data and Build Address List

```bash
pip install geopandas fiona shapely pyproj requests
python3 scripts/download_gis_data.py
```

Downloads Solano County Address Points and Parcels shapefiles, filters to historic downtown Benicia (south of Military Street + Arsenal), and generates `data/seed/addresses.json`.

### 4. Import Templates and Content

```bash
python3 scripts/import_templates.py
```

Imports all wiki templates, forms, categories, era pages, and documentation pages.

### 5. Create Property Stub Pages

```bash
python3 scripts/create_stubs.py
```

Creates a wiki page for every address in `addresses.json`. Each page is a stub with basic GIS data awaiting research.

### 6. Create Sanborn Map Index

```bash
python3 scripts/index_sanborn.py
```

Fetches Library of Congress metadata for Benicia's Sanborn maps (1886-1942) and creates index and sheet pages.

## Project Structure

```
benicia-historic-wiki/
├── docker-compose.yml          # MediaWiki + MariaDB containers
├── LocalSettings.php           # MediaWiki configuration
├── .env                        # Database passwords, admin credentials
├── data/
│   ├── seed/
│   │   ├── addresses.json      # Master address list (generated from GIS)
│   │   ├── eras.json           # Historical era definitions
│   │   └── sanborn_index.json  # Sanborn map metadata from LOC
│   ├── templates/              # MediaWiki template source files
│   │   ├── Property.wiki
│   │   ├── Person.wiki
│   │   ├── Era.wiki
│   │   ├── Source.wiki
│   │   ├── SanbornSheet.wiki
│   │   └── CensusRecord.wiki
│   ├── forms/                  # Page Forms definitions
│   │   ├── PropertyForm.wiki
│   │   ├── PersonForm.wiki
│   │   └── CensusEntryForm.wiki
│   ├── pages/                  # Documentation and content pages
│   │   ├── Main_Page.wiki
│   │   ├── Project_About.wiki
│   │   └── ...
│   ├── categories.json         # Category page definitions
│   └── downloads/              # Downloaded GIS shapefiles (gitignored)
├── scripts/
│   ├── setup_wiki.sh           # Initial wiki setup
│   ├── download_gis_data.py    # Download and process GIS data
│   ├── import_templates.py     # Import templates, forms, categories
│   ├── create_stubs.py         # Create property stub pages
│   ├── index_sanborn.py        # Create Sanborn map index
│   └── maintenance.py          # Backup, export, restore
├── backups/                    # Database backups (gitignored)
└── docs/
    ├── DATA_SOURCES.md         # Documentation of all data sources
    ├── ADDRESS_CHANGES.md      # Known address changes guide
    ├── CENSUS_GUIDE.md         # Census transcription guide
    └── CONTRIBUTING.md         # How to contribute
```

## Data Sources

Data is organized in tiers by reliability:

| Tier | Source | What It Provides |
|------|--------|-----------------|
| 1a | Solano County GIS | Current addresses, APNs, coordinates |
| 1b | City of Benicia Historic Survey (2009) | Designation status, architectural details |
| 1c | Design Guidelines (2018) | Historic property address list |
| 1d | Historic Context Statement (2011) | Thematic history, building discussions |
| 2a | Sanborn Maps (1886-1942) | Building footprints, materials, uses |
| 2b | US Census (1850-1950) | Residents, occupations, households |
| 2c | CA State Census (1852) | Early Benicia population |
| 2d | HABS Survey (1976) | Architectural documentation |

See `docs/DATA_SOURCES.md` for full details.

## Wiki Data Model

- **Property** - Core entity. One page per current street address with structured fields for APN, year built, style, status, coordinates, etc.
- **Person** - People connected to properties (owners, builders, residents)
- **Era** - Historical periods (1847-1853, 1853-1854, etc.)
- **SanbornSheet** - Individual Sanborn map sheets with LOC links
- **CensusRecord** - Structured census transcription entries
- **Source** - Standardized source citations

## Maintenance

### Backup

```bash
python3 scripts/maintenance.py backup        # Database backup
python3 scripts/maintenance.py export-xml     # Wiki pages as XML
python3 scripts/maintenance.py export-smw     # Structured data as JSON
```

### Restore

```bash
python3 scripts/maintenance.py restore backups/benicia_wiki_2024-01-15.sql.gz
```

### Statistics

```bash
python3 scripts/maintenance.py stats
```

### Stop/Start

```bash
docker compose stop     # Stop containers (data preserved)
docker compose up -d    # Restart containers
docker compose down     # Stop and remove containers (data in volumes preserved)
docker compose down -v  # Stop and remove everything including data
```

## Coverage Area

The wiki covers all properties in two areas:
- **Downtown Benicia** - South of Military East/Military West (~38.0555 latitude)
- **Benicia Arsenal** - East of downtown (bounded box in the GIS script)

This is intentionally broader than the official Downtown Historic District.

## Contributing

See `docs/CONTRIBUTING.md` for how to contribute research to the wiki.

## Human Work That Follows

After the automated setup, these manual tasks remain:
1. Review the generated address list (check the Military Street cutoff)
2. Contact Benicia Community Development for the historic buildings list
3. Download DPR 523 survey forms and enrich property pages
4. Begin census transcription (start with 1910)
5. Recruit volunteers from the Benicia Historical Society
