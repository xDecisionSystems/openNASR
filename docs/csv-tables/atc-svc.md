# `ATC_SVC`

Services published for an airport traffic control facility.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. | Text, up to 9 characters | Not specified by FAA | Yes | `19673.` |
| `SITE_TYPE_CODE` | Facility Type Code. | Text, up to 1 character | Not applicable | Yes | `A` |
| `FACILITY_TYPE` | Facility Type. | Text, up to 12 characters | Not applicable | No | `TRACON` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `GA` |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. | Text, up to 4 characters | Not applicable | No | `A80` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `PEACHTREE CITY` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `CTL_SVC` | Services Provided to Satellite Airport. | Text, up to 200 characters | Not specified by FAA | No | `ARTS-IIIE` |

## Sources

- `ATC_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ATC DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ATC_SVC.csv` from the 2026-08-06 cycle for example values
