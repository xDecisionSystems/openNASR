# `AWOS`

Automated weather observing station identity, location, equipment, and commissioning information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `ASOS_AWOS_ID` | Weather System Identifier. Unique 3-4 character alphanumeric identifier. | Text, up to 4 characters | Not applicable | No | `00U` |
| `ASOS_AWOS_TYPE` | Weather System Type. | Text, up to 10 characters | Not applicable | No | `AWOS-3` |
| `STATE_CODE` | Associated State Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `MT` |
| `CITY` | Weather System associated City Name. | Text, up to 40 characters | Not applicable | No | `HARDIN` |
| `COUNTRY_CODE` | Country Code Weather System is Located. | Text, up to 2 characters | Not applicable | No | `US` |
| `COMMISSIONED_DATE` | Decommissioned Weather systems are not included so Dates given are for Commissioning Dates. | Text, up to 10 characters | Not applicable | Yes | `2014/08/08` |
| `NAVAID_FLAG` | Weather associated with NAVAID – Y/N Flag. | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DEG` | Weather System Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | Yes | `45` |
| `LAT_MIN` | Weather System Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | Yes | `44` |
| `LAT_SEC` | Weather System Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | Yes | `43.15` |
| `LAT_HEMIS` | Weather System Latitude Hemisphere | Text, up to 1 character | Not applicable | Yes | `N` |
| `LAT_DECIMAL` | Weather System Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | Yes | `45.74531944` |
| `LONG_DEG` | Weather System Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | Yes | `107` |
| `LONG_MIN` | Weather System Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | Yes | `39` |
| `LONG_SEC` | Weather System Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | Yes | `35.13` |
| `LONG_HEMIS` | Weather System Longitude Hemisphere | Text, up to 1 character | Not applicable | Yes | `W` |
| `LONG_DECIMAL` | Weather System Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | Yes | `-107.65975833` |
| `ELEV` | Weather System Elevation (Nearest Tenth of a Foot) | Numeric (6,1) (precision, scale) | feet | Yes | `3085` |
| `SURVEY_METHOD_CODE` | Weather System Location Determination Method | Text, up to 1 character | Not applicable | Yes | `E` |
| `PHONE_NO` | Weather System Telephone Number | Text, up to 14 characters | Not specified by FAA | Yes | `406-665-4241` |
| `SECOND_PHONE_NO` | Weather System Second Telephone Number | Text, up to 14 characters | seconds | Yes | `757-433-3619` |
| `SITE_NO` | Landing Facility Site Number when Weather System Located at Airport. | Text, up to 9 characters | Not specified by FAA | Yes | `12385.2` |
| `SITE_TYPE_CODE` | Landing Facility Type Code when Weather System Located at Airport. | Text, up to 1 character | Not applicable | Yes | `A` |
| `REMARK` | Remark associated with Weather System. | Text, up to 1500 characters | Not applicable | Yes | `0A0 AWOS-3PT IS ASSOCIATED WITH SPACEPORT AMERICA ARPT, 9NM9.` |

## Sources

- `AWOS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `AWOS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `AWOS.csv` from the 2026-08-06 cycle for example values
