# `PFR_BASE`

Preferred-route identity, origin, destination, type, direction, and route text.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `ORIGIN_ID` | Origin Facility Location Identifier (Depending on NAR Type and Direction, Origin ID Is either Coastal Fix or Inland NAV Facility or Fix) | Text, up to 5 characters | Not applicable | No | `ABE` |
| `ORIGIN_CITY` | Origin Facility Associated City Name. | Text, up to 40 characters | Not applicable | Yes | `ALLENTOWN` |
| `ORIGIN_STATE_CODE` | This is the two letter state ID of the Origin Facility location. NULL if outside the US. | Text, up to 2 characters | Not applicable | Yes | `PA` |
| `ORIGIN_COUNTRY_CODE` | Country Code of the Origin Facility Located. | Text, up to 2 characters | Not applicable | No | `US` |
| `DSTN_ID` | Destination Facility Location Identifier (Depending on NAR Type and Direction, Destination ID Is either Airport, Coastal Fix or Inland NAV Facility or Fix) | Text, up to 5 characters | Not applicable | No | `ACY` |
| `DSTN_CITY` | Destination Facility Associated City Name. | Text, up to 40 characters | Not applicable | Yes | `ATLANTIC CITY` |
| `DSTN_STATE_CODE` | This is the two letter state ID of the Destination Facility location. NULL if outside the US. | Text, up to 2 characters | Not applicable | Yes | `NJ` |
| `DSTN_COUNTRY_CODE` | Country Code of the Destination Facility Located. | Text, up to 2 characters | Not applicable | No | `US` |
| `PFR_TYPE_CODE` | Type Code of Preferred Route Description. | Text, up to 3 characters | Not applicable | No | `TEC` |
| `ROUTE_NO` | Route Identifier Sequence Number (1-99) | Numeric (2,0) (precision, scale) | Not specified by FAA | No | `1` |
| `SPECIAL_AREA_DESCRIP` | Preferred Route Area Description. | Text, up to 75 characters | Not specified by FAA | Yes | `TO ALB,SCH` |
| `ALT_DESCRIP` | Preferred Route Altitude Description. | Text, up to 40 characters | Not specified by FAA | Yes | `5000` |
| `AIRCRAFT` | Aircraft Allowed/Limitations Description | Text, up to 50 characters | Not specified by FAA | Yes | `PROPS LESS THAN 210 KTS IAS` |
| `HOURS` | Effective Hours (GMT) Description * All Preferred IFR Routes are in Effect Continuously Unless Otherwise Noted. | Text, up to 15 characters | hours | Yes | `1100-0400` |
| `ROUTE_DIR_DESCRIP` | Route Direction Limitations Description | Text, up to 20 characters | Not specified by FAA | Yes | `IAH EAST FLOW` |
| `DESIGNATOR` | Preferred Route Designator if applicable | Text, up to 5 characters | Not specified by FAA | Yes | `ONTQ8` |
| `NAR_TYPE` | North American Route Type (COMMON, NON-COMMON) | Text, up to 20 characters | Not applicable | Yes | `NON-COMMON` |
| `INLAND_FAC_FIX` | North American Route Inland NAV Facility or Fix is the Origin on COMMON EASTBOUND and NON-COMMON (Eastbound or Westbound) and the Destination on COMMON WESTBOUND. | Text, up to 5 characters | Not specified by FAA | Yes | `ALLEX` |
| `COASTAL_FIX` | North American Route Coastal Fix is the Origin on COMMON WESTBOUND and the Destination on COMMON EASTBOUND. | Text, up to 5 characters | Not specified by FAA | Yes | `ALLRY` |
| `DESTINATION` | North American Route Destination for NON_COMMON (Eastbound or Westbound). | Text, up to 40 characters | Not specified by FAA | Yes | `ANDREWS` |
| `ROUTE_STRING` | Preferred Route String. *Canadian DPs and STARs will use the generic format of “-DP” and “-STAR”. See the Canadian Aeronautical Data for the correct amendment number for filing. | Text, up to 300 characters | Not specified by FAA | Yes | `FJC ARD CYN` |

## Sources

- `PFR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `PFR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `PFR_BASE.csv` from the 2026-08-06 cycle for example values
