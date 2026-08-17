# `WXL_SVC`

Weather services published for a weather-reporting location.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `WEA_ID` | Weather Reporting Location Identifier | Text, up to 4 characters | Not applicable | No | `00U` |
| `CITY` | Associated City Name | Text, up to 40 characters | Not applicable | No | `HARDIN` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `MT` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `WEA_SVC_TYPE_CODE` | Weather Services Available at Location | Text, up to 5 characters | Not applicable | No | `METAR` |
| `WEA_AFFECT_AREA` | Affected State/Area. An Alphabetically Ordered Series of Two Character US State Post Office Abbreviations Separated by Commas. Values May Also Include LE, LH, LM, LO, LS for the Great Lakes (Erie, Huron, Michigan, Ontario, Superior) | Text, up to 200 characters | Not specified by FAA | Yes | `AZ` |

## Sources

- `WXL_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `WXL DATA LAYOUT.pdf` for FAA field definitions and stated units
- `WXL_SVC.csv` from the 2026-08-06 cycle for example values
