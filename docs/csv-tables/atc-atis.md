# `ATC_ATIS`

Automatic Terminal Information Service records associated with an ATC facility.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. | Text, up to 9 characters | Not specified by FAA | No | `00164.` |
| `SITE_TYPE_CODE` | Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `FACILITY_TYPE` | Facility Type. | Text, up to 12 characters | Not applicable | No | `ATCT-TRACON` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. | Text, up to 4 characters | Not applicable | No | `BHM` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `BIRMINGHAM` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `ATIS_NO` | ATIS Serial Number. | Numeric (3,0) (precision, scale) | Not specified by FAA | No | `1` |
| `DESCRIPTION` | Optional Description of Purpose, Fulfilled by ATIS. | Text, up to 100 characters | Not specified by FAA | Yes | `D-ATIS` |
| `ATIS_HRS` | ATIS Hours of Operation in Local Time. | Text, up to 200 characters | hours | No | `24` |
| `ATIS_PHONE_NO` | ATIS Phone Number. | Text, up to 18 characters | Not specified by FAA | Yes | `251-968-7581` |

## Sources

- `ATC_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ATC DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ATC_ATIS.csv` from the 2026-08-06 cycle for example values
