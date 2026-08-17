# `ARB_BASE`

Air Route Traffic Control Center identity and reference-location information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `LOCATION_ID` | Location Identifier. 3-4 character alphanumeric identifier. | Text, up to 4 characters | Not applicable | No | `FIMM` |
| `LOCATION_NAME` | Center Name. | Text, up to 30 characters | Not applicable | Yes | `MAURITIUS FIR` |
| `COMPUTER_ID` | Location Computer Identifier | Text, up to 3 characters | Not applicable | No | `PLS` |
| `ICAO_ID` | ICAO Identifier | Text, up to 7 characters | Not applicable | Yes | `FIMM` |
| `LOCATION_TYPE` | Location Type (ARTCC or CERAP). | Text, up to 5 characters | Not applicable | No | `ARTCC` |
| `CITY` | Location City Name | Text, up to 40 characters | Not applicable | No | `MAURITIUS` |
| `STATE` | Location State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `NM` |
| `COUNTRY_CODE` | Location Country Post Office Code | Text, up to 2 characters | Not applicable | No | `MU` |
| `LAT_DEG` | Location Reference Point Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `20` |
| `LAT_MIN` | Location Reference Point Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `26` |
| `LAT_SEC` | Location Reference Point Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `0` |
| `LAT_HEMIS` | Location Reference Point Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `S` |
| `LAT_DECIMAL` | Location Reference Point Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `-20.43333333` |
| `LONG_DEG` | Location Reference Point Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `57` |
| `LONG_MIN` | Location Reference Point Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `41` |
| `LONG_SEC` | Location Reference Point Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `0` |
| `LONG_HEMIS` | Location Reference Point Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `E` |
| `LONG_DECIMAL` | Location Reference Point Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `57.68333333` |
| `CROSS_REF` | Cross Reference Text (Free Form Text that further describes a specific Information Item.) | Text, up to 50 characters | Not specified by FAA | Yes | `FACILITY LOCATED AT ALBUQUERQUE, NM` |

## Sources

- `ARB_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ARB DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ARB_BASE.csv` from the 2026-08-06 cycle for example values
