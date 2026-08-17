# `MAA_BASE`

Miscellaneous Activity Area identity, activity type, location, schedule, and operating information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. | Text, up to 6 characters | Not applicable | No | `AAL001` |
| `MAA_TYPE_NAME` | Type of Miscellaneous Activity Area | Text, up to 20 characters | Not applicable | No | `AEROBATIC PRACTICE` |
| `NAV_ID` | NAVAID Facility Identifier with which MAA is Associated. | Text, up to 4 characters | Not applicable | Yes | `POM` |
| `NAV_TYPE` | NAVAID Facility Type with which the MAA is Associated. | Text, up to 25 characters | Not applicable | Yes | `VORTAC` |
| `NAV_RADIAL` | Azimuth (Degrees) From NAVAID (0-359.99) | Numeric (5,2) (precision, scale) | degrees | Yes | `72.61` |
| `NAV_DISTANCE` | Distance, In Nautical Miles, From NAVAID | Numeric (7,2) (precision, scale) | nautical miles | Yes | `33.76` |
| `STATE_CODE` | MAA State Abbreviation (Two-Letter Post Office) | Text, up to 2 characters | Not applicable | No | `AL` |
| `CITY` | MAA Associated City Name | Text, up to 30 characters | Not applicable | Yes | `MANCHESTER` |
| `LATITUDE` | MAA Latitude (Formatted) | Text, up to 14 characters | Not specified by FAA | Yes | `32-54-30.6000N` |
| `LONGITUDE` | MAA Longitude (Formatted) | Text, up to 15 characters | Not specified by FAA | Yes | `088-19-59.9900W` |
| `ARPT_IDS` | LIST of Landing Facility Identifiers with which MAA is Associated. | Text, up to 50 characters | Not applicable | Yes | `JFX` |
| `NEAREST_ARPT` | Nearest Airport ID Only Applies to Space Launch Activity Areas | Text, up to 4 characters | Not specified by FAA | Yes | `ADQ` |
| `NEAREST_ARPT_DIST` | Nearest Airport Distance in Nautical Miles Only Applies to Space Launch Activity Areas | Numeric (7,2) (precision, scale) | nautical miles | Yes | `20` |
| `NEAREST_ARPT_DIR` | Nearest Airport Direction Only Applies to Space Launch Activity Areas | Text, up to 2 characters | Not specified by FAA | Yes | `S` |
| `MAA_NAME` | MAA Area Name | Text, up to 120 characters | Not applicable | Yes | `HENLEY RANCH AIRPORT APA` |
| `MAX_ALT` | MAA Maximum Altitude Allowed | Text, up to 8 characters | Not specified by FAA | Yes | `5000AGL` |
| `MIN_ALT` | MAA Minimum Altitude Allowed | Text, up to 8 characters | Not specified by FAA | Yes | `0AGL` |
| `MAA_RADIUS` | MAA Area Radius, in Nautical Miles from Center Point | Numeric (4,2) (precision, scale) | nautical miles | Yes | `3` |
| `DESCRIPTION` | Additional Descriptive Text for MAA Area | Text, up to 450 characters | Not specified by FAA | Yes | `THE APA WOULD BE LOCATED AT WALKER COUNTY AIRPORT. IT WOULD HAVE AN IRREGULAR SH` |
| `MAA_USE` | MAA Use Description | Text, up to 8 characters | Not specified by FAA | Yes | `CIVIL` |
| `CHECK_NOTAMS` | Check for NOTAMs Only Applies to Space Launch Activity Areas | Text, up to 50 characters | Not specified by FAA | Yes | `PAZA ZAN` |
| `TIME_OF_USE` | Times of Use Description | Text, up to 300 characters | Not specified by FAA | Yes | `DAYLIGHT HOURS MONDAY THROUGH SUNDAY` |
| `USER_GROUP_NAME` | MAA User Group Name and Description | Text, up to 300 characters | Not applicable | Yes | `GRATIOT COMMUNITY AIRPORT APA` |

## Sources

- `MAA_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MAA DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MAA_BASE.csv` from the 2026-08-06 cycle for example values
