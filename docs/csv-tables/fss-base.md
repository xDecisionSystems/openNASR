# `FSS_BASE`

Flight Service Station identity, location, communications, and service information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FSS_ID` | Flight Service Station Identifier | Text, up to 4 characters | Not applicable | No | `ABQ` |
| `NAME` | Flight Service Station Name | Text, up to 30 characters | Not applicable | No | `ALBUQUERQUE` |
| `UPDATE_DATE` | Last Date on which the Record was updated. | Text, up to 10 characters | Not applicable | Yes | `2024/11/27` |
| `FSS_FAC_TYPE` | Facility Type: Flight Service Station (FSS), FS21 HUB Station (HUB) or FS21 Radio Service Area (RADIO). | Text, up to 8 characters | Not applicable | No | `RADIO` |
| `VOICE_CALL` | FSS Voice Call | Text, up to 30 characters | Not specified by FAA | Yes | `ALBUQUERQUE` |
| `CITY` | Associated City Name | Text, up to 40 characters | Not applicable | No | `ALBUQUERQUE` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `NM` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `LAT_DEG` | Flight Service Station Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `35` |
| `LAT_MIN` | Flight Service Station Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `2` |
| `LAT_SEC` | Flight Service Station Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `20.1536` |
| `LAT_HEMIS` | Flight Service Station Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Flight Service Station Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `35.03893155` |
| `LONG_DEG` | Flight Service Station Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `106` |
| `LONG_MIN` | Flight Service Station Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `36` |
| `LONG_SEC` | Flight Service Station Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `29.7438` |
| `LONG_HEMIS` | Flight Service Station Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Flight Service Station Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-106.60826216` |
| `OPR_HOURS` | FSS Hours of Operation | Text, up to 65 characters | hours | No | `24` |
| `FAC_STATUS` | Status of Facility | Text, up to 1 character | Not applicable | Yes | `A` |
| `ALTERNATE_FSS` | If the Record Facility does not have Circuit B Teletype Capable of Transmitting/Receiving Flight Plan Messages then Alternate FSS with this Capability listed. | Text, up to 4 characters | Not specified by FAA | Yes | `FAI` |
| `WEA_RADAR_FLAG` | Availability of Weather Radar | Text, up to 1 character | Not applicable | Yes | `N` |
| `PHONE_NO` | Telephone Number used to reach FSS. | Text, up to 16 characters | Not specified by FAA | Yes | `907-852-2511` |
| `TOLL_FREE_NO` | Toll Free Telephone Number used to reach FSS. | Text, up to 16 characters | Not specified by FAA | Yes | `1-800-WX-BRIEF` |

## Sources

- `FSS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `FSS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `FSS_BASE.csv` from the 2026-08-06 cycle for example values
