# `MTR_SOP`

Special operating procedures for a military training route.

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
| `SOP_SEQ_NO` | SOP Text Computer assigned Sequence Number | Numeric (3,0) (precision, scale) | Not applicable | No | `4` |
| `SOP_TEXT` | Standard Operating Procedure Text | Text, up to 100 characters | Not applicable | No | `(1) ROUTE RESERVATION AND BRIEF REQUIRED.` |

## Sources

- `MTR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MTR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MTR_SOP.csv` from the 2026-08-06 cycle for example values
