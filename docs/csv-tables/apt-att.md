# `APT_ATT`

Published airport attendance schedules and attendance remarks.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00103.` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `0J0` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `ABBEVILLE` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `SKED_SEQ_NO` | Attendance Schedule Sequence Number (A Number which, together with the Site Number, uniquely identifies the Attendance Schedule Component.) | Numeric (2,0) (precision, scale) | Not applicable | No | `1` |
| `MONTH` | Describes the Months that the Facility is Attended. This field may also contain 'UNATNDD' for unattended Facilities. | Text, up to 50 characters | Not specified by FAA | Yes | `UNATNDD` |
| `DAY` | Describes the Days of the Week that the Facility is Open | Text, up to 16 characters | Not specified by FAA | Yes | `ALL` |
| `HOUR` | Describes the Hours within the Day that the Facility is Attended | Text, up to 40 characters | hours | Yes | `0700-1900` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_ATT.csv` from the 2026-08-06 cycle for example values
