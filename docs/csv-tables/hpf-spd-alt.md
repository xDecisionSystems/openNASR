# `HPF_SPD_ALT`

Published speed and altitude restrictions for a holding pattern.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). | Text, up to 80 characters | Not applicable | No | `AABEE INT*GA*K7` |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern | Numeric (3,0) (precision, scale) | Not specified by FAA | No | `1` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `GA` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | No | `US` |
| `SPEED_RANGE` | Speed Range for Holding Altitude of Record. | Text, up to 7 characters | Not specified by FAA | No | `200` |
| `ALTITUDE` | Holding Altitude for Speed Range of Record. | Text, up to 10 characters | Not specified by FAA | No | `30/54` |

## Sources

- `HPF_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `HPF DATA LAYOUT.pdf` for FAA field definitions and stated units
- `HPF_SPD_ALT.csv` from the 2026-08-06 cycle for example values
