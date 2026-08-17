# `ATC_RMK`

Remarks associated with an ATC facility or one of its fields.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. | Text, up to 9 characters | Not specified by FAA | Yes | `24226.1` |
| `SITE_TYPE_CODE` | Facility Type Code. | Text, up to 1 character | Not applicable | Yes | `A` |
| `FACILITY_TYPE` | Facility Type. | Text, up to 12 characters | Not applicable | No | `NON-ATCT` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `TX` |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. | Text, up to 4 characters | Not applicable | No | `00R` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `LIVINGSTON` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `LEGACY_ELEMENT_NUMBER` | Legacy Remark Element. | Text, up to 30 characters | Not specified by FAA | No | `1` |
| `TAB_NAME` | NASR Table name associated with Remark. | Text, up to 30 characters | Not applicable | No | `ARPT_CTL_REMARK` |
| `REF_COL_NAME` | NASR Column name associated with Remark. ARPT_CTL_REMARKs are identified as ATC_REMARK. All other Non-specific remarks are identified as GENERAL_REMARK. | Text, up to 30 characters | Not applicable | No | `ATC_REMARK` |
| `REMARK_NO` | Sequence number assigned to Reference Column Remark. | Numeric (3,0) (precision, scale) | Not applicable | No | `1` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 1500 characters | Not applicable | No | `APCH/DEP CTL SVC PRVDD BY HOUSTON ARTCC (ZHU) ON FREQS 125.175/285.575 (LUFKIN R` |

## Sources

- `ATC_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ATC DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ATC_RMK.csv` from the 2026-08-06 cycle for example values
