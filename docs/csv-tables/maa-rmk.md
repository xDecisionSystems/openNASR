# `MAA_RMK`

Remarks associated with a Miscellaneous Activity Area.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. | Text, up to 6 characters | Not applicable | No | `AAR002` |
| `TAB_NAME` | NASR table name associated with the remark. | Text, up to 30 characters | Not applicable | No | `MISC_ACTIVITY_AREA` |
| `REF_COL_NAME` | NASR column name associated with the remark; identifies a general remark when no specific source column applies. | Text, up to 30 characters | Not applicable | No | `GENERAL_REMARK` |
| `REF_COL_SEQ_NO` | Sequence number of the source record associated with the remark. | Numeric (3,0) (precision, scale) | Not applicable | No | `1` |
| `REMARK` | Free-form FAA remark text associated with the record or referenced field. | Text, up to 300 characters | Not applicable | No | `THIS APA WOULD BE USED ON AVERAGE OF EIGHT HOURS PER MONTH, DURING DAYLIGHT` |

## Sources

- `MAA_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MAA DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MAA_RMK.csv` from the 2026-08-06 cycle for example values
