# `MAA_CON`

Contacts for a Miscellaneous Activity Area.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. | Text, up to 6 characters | Not applicable | No | `ACO001` |
| `FREQ_SEQ` | Unique Sequence number for Frequency Contact entries | Numeric (2,0) (precision, scale) | Not applicable | No | `1` |
| `FAC_ID` | Contact Facility Identifier | Text, up to 4 characters | Not applicable | Yes | `ZDV` |
| `FAC_NAME` | Contact Facility Name | Text, up to 30 characters | Not applicable | No | `DENVER` |
| `COMMERCIAL_FREQ` | Commercial Frequency | Numeric (7,3) (precision, scale) | Not specified by FAA | No | `128.37` |
| `COMMERCIAL_CHART_FLAG` | Commercial Chart Flag | Text, up to 1 character | Not applicable | Yes | `N` |
| `MIL_FREQ` | Military Frequency | Numeric (7,3) (precision, scale) | Not specified by FAA | Yes | `379.95` |
| `MIL_CHART_FLAG` | Military Chart Flag | Text, up to 1 character | Not applicable | Yes | `N` |

## Sources

- `MAA_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MAA DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MAA_CON.csv` from the 2026-08-06 cycle for example values
