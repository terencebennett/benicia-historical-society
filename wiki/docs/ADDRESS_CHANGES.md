# Address Changes in Benicia

## The Problem

Benicia's street numbering has changed over time. The same physical building may appear at different addresses across different historical records. This is one of the hardest problems in the project.

## Types of Changes

1. **Street renumbering** - Early house numbers were sequential; later standardized with wider spacing
2. **Directional prefix addition** - "G Street" became "West G Street" / "East G Street" (First Street is the dividing line)
3. **Street renaming** - Some streets have been renamed entirely

## Strategy

- Track address changes as first-class data in each property's "Historical Addresses" section
- Use Sanborn maps as the primary tool for establishing crosswalks (they show building footprints at specific addresses for specific years)
- Do NOT automate address reconciliation - this requires human judgment
- Always cite the source for each historical address

## How to Document

On each property wiki page, use the Historical Addresses table:

```
{| class="wikitable"
! Period !! Address !! Source
|-
| Current || 123 West G Street || Solano County GIS
|-
| 1913 || 45 G Street || 1913 Sanborn Map, Sheet 5
|-
| 1899 || 45 G Street || 1899 Sanborn Map, Sheet 5
|}
```

## Best Practices

- Focus on building footprints, not address numbers, when comparing maps
- If uncertain, add the page to `Category:Needs Address Verification`
- Never delete someone else's address identification; add your alternative and explain
- Record "not mapped" if the area wasn't covered by a particular Sanborn edition

## Pre-1880 Census

Census records before 1880 don't have street addresses. Households are listed in enumeration order. Reconstructing locations from context is speculative and should be clearly flagged.
