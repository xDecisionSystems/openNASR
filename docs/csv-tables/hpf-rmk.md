# `HPF_RMK`

Remarks associated with a holding pattern or one of its fields.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). | Text, up to 80 characters | Not applicable | No | `ALWYZ INT*VA*K6` |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern | Numeric (3,0) (precision, scale) | Not specified by FAA | No | `1` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `VA` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `TAB_NAME` | NASR table associated with Remark. | Text, up to 30 characters | Not applicable | No | `HOLDING_PATTERN` |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks are identified as GENERAL_REMARK. | Text, up to 30 characters | Not applicable | No | `GENERAL_REMARK` |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark. | Numeric (3,0) (precision, scale) | Not applicable | No | `1` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 300 characters | Not applicable | No | `CHART 210K ICON` |

## Sources

- `HPF_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `HPF DATA LAYOUT.pdf` for FAA field definitions and stated units
- `HPF_RMK.csv` from the 2026-08-06 cycle for example values
