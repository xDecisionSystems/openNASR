# `FSS_RMK`

Remarks associated with a Flight Service Station or one of its fields.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FSS_ID` | Flight Service Station Identifier | Text, up to 4 characters | Not applicable | No | `BRW` |
| `NAME` | Flight Service Station Name | Text, up to 30 characters | Not applicable | No | `BARROW` |
| `CITY` | Associated City Name | Text, up to 40 characters | Not applicable | No | `UTQIAGVIK` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AK` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks identified as GENERAL_REMARK. | Text, up to 30 characters | Not applicable | No | `GENERAL_REMARK` |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark | Numeric (3,0) (precision, scale) | Not applicable | No | `1` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 300 characters | Not applicable | No | `FREQ 121.9 USED FOR COMM WITH SNOW PLOWS.` |

## Sources

- `FSS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `FSS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `FSS_RMK.csv` from the 2026-08-06 cycle for example values
