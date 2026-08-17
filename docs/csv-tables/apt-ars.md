# `APT_ARS`

Airport arresting systems and the runways on which they are installed.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00447.` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `MGM` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `MONTGOMERY` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `RWY_ID` | Runway Identification | Text, up to 7 characters | Not applicable | No | `10/28` |
| `RWY_END_ID` | Runway End Identifier (The Runway End described by the Arresting System Information.) | Text, up to 3 characters | Not applicable | No | `10` |
| `ARREST_DEVICE_CODE` | Type of Aircraft Arresting Device (Indicates Type of Jet Arresting Barrier installed at the Far End.) Possible Values: | Text, up to 9 characters | Not applicable | No | `BAK-12B` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_ARS.csv` from the 2026-08-06 cycle for example values
