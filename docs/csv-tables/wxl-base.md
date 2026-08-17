# `WXL_BASE`

Weather-reporting location identity, position, and associated facility information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `WEA_ID` | Weather Reporting Location Identifier | Text, up to 4 characters | Not applicable | No | `00U` |
| `CITY` | Associated City Name | Text, up to 40 characters | Not applicable | No | `HARDIN` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `MT` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `LAT_DEG` | Weather Reporting Location Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `45` |
| `LAT_MIN` | Weather Reporting Location Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `44` |
| `LAT_SEC` | Weather Reporting Location Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `43.15` |
| `LAT_HEMIS` | Weather Reporting Location Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Weather Reporting Location Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `45.74531944` |
| `LONG_DEG` | Weather Reporting Location Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `107` |
| `LONG_MIN` | Weather Reporting Location Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `39` |
| `LONG_SEC` | Weather Reporting Location Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `35.13` |
| `LONG_HEMIS` | Weather Reporting Location Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Weather Reporting Location Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-107.65975833` |
| `ELEV` | Weather Reporting Location Elevation - Value (Whole Feet MSL). | Numeric (5,0) (precision, scale) | feet MSL | No | `3085` |
| `SURVEY_METHOD_CODE` | Weather Reporting Location Elevation - Accuracy | Text, up to 1 character | Not applicable | No | `E` |

## Sources

- `WXL_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `WXL DATA LAYOUT.pdf` for FAA field definitions and stated units
- `WXL_BASE.csv` from the 2026-08-06 cycle for example values
