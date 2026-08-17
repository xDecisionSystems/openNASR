# `NAV_CKPT`

Checkpoint information associated with a navaid.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `NAV_ID` | NAVAID Facility Identifier. | Text, up to 4 characters | Not applicable | No | `ACK` |
| `NAV_TYPE` | NAVAID Facility Type. | Text, up to 25 characters | Not applicable | No | `VOR/DME` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `MA` |
| `CITY` | NAVAID Associated City Name | Text, up to 40 characters | Not applicable | No | `NANTUCKET` |
| `COUNTRY_CODE` | Country Post Office Code NAVAID Located | Text, up to 2 characters | Not applicable | No | `US` |
| `ALTITUDE` | Altitude Only When Checkpoint is in Air | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `BRG` | Bearing of Checkpoint | Numeric (3,0) (precision, scale) | Not specified by FAA | No | `242` |
| `AIR_GND_CODE` | Air/Ground Code: A=AIR, G=GROUND, G1=GROUND ONE | Text, up to 2 characters | Not applicable | No | `G` |
| `CHK_DESC` | Narrative Description Associated with the Checkpoint in AIR/Ground | Text, up to 75 characters | Not specified by FAA | No | `1.9 NM ON RUNUP AREA AT APCH END RWY 24.` |
| `ARPT_ID` | Airport ID | Text, up to 4 characters | Not applicable | Yes | `ACK` |
| `STATE_CHK_CODE` | State Code in Which Associated City is Located | Text, up to 2 characters | Not applicable | No | `MA` |

## Sources

- `NAV_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `NAV DATA LAYOUT.pdf` for FAA field definitions and stated units
- `NAV_CKPT.csv` from the 2026-08-06 cycle for example values
