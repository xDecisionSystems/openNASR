# `FIX_BASE`

Core fix identity, coordinates, location, use, and controlling-facility information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FIX_ID` | Fixed Geographical Position Identifier. | Text, up to 30 characters | Not applicable | No | `AAALL` |
| `ICAO_REGION_CODE` | International Civil Aviation Organization (ICAO) Code. In General, the First Letter of an ICAO Code refers to the Country. The Second Letter discerns the Region within the Country. | Text, up to 2 characters | Not applicable | No | `K6` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `MA` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `LAT_DEG` | FIX Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `42` |
| `LAT_MIN` | FIX Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `7` |
| `LAT_SEC` | FIX Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `12.68` |
| `LAT_HEMIS` | FIX Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | FIX Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `42.12018888` |
| `LONG_DEG` | FIX Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `71` |
| `LONG_MIN` | FIX Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `8` |
| `LONG_SEC` | FIX Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `30.34` |
| `LONG_HEMIS` | FIX Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | FIX Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-71.14176111` |
| `FIX_ID_OLD` | Previous Name(s) of the Fix before It was Renamed. | Text, up to 30 characters | Not applicable | Yes | `MOROW` |
| `CHARTING_REMARK` | Charting Information. | Text, up to 38 characters | Not applicable | Yes | `RNAV` |
| `FIX_USE_CODE` | FIX Type. | Text, up to 5 characters | Not applicable | No | `WP` |
| `ARTCC_ID_HIGH` | Denotes High ARTCC Area Of Jurisdiction. | Text, up to 4 characters | Not applicable | Yes | `ZBW` |
| `ARTCC_ID_LOW` | Denotes Low ARTCC Area Of Jurisdiction. | Text, up to 4 characters | Not applicable | No | `ZBW` |
| `PITCH_FLAG` | Pitch (Y = YES or N = NO) | Text, up to 1 character | Not applicable | No | `N` |
| `CATCH_FLAG` | Catch (Y = YES or N = NO) | Text, up to 1 character | Not applicable | No | `N` |
| `SUA_ATCAA_FLAG` | SUA/ATCAA (Y = YES or N = NO) | Text, up to 1 character | Not applicable | No | `N` |
| `MIN_RECEP_ALT` | Fix Minimum Reception Altitude (MRA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `8000` |
| `COMPULSORY` | Compulsory FIX identified as HIGH or LOW or LOW/HIGH. Null in this field identifies Non-Compulsory FIX. | Text, up to 8 characters | Not specified by FAA | Yes | `HIGH` |
| `CHARTS` | Concatenated list of the information found in the FIX_CHRT file separated by a comma. | Text, up to 600 characters | Not specified by FAA | Yes | `IAP` |

## Sources

- `FIX_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `FIX DATA LAYOUT.pdf` for FAA field definitions and stated units
- `FIX_BASE.csv` from the 2026-08-06 cycle for example values
