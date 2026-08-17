# `FIX_NAV`

Navaids and radials associated with a fix.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FIX_ID` | Fixed Geographical Position Identifier. | Text, up to 30 characters | Not applicable | No | `AABEE` |
| `ICAO_REGION_CODE` | International Civil Aviation Organization (ICAO) Code. In General, the First Letter of an ICAO Code refers to the Country. The Second Letter discerns the Region within the Country. | Text, up to 2 characters | Not applicable | No | `K7` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `GA` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `NAV_ID` | NAVAID Identifier. | Text, up to 6 characters | Not applicable | No | `PDK` |
| `NAV_TYPE` | Facility Type. | Text, up to 25 characters | Not applicable | No | `LOC` |
| `BEARING` | Bearing, Radial, Direction or Course depending on Facility Type. | Numeric (5,2) (precision, scale) | Not specified by FAA | Yes | `25.51` |
| `DISTANCE` | DME Distance from Facility. | Numeric (7,2) (precision, scale) | Not specified by FAA | Yes | `12.86` |

## Sources

- `FIX_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `FIX DATA LAYOUT.pdf` for FAA field definitions and stated units
- `FIX_NAV.csv` from the 2026-08-06 cycle for example values
