# Data Sources

Complete documentation of every data source used in the Benicia Historic Homes Wiki.

## Tier 1: Authoritative Government Records

### 1a. Solano County GIS Data

**Address Points Shapefile:**
- URL: `https://solanocountysftpsa.blob.core.windows.net/solano-county-ca-gis-public-sftp/root/Address_Pts_GIS/Address_Pts_Shapefiles.zip`
- Source: Solano County ReGIS (https://regis.solanocounty.com/apps/)
- Schema: CalOES address point standard
- Created: April 5, 2023; updated monthly
- Key fields: FullAddress, APN, Add_Number, St_Name, St_PosTyp, coordinates
- Reliability: Very high for current addresses

**Parcels Shapefile:**
- URL: `https://solanocountysftpsa.blob.core.windows.net/solano-county-ca-gis-public-sftp/root/Parcels_Public_Aumentum_GIS/Parcels_Public_Aumentum_Shapefiles.zip`
- Uses Aumentum CAMA system
- Key fields: PARCELID (APN), polygon geometry, tax map references

### 1b. City of Benicia Historic Resources Inventory (2009)

- Surveyor: Carol Roland, Ph.D.
- Format: Individual DPR 523 survey forms (PDF)
- URL pattern: `ci.benicia.ca.us/vertical/sites/{GUID}/uploads/{address}Survey.PDF`
- Content: Designation status, architectural descriptions, build dates, historical significance
- WARNING: City website blocks robots.txt; manual download required

### 1c. Downtown Historic District Design Guidelines (2018)

- Source: City of Benicia
- Pages 156+: Appendix listing historic property addresses in the district
- Also blocked by robots.txt

### 1d. Benicia Historic Context Statement (February 2011)

- Prepared by professional consultants for the City
- Thematic history by era
- Downtown Historic Overlay District analysis (page 178+)
- References Sanborn Maps from 1886, 1891, 1899, 1913, 1942

## Tier 2: Federal Records

### 2a. Sanborn Fire Insurance Maps

- Source: Library of Congress, Geography and Map Division
- Available years: 1886, 1891, 1899, 1913, 1942
- Access: https://www.loc.gov/collections/sanborn-maps/ (search "Benicia")
- Pre-1926 maps are public domain
- Content: Building footprints, materials, stories, use, addresses, block numbers
- NOTE: Historical addresses may differ from modern ones

**Known LOC item IDs:**
| Year | Item ID | Sheets | LOC URL |
|------|---------|--------|---------|
| 1886 | sanborn00417_001 | 3 | https://www.loc.gov/item/sanborn00417_001/ |
| 1891 | sanborn00417_002 | 5 | https://www.loc.gov/item/sanborn00417_002/ |
| 1899 | sanborn00417_003 | 17 | https://www.loc.gov/item/sanborn00417_003/ |
| 1913 | sanborn00417_004 | 17 | https://www.loc.gov/item/sanborn00417_004/ |
| 1942 | sanborn00417_005 | 17 | https://www.loc.gov/item/sanborn00417_005/ |

### 2b. US Census Records

- Access: FamilySearch.org (free), Ancestry.com (subscription)
- Available: 1850, 1860, 1870, 1880, 1900, 1910, 1920, 1930, 1940, 1950
- Missing: 1890 (destroyed by fire)
- Addresses included from 1880 onward (inconsistent in 1880)
- Transcribed data NOT available for bulk download

### 2c. California State Census (1852)

- Source: FamilySearch, California State Library
- Predates the 1860 federal census
- Captures Benicia near its time as state capital

### 2d. HABS Survey (1976)

- Source: Library of Congress, Prints and Photographs Division
- Robert Bruegmann's survey produced "Benicia: Portrait of an Early California Town"
- Includes measured drawings, photographs, written documentation

## Tier 3: Secondary Sources

| Source | Author | Year | Content |
|--------|--------|------|---------|
| "Great Expectations" | Richard Dillon | — | Comprehensive city history |
| "Benicia: Portrait of an Early California Town" | Robert Bruegmann | 1980 | HABS-based architectural survey |
| "Downtown Historic Conservation Plan" | Woodbridge & Cannon | 1990 | Building-by-building descriptions |
| 1986 Benicia Historic Inventory | — | 1986 | Earlier survey, pre-2009 |

## Tier 4: Future Sources

These sources are designed for but not yet integrated:

- **Benicia Herald** - Currently being digitized
- **City Directories** - Check Benicia Public Library
- **Solano County Recorder** - Deed records, vital records
- **Benicia Historical Museum** - Photos, documents, oral histories (not digitized)

## Solano County Assessor (Optional)

- Portal: https://ca-solano.publicaccessnow.com/Assessor/PropertySearch.aspx
- Searchable by APN
- May provide: owner name, assessed value, year built, use code, square footage
- WARNING: Year built from assessor may reflect renovation dates, not original construction
- No documented API; use cautiously with rate limiting
