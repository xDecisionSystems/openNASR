# `NAV_RMK`

Remarks associated with a navaid or one of its fields.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `NAV_ID` | NAVAID Facility Identifier. | Text, up to 4 characters | Not applicable | No | `AA` |
| `NAV_TYPE` | NAVAID Facility Type. | Text, up to 25 characters | Not applicable | No | `NDB` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `GA` |
| `CITY` | NAVAID Associated City Name | Text, up to 40 characters | Not applicable | No | `THOMSON` |
| `COUNTRY_CODE` | Country Post Office Code NAVAID Located | Text, up to 2 characters | Not applicable | No | `US` |
| `TAB_NAME` | NASR table associated with Remark. | Text, up to 30 characters | Not applicable | No | `NAVIGATION_AID` |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks are identified as GENERAL_REMARK. | Text, up to 30 characters | Not applicable | No | `GENERAL_REMARK` |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark. | Numeric (3,0) (precision, scale) | Not applicable | No | `1` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 600 characters | Not applicable | No | `NDB UNUSBL BYD 15 NM.` |

## Sources

- `NAV_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `NAV DATA LAYOUT.pdf` for FAA field definitions and stated units
- `NAV_RMK.csv` from the 2026-08-06 cycle for example values
