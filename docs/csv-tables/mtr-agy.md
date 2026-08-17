# `MTR_AGY`

Scheduling and originating agencies associated with a military training route.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `ROUTE_TYPE_CODE` | MTR Type Code. | Text, up to 2 characters | Not applicable | No | `IR` |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. | Text, up to 5 characters | Not applicable | No | `002` |
| `ARTCC` | List of ARTCC Idents that MTR traverses. | Text, up to 80 characters | Not specified by FAA | Yes | `ZTL` |
| `AGENCY_TYPE` | MTR Agency Type Code. | Text, up to 2 characters | Not applicable | No | `O` |
| `AGENCY_NAME` | Agency Organization Name | Text, up to 30 characters | Not applicable | No | `COMSTRKFIGHTWINGLANT` |
| `STATION` | Agency Station | Text, up to 30 characters | Not specified by FAA | Yes | `OCEANA NAS` |
| `ADDRESS` | Agency Address | Text, up to 35 characters | Not specified by FAA | Yes | `MCAS` |
| `CITY` | Agency City | Text, up to 30 characters | Not applicable | Yes | `VIRGINIA BEACH` |
| `STATE_CODE` | Agency State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `VA` |
| `ZIP_CODE` | Agency ZIP Code | Text, up to 10 characters | Not applicable | Yes | `23460` |
| `COMMERCIAL_NO` | Agency Commercial Phone Number | Text, up to 40 characters | Not specified by FAA | Yes | `757-433-9141` |
| `DSN_NO` | Agency DSN Phone Number | Text, up to 40 characters | Not specified by FAA | Yes | `433-9141` |
| `HOURS` | Agency Hours | Text, up to 175 characters | hours | Yes | `SEE GENERAL REMARKS` |

## Sources

- `MTR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MTR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MTR_AGY.csv` from the 2026-08-06 cycle for example values
