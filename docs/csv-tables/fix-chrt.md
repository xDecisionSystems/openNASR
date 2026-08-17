# `FIX_CHRT`

Charts on which a fix is published.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FIX_ID` | Fixed Geographical Position Identifier. | Text, up to 30 characters | Not applicable | No | `AAALL` |
| `ICAO_REGION_CODE` | International Civil Aviation Organization (ICAO) Code. In General, the First Letter of an ICAO Code refers to the Country. The Second Letter discerns the Region within the Country. | Text, up to 2 characters | Not applicable | No | `K6` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `MA` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `CHARTING_TYPE_DESC` | Chart on Which Fix Is To Be Depicted | Text, up to 22 characters | Not applicable | No | `IAP` |

## Sources

- `FIX_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `FIX DATA LAYOUT.pdf` for FAA field definitions and stated units
- `FIX_CHRT.csv` from the 2026-08-06 cycle for example values
