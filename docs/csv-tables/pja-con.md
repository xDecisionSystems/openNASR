# `PJA_CON`

Contacts for a Parachute Jump Area.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `PJA_ID` | PJA ID that uniquely identifies a Parachute Jump Area. | Text, up to 6 characters | Not applicable | No | `PAK002` |
| `FAC_ID` | Contact Facility Identifier | Text, up to 4 characters | Not applicable | Yes | `FAI` |
| `FAC_NAME` | Contact Facility Name | Text, up to 50 characters | Not applicable | No | `FAIRBANKS INTL` |
| `LOC_ID` | Related Location Identifier | Text, up to 4 characters | Not applicable | No | `FAI` |
| `COMMERCIAL_FREQ` | Commercial Frequency | Numeric (7,3) (precision, scale) | Not specified by FAA | No | `126.5` |
| `COMMERCIAL_CHART_FLAG` | Commercial Chart Flag | Text, up to 1 character | Not applicable | No | `Y` |
| `MIL_FREQ` | Military Frequency | Numeric (7,3) (precision, scale) | Not specified by FAA | Yes | `278.3` |
| `MIL_CHART_FLAG` | Military Chart Flag | Text, up to 1 character | Not applicable | Yes | `N` |
| `SECTOR` | Sector Description Text | Text, up to 30 characters | Not specified by FAA | Yes | `SOUTH` |
| `CONTACT_FREQ_ALTITUDE` | Altitude Description Text | Text, up to 20 characters | Not specified by FAA | Yes | `10500` |

## Sources

- `PJA_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `PJA DATA LAYOUT.pdf` for FAA field definitions and stated units
- `PJA_CON.csv` from the 2026-08-06 cycle for example values
