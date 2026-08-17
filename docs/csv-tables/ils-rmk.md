# `ILS_RMK`

Remarks associated with an instrument landing system or one of its components.

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
| `TAB_NAME` | NASR table associated with Remark. | Text, up to 30 characters | Not applicable | No | `ILS` |
| `ILS_COMP_TYPE_CODE` | TAB_NAME with the Exception of ILS will designate a specific Component Type that the Remark refers to. | Text, up to 3 characters | Not applicable | Yes | `LOC` |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks are identified as GENERAL_REMARK. | Text, up to 30 characters | Not applicable | No | `GENERAL_REMARK` |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark. | Numeric (3,0) (precision, scale) | Not applicable | No | `2` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 300 characters | Not applicable | No | `ILS CLASSIFICATION CODE IA` |

## Sources

- `ILS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ILS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ILS_RMK.csv` from the 2026-08-06 cycle for example values
