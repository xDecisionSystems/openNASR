# `PJA_BASE`

Parachute Jump Area identity, center, radius, schedule, and associated airport information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `PJA_ID` | PJA ID that uniquely identifies a Parachute Jump Area. | Text, up to 6 characters | Not applicable | No | `PAK001` |
| `NAV_ID` | NAVAID Facility Identifier with which PJA is Associated. | Text, up to 4 characters | Not applicable | Yes | `MCG` |
| `NAV_TYPE` | NAVAID Facility Type with which the PJA is Associated. | Text, up to 25 characters | Not applicable | Yes | `VORTAC` |
| `RADIAL` | Azimuth (Degrees) From NAVAID (0-359.99) | Numeric (5,2) (precision, scale) | degrees | Yes | `341` |
| `DISTANCE` | Distance, In Nautical Miles, From NAVAID | Numeric (7,2) (precision, scale) | nautical miles | Yes | `0` |
| `NAVAID_NAME` | Name of NAVAID with which PJA is Associated. | Text, up to 30 characters | Not applicable | Yes | `MC GRATH` |
| `STATE_CODE` | PJA State Abbreviation (Two-Letter Post Office) | Text, up to 2 characters | Not applicable | Yes | `AK` |
| `CITY` | PJA Associated City Name | Text, up to 30 characters | Not applicable | Yes | `MCGRATH` |
| `LATITUDE` | PJA Latitude (Formatted) | Text, up to 14 characters | Not specified by FAA | No | `62-57-03.7450N` |
| `LAT_DECIMAL` | PJA Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `62.95104027` |
| `LONGITUDE` | PJA Longitude (Formatted) | Text, up to 15 characters | Not specified by FAA | No | `155-36-41.0500W` |
| `LONG_DECIMAL` | PJA Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-155.61140277` |
| `ARPT_ID` | Landing Facility Identifier with which PJA is Associated. | Text, up to 4 characters | Not applicable | Yes | `16Z` |
| `SITE_NO` | Site Number of Associated Landing Facility | Text, up to 9 characters | Not specified by FAA | Yes | `50467.1` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | Yes | `C` |
| `DROP_ZONE_NAME` | PJA Drop Zone Name | Text, up to 50 characters | Not applicable | Yes | `HUSKY DROP ZONE` |
| `MAX_ALTITUDE` | PJA Maximum Altitude Allowed | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `5000` |
| `MAX_ALTITUDE_TYPE_CODE` | PJA Maximum Altitude Allowed Type (AGL, MSL, UNR) | Text, up to 3 characters | Not applicable | Yes | `MSL` |
| `PJA_RADIUS` | PJA Area Radius, in Nautical Miles from Center Point | Numeric (4,2) (precision, scale) | nautical miles | Yes | `3` |
| `CHART_REQUEST_FLAG` | Sectional Charting Required (Y/N) | Text, up to 1 character | Not applicable | Yes | `N` |
| `PUBLISH_CRITERIA` | PJA to be Published in Airport/Facility Directory (Y/N) | Text, up to 1 character | Not specified by FAA | Yes | `Y` |
| `DESCRIPTION` | Additional Descriptive Text for PJA Area | Text, up to 100 characters | Not specified by FAA | Yes | `20331 N US HWY 93 WHITE HILLS, AZ 86445` |
| `TIME_OF_USE` | Times of Use Description | Text, up to 150 characters | Not specified by FAA | Yes | `JUN- SEP;IRREGULAR HOURS` |
| `FSS_ID` | FSS Ident with which PJA is Associated | Text, up to 4 characters | Not applicable | Yes | `MCG` |
| `FSS_NAME` | FSS Name with which PJA is Associated | Text, up to 30 characters | Not applicable | Yes | `MCGRATH` |
| `PJA_USE` | PJA Use Description | Text, up to 8 characters | Not specified by FAA | Yes | `MILITARY` |
| `VOLUME` | PJA Area Volume | Text, up to 1 character | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `PJA_USER` | PJA User Group Name and Description | Text, up to 150 characters | Not specified by FAA | Yes | `ACTIVE ARMY AND USAF` |
| `REMARK` | Remark Text (Free Form Text that further describes a PJA.) | Text, up to 600 characters | Not applicable | Yes | `JUMPING OVER MCGRATH VORTAC` |

## Sources

- `PJA_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `PJA DATA LAYOUT.pdf` for FAA field definitions and stated units
- `PJA_BASE.csv` from the 2026-08-06 cycle for example values
