# `ILS_GS`

Glide-slope transmitter and location information for an instrument landing system.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00128.` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `ANB` |
| `CITY` | Associated City Name | Text, up to 40 characters | Not applicable | No | `ANNISTON` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `RWY_END_ID` | ILS Runway End Identifier | Text, up to 3 characters | Not applicable | No | `05` |
| `ILS_LOC_ID` | ILS Identification | Text, up to 6 characters | Not applicable | No | `ANB` |
| `SYSTEM_TYPE_CODE` | ILS System Type. | Text, up to 2 characters | Not applicable | No | `LS` |
| `COMPONENT_STATUS` | Operational Status of Glide Slope | Text, up to 30 characters | Not applicable | No | `OPERATIONAL IFR` |
| `COMPONENT_STATUS_DATE` | Effective Date of Glide Slope Operational Status | Text, up to 10 characters | Not applicable | No | `1991/07/25` |
| `LAT_DEG` | Glide Slope Transmitter Antenna Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `33` |
| `LAT_MIN` | Glide Slope Transmitter Antenna Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `35` |
| `LAT_SEC` | Glide Slope Transmitter Antenna Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `1.8307` |
| `LAT_HEMIS` | Glide Slope Transmitter Antenna Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Glide Slope Transmitter Antenna Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `33.58384186` |
| `LONG_DEG` | Glide Slope Transmitter Antenna Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `85` |
| `LONG_MIN` | Glide Slope Transmitter Antenna Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `51` |
| `LONG_SEC` | Glide Slope Transmitter Antenna Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `55.9432` |
| `LONG_HEMIS` | Glide Slope Transmitter Antenna Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Glide Slope Transmitter Antenna Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-85.86553977` |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information | Text, up to 2 characters | Not applicable | Yes | `T` |
| `SITE_ELEVATION` | Site Elevation of Glide Slope Transmitter Antenna in Tenth of a Foot (MSL). | Numeric (6,1) (precision, scale) | feet | Yes | `590.5` |
| `G_S_TYPE_CODE` | Glide Slope Class/Type | Text, up to 2 characters | Not applicable | No | `GS` |
| `G_S_ANGLE` | Glide Slope Angle in Degrees and Hundredths of Degree | Numeric (4,2) (precision, scale) | degrees | No | `3` |
| `G_S_FREQ` | Glide Slope Transmission Frequency | Numeric (6,2) (precision, scale) | Not specified by FAA | No | `332.9` |

## Sources

- `ILS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ILS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ILS_GS.csv` from the 2026-08-06 cycle for example values
