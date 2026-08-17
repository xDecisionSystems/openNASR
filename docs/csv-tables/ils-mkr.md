# `ILS_MKR`

Marker beacon or locator information associated with an instrument landing system.

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
| `ILS_COMP_TYPE_CODE` | Marker Type (IM - Inner Marker, MM - Middle Marker, OM - Outer Marker) | Text, up to 3 characters | Not applicable | No | `OM` |
| `COMPONENT_STATUS` | Operational Status of Marker Beacon | Text, up to 30 characters | Not applicable | No | `OPERATIONAL IFR` |
| `COMPONENT_STATUS_DATE` | Effective Date of Marker Beacon Operational Status | Text, up to 10 characters | Not applicable | No | `2011/08/30` |
| `LAT_DEG` | Marker Beacon Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `33` |
| `LAT_MIN` | Marker Beacon Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `32` |
| `LAT_SEC` | Marker Beacon Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `3.6507` |
| `LAT_HEMIS` | Marker Beacon Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Marker Beacon Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `33.53434741` |
| `LONG_DEG` | Marker Beacon Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `85` |
| `LONG_MIN` | Marker Beacon Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `55` |
| `LONG_SEC` | Marker Beacon Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `50.8473` |
| `LONG_HEMIS` | Marker Beacon Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Marker Beacon Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-85.93079091` |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information | Text, up to 2 characters | Not applicable | Yes | `T` |
| `SITE_ELEVATION` | Site Elevation of Marker Beacon in Tenth of a Foot (MSL). | Numeric (6,1) (precision, scale) | feet | Yes | `589.9` |
| `MKR_FAC_TYPE_CODE` | Facility/Type of Marker/Locator | Text, up to 2 characters | Not applicable | No | `MR` |
| `MARKER_ID_BEACON` | Location Identifier of Beacon at Marker | Text, up to 2 characters | Not applicable | Yes | `AN` |
| `COMPASS_LOCATOR_NAME` | Name of the Marker Locator Beacon | Text, up to 30 characters | Not applicable | Yes | `BOGGA` |
| `FREQ` | NAVAID Frequency when Marker is collocated else Locator Frequency (in KHZ) | Numeric (5,2) (precision, scale) | kHz | Yes | `211` |
| `NAV_ID` | Location Identifier of Navigation Aid Collocated With Marker (Blank Indicates Marker Is Not Collocated With A NAVAID) | Text, up to 6 characters | Not applicable | Yes | `AN` |
| `NAV_TYPE` | Collocated NAVAID Type | Text, up to 25 characters | Not applicable | Yes | `NDB` |
| `LOW_POWERED_NDB_STATUS` | Low Powered NDB Status of Marker Beacon | Text, up to 30 characters | Not applicable | Yes | `OPERATIONAL IFR` |

## Sources

- `ILS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ILS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ILS_MKR.csv` from the 2026-08-06 cycle for example values
