# `ILS_DME`

Distance Measuring Equipment associated with an instrument landing system.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00146.` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `AUO` |
| `CITY` | Associated City Name | Text, up to 40 characters | Not applicable | No | `AUBURN` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `RWY_END_ID` | ILS Runway End Identifier | Text, up to 3 characters | Not applicable | No | `36` |
| `ILS_LOC_ID` | ILS Identification | Text, up to 6 characters | Not applicable | No | `AUO` |
| `SYSTEM_TYPE_CODE` | ILS System Type. | Text, up to 2 characters | Not applicable | No | `LD` |
| `COMPONENT_STATUS` | Operational Status of DME | Text, up to 30 characters | Not applicable | No | `OPERATIONAL IFR` |
| `COMPONENT_STATUS_DATE` | Effective Date of DME Operational Status | Text, up to 10 characters | Not applicable | No | `2022/07/28` |
| `LAT_DEG` | DME Transponder Antenna Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `32` |
| `LAT_MIN` | DME Transponder Antenna Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `37` |
| `LAT_SEC` | DME Transponder Antenna Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `22.81` |
| `LAT_HEMIS` | DME Transponder Antenna Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | DME Transponder Antenna Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `32.62300277` |
| `LONG_DEG` | DME Transponder Antenna Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `85` |
| `LONG_MIN` | DME Transponder Antenna Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `26` |
| `LONG_SEC` | DME Transponder Antenna Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `8.88` |
| `LONG_HEMIS` | DME Transponder Antenna Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | DME Transponder Antenna Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-85.4358` |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information | Text, up to 2 characters | Not applicable | Yes | `F` |
| `SITE_ELEVATION` | Site Elevation of DME Transponder Antenna in Tenth of a Foot (MSL). | Numeric (6,1) (precision, scale) | feet | Yes | `779` |
| `CHANNEL` | NAS Channel on Which Distance Data is Transmitted | Text, up to 4 characters | Not specified by FAA | No | `38X` |

## Sources

- `ILS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ILS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ILS_DME.csv` from the 2026-08-06 cycle for example values
