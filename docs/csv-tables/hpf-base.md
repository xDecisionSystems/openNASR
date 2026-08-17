# `HPF_BASE`

Holding-pattern identity, fix, inbound course, turn direction, and leg geometry.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). | Text, up to 80 characters | Not applicable | No | `AABEE INT*GA*K7` |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern | Numeric (3,0) (precision, scale) | Not specified by FAA | No | `1` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `GA` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `FIX_ID` | Fix with which Holding is Associated. | Text, up to 30 characters | Not applicable | Yes | `AABEE` |
| `ICAO_REGION_CODE` | ICAO Region Code of the Fix with which the Holding is Associated. | Text, up to 2 characters | Not applicable | Yes | `K7` |
| `NAV_ID` | NAVAID with which Holding is Associated. | Text, up to 6 characters | Not applicable | Yes | `PDK` |
| `NAV_TYPE` | Facility Type of the NAVAID with which the Holding is Associated. | Text, up to 25 characters | Not applicable | Yes | `LD` |
| `HOLD_DIRECTION` | Direction of Holding on the NAVAID or Fix | Text, up to 3 characters | Not specified by FAA | Yes | `NE` |
| `HOLD_DEG_OR_CRS` | Magnetic Bearing, Radial (Degrees) or Course Direction of Holding | Text, up to 3 characters | degrees | Yes | `26` |
| `AZIMUTH` | Azimuth (Degrees Shown Above is a Radial, Course, Bearing, or RNAV Track) | Text, up to 4 characters | degrees | No | `CRS` |
| `COURSE_INBOUND_DEG` | Inbound Course. | Numeric (3,0) (precision, scale) | Not specified by FAA | Yes | `206` |
| `TURN_DIRECTION` | Turning Direction | Text, up to 3 characters | Not specified by FAA | No | `L` |
| `LEG_LENGTH_DIST` | Leg Length Outbound DME (NM) | Numeric (2,0) (precision, scale) | nautical miles | Yes | `15` |

## Sources

- `HPF_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `HPF DATA LAYOUT.pdf` for FAA field definitions and stated units
- `HPF_BASE.csv` from the 2026-08-06 cycle for example values
