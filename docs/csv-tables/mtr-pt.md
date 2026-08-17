# `MTR_PT`

Ordered navigation points and segment information for a military training route.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `ROUTE_TYPE_CODE` | MTR Type Code. | Text, up to 2 characters | Not applicable | No | `IR` |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. | Text, up to 5 characters | Not applicable | No | `002` |
| `ARTCC` | List of ARTCC Idents that MTR traverses. | Text, up to 80 characters | Not specified by FAA | Yes | `ZTL` |
| `ROUTE_PT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given MTR. | Numeric (3,0) (precision, scale) | Not applicable | No | `10` |
| `ROUTE_PT_ID` | Route Point Identifier. | Text, up to 4 characters | Not applicable | No | `A` |
| `NEXT_ROUTE_PT_ID` | The Next Sequential ROUTE_PT_ID. | Text, up to 4 characters | Not applicable | Yes | `B` |
| `SEGMENT_TEXT` | Concatenation of Segment Text preceded by the Segment Text Sequence Number. | Text, up to 228 characters | Not applicable | Yes | `(1) CROSS AT 60 MSL TO` |
| `LAT_DEG` | MTR Route Point Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `36` |
| `LAT_MIN` | MTR Route Point Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `4` |
| `LAT_SEC` | MTR Route Point Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `0` |
| `LAT_HEMIS` | MTR Route Point Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | MTR Route Point Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `36.06666666` |
| `LONG_DEG` | MTR Route Point Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `84` |
| `LONG_MIN` | MTR Route Point Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `39` |
| `LONG_SEC` | MTR Route Point Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `0` |
| `LONG_HEMIS` | MTR Route Point Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | MTR Route Point Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-84.65` |
| `NAV_ID` | Identifier of related NAVAID | Text, up to 4 characters | Not applicable | Yes | `VXV` |
| `NAVAID_BEARING` | Bearing of NAVAID from Point | Numeric (3,0) (precision, scale) | Not applicable | Yes | `288` |
| `NAVAID_DIST` | Distance of NAVAID from Point | Numeric (4,0) (precision, scale) | Not applicable | Yes | `38` |

## Sources

- `MTR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MTR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MTR_PT.csv` from the 2026-08-06 cycle for example values
