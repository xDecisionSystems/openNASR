# `AWY_BASE`

Airway identity, designation, effective-date, and route-string information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `REGULATORY` | Identifies Airways published under 14 CFR (Code of Federal Regulation) Part-71 and Part- 95 – Y/N. | Text, up to 1 character | Not specified by FAA | No | `N` |
| `AWY_DESIGNATION` | Airway Designation. | Text, up to 2 characters | Not specified by FAA | No | `PA` |
| `AWY_LOCATION` | Airway Type which identifies the General Location of the Airway. | Text, up to 1 character | Not specified by FAA | No | `C` |
| `AWY_ID` | Airway Identifier. | Text, up to 12 characters | Not applicable | No | `A216` |
| `UPDATE_DATE` | The Last Date for which the AIRWAY Data amended. | Text, up to 10 characters | Not applicable | No | `2014/06/02` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 1500 characters | Not applicable | Yes | `VIRGINIA KEY R-058 UNUSABLE JANUS TO VALLY` |
| `AIRWAY_STRING` | List of FIX and NAVAID that make up the AIRWAY in order adapted. | Text, up to 1500 characters | Not specified by FAA | No | `MONPI OATSS RIDLL LOEBB HOOVR GALEE FACED` |

## Sources

- `AWY_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `AWY DATA LAYOUT.pdf` for FAA field definitions and stated units
- `AWY_BASE.csv` from the 2026-08-06 cycle for example values
