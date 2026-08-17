# `COM`

Remote communications outlets and related communication facility information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `COMM_LOC_ID` | Communications Outlet Ident. A 3-4 character alphanumeric identifier. COMM_TYPE RCAG do not currently have a 3-4 character identifier stored in NASR. | Text, up to 6 characters | Not applicable | Yes | `05U` |
| `COMM_TYPE` | Communication Outlet Type – RCAG, RCO or RCO1. RCAG is a Remote Communications, Air/Ground. RCO and RCO1 are the same and Serve the Same Function; A Remote Communication Outlet. An RCO1 may exist if two separate sites share the same identifier, e.g. one is collocated with a NAVAID, the Other Is Physically on Airport Property. | Text, up to 5 characters | Not applicable | No | `RCO` |
| `NAV_ID` | Associated NAVAID Ident - Applies to RCO/RCO1 types only. | Text, up to 4 characters | Not applicable | Yes | `ABR` |
| `NAV_TYPE` | Associated NAVAID Type - Applies to RCO/RCO1 types only. | Text, up to 25 characters | Not applicable | Yes | `VOR/DME` |
| `CITY` | Communications Outlet City Name. RCAG do not have an Associated City stored in NASR. | Text, up to 40 characters | Not applicable | Yes | `EUREKA` |
| `STATE_CODE` | Associated State Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `NV` |
| `REGION_CODE` | FAA Region responsible for Communications Outlet (code) | Text, up to 3 characters | Not applicable | Yes | `AWP` |
| `COUNTRY_CODE` | Country Code Communications Outlet is Located. | Text, up to 2 characters | Not applicable | No | `US` |
| `COMM_OUTLET_NAME` | Communications Outlet Name. The Communications Outlet Name is also used as the Communications Outlet Call. | Text, up to 30 characters | Not applicable | No | `EUREKA` |
| `LAT_DEG` | Communications Outlet Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `39` |
| `LAT_MIN` | Communications Outlet Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `28` |
| `LAT_SEC` | Communications Outlet Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `46.7` |
| `LAT_HEMIS` | Communications Outlet Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Communications Outlet Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `39.47963888` |
| `LONG_DEG` | Communications Outlet Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `115` |
| `LONG_MIN` | Communications Outlet Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `59` |
| `LONG_SEC` | Communications Outlet Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `30.2` |
| `LONG_HEMIS` | Communications Outlet Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Communications Outlet Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-115.99172222` |
| `FACILITY_ID` | For RCO and RCO1, the Facility ID is the Associated Flight Service Station Ident. For RCAG, the Facility ID is the Associated ARTCC. | Text, up to 4 characters | Not applicable | No | `RNO` |
| `FACILITY_NAME` | For RCO and RCO1, the Facility Name is the Associated Flight Service Station Name. For RCAG, the Facility Name is the Associated ARTCC Name. | Text, up to 30 characters | Not applicable | No | `RENO` |
| `ALT_FSS_ID` | Associated Alternate Flight Service Station Ident - Applies to RCO/RCO1 types only. | Text, up to 4 characters | Not applicable | Yes | `JNU` |
| `ALT_FSS_NAME` | Associated Alternate Flight Service Station Name - Applies to RCO/RCO1 types only. | Text, up to 30 characters | Not applicable | Yes | `JUNEAU` |
| `OPR_HRS` | Standard Time Zone - Applies to RCO/RCO1 types only. | Text, up to 65 characters | Not specified by FAA | Yes | `24` |
| `COMM_STATUS_CODE` | Communication Outlet Status - Applies to RCO/RCO1 types only. | Text, up to 1 character | Not applicable | Yes | `A` |
| `COMM_STATUS_DATE` | STATUS Date of Communications Outlet - Applies to RCO/RCO1 types only. | Text, up to 10 characters | Not applicable | Yes | `2020/04/24` |
| `REMARK` | Remark associated with Communications Outlet. | Text, up to 1500 characters | Not applicable | Yes | `(COMM_LOC_ID) FREQ 122.5 ALSO AVBL AT CORDOVA MUNI & CORDOVA MUNI SEAPLANE.` |

## Sources

- `COM_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `COM DATA LAYOUT.pdf` for FAA field definitions and stated units
- `COM.csv` from the 2026-08-06 cycle for example values
