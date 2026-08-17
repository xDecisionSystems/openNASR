# `ILS_BASE`

Core instrument landing system identity, runway association, status, category, and localizer information.

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
| `STATE_NAME` | Associated State Name | Text, up to 30 characters | Not applicable | Yes | `ALABAMA` |
| `REGION_CODE` | FAA Region responsible for NAVAID (code) | Text, up to 3 characters | Not applicable | No | `ASO` |
| `RWY_LEN` | ILS Runway Length in Whole Feet | Numeric (5,0) (precision, scale) | feet | No | `7002` |
| `RWY_WIDTH` | ILS Runway Width in Whole Feet | Numeric (4,0) (precision, scale) | Not applicable | No | `150` |
| `CATEGORY` | Category of the ILS | Text, up to 4 characters | Not specified by FAA | Yes | `I` |
| `OWNER` | A Concatenation of the ILS OWNER CODE - ILS OWNER NAME | Text, up to 40 characters | Not specified by FAA | No | `F-FEDERAL AVIATION ADMIN.` |
| `OPERATOR` | A Concatenation of the ILS OPERATOR CODE - ILS OPERATOR NAME | Text, up to 40 characters | Not specified by FAA | No | `F-FEDERAL AVIATION ADMIN.` |
| `APCH_BEAR` | ILS Approach Bearing in Degrees Magnetic | Numeric (5,2) (precision, scale) | degrees | No | `52.45` |
| `MAG_VAR` | Magnetic Variation Degrees | Numeric (3,0) (precision, scale) | degrees | No | `4` |
| `MAG_VAR_HEMIS` | Magnetic Variation Direction | Text, up to 1 character | Not applicable | No | `W` |
| `COMPONENT_STATUS` | Operational Status of Localizer | Text, up to 30 characters | Not applicable | No | `OPERATIONAL RESTRICTED` |
| `COMPONENT_STATUS_DATE` | Effective Date of Localizer Operational Status | Text, up to 10 characters | Not applicable | No | `2017/07/18` |
| `LAT_DEG` | Localizer Antenna Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `33` |
| `LAT_MIN` | Localizer Antenna Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `35` |
| `LAT_SEC` | Localizer Antenna Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `47.2749` |
| `LAT_HEMIS` | Localizer Antenna Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Localizer Antenna Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `33.59646525` |
| `LONG_DEG` | Localizer Antenna Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `85` |
| `LONG_MIN` | Localizer Antenna Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `50` |
| `LONG_SEC` | Localizer Antenna Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `48.9232` |
| `LONG_HEMIS` | Localizer Antenna Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Localizer Antenna Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-85.84692311` |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information | Text, up to 2 characters | Not applicable | Yes | `T` |
| `SITE_ELEVATION` | Site Elevation of Localizer Antenna in Tenth of a Foot (MSL). | Numeric (6,1) (precision, scale) | feet | Yes | `606.3` |
| `LOC_FREQ` | Localizer Frequency (MHZ) | Numeric (6,2) (precision, scale) | MHz | No | `111.5` |
| `BK_COURSE_STATUS_CODE` | Localizer Back Course Status | Text, up to 1 character | Not applicable | Yes | `Y` |

## Sources

- `ILS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ILS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ILS_BASE.csv` from the 2026-08-06 cycle for example values
