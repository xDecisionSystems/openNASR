# `ARB_SEG`

Ordered high- and low-altitude ARTCC boundary vertices.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `REC_ID` | Concatenation of the LOCATION_ID * BNDRY_CODE * 5 Character Point Designator. | Text, up to 14 characters | Not applicable | No | `ZAB*H*53855` |
| `LOCATION_ID` | Location Identifier. 3-4 character alphanumeric identifier. | Text, up to 4 characters | Not applicable | No | `ZAB` |
| `LOCATION_NAME` | Center Name. | Text, up to 30 characters | Not applicable | Yes | `ALBUQUERQUE` |
| `ALTITUDE` | Boundary Altitude Structure – HIGH, LOW or UNLIMITED. | Text, up to 10 characters | Not specified by FAA | No | `HIGH` |
| `TYPE` | Boundary Type (ARTCC, FIR, CTA, CTA/FIR, UTA). | Text, up to 10 characters | Not applicable | No | `ARTCC` |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Boundary. | Numeric (4,0) (precision, scale) | Not applicable | No | `10` |
| `LAT_DEG` | Boundary Point Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `35` |
| `LAT_MIN` | Boundary Point Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `46` |
| `LAT_SEC` | Boundary Point Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `0` |
| `LAT_HEMIS` | Boundary Point Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Boundary Point Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `35.76666666` |
| `LONG_DEG` | Boundary Point Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `111` |
| `LONG_MIN` | Boundary Point Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `50` |
| `LONG_SEC` | Boundary Point Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `30` |
| `LONG_HEMIS` | Boundary Point Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Boundary Point Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-111.84166666` |
| `BNDRY_PT_DESCRIP` | Description of Boundary Line Connecting Points on The Boundary. | Text, up to 300 characters | Not specified by FAA | Yes | `/COMMON ZAB-ZDV-ZLA/TO` |
| `NAS_DESCRIP_FLAG` | An 'X' In This Field Indicates This Point Is Used Only in The NAS Description and Not the Legal Description. | Text, up to 1 character | Not applicable | Yes | `X` |

## Sources

- `ARB_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ARB DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ARB_SEG.csv` from the 2026-08-06 cycle for example values
