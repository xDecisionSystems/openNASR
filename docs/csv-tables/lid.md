# `LID`

FAA location identifiers and their associated facility, state, country, and controlling organization.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `COUNTRY_CODE` | Country Code Associated with The Location Identifier. | Text, up to 2 characters | Not applicable | No | `US` |
| `LOC_ID` | Location Identifier. 3-4 character alphanumeric identifier. | Text, up to 4 characters | Not applicable | No | `00A` |
| `REGION_CODE` | FAA Region Code Associated with The Location Identifier | Text, up to 3 characters | Not applicable | Yes | `AEA` |
| `STATE` | State or territory name associated with the location identifier. | Text, up to 30 characters | Not applicable | Yes | `PA` |
| `CITY` | City Name Associated with The Location Identifier. | Text, up to 40 characters | Not applicable | No | `BENSALEM` |
| `LID_GROUP` | Logical grouping of LID entries. CONTROL FACILITY FLIGHT SERVICE STATION INSTRUMENT LANDING FACILITY LANDING FACILITY NAVIGATION AID REMOTE COMMINICATION OUTLET SPECIAL USE RESOURCE WEATHER REPORTING STATION WEATHER SENSOR | Text, up to 30 characters | Not applicable | No | `LANDING FACILITY` |
| `FAC_TYPE` | Facility Type of Location Identifier Record | Text, up to 30 characters | Not applicable | No | `H` |
| `FAC_NAME` | Official Facility Name. Instrument Landing System Facility Name is a concatenation of the Associated Landing Facility Name, ID and Runway End ID (e.g. ATLANTIC CITY INTL(ACY) ILS RWY 31) LID | Text, up to 75 characters | Not applicable | Yes | `TOTAL RF` |
| `RESP_ARTCC_ID` | Responsible FAA Air Route Traffic Control Center (ARTCC) Identifier | Text, up to 4 characters | Not applicable | Yes | `ZNY` |
| `ARTCC_COMPUTER_ID` | Responsible ARTCC Computer Identifier | Text, up to 3 characters | Not applicable | Yes | `ZCN` |
| `FSS_ID` | Tie-In Flight Service Station (FSS) Identifier | Text, up to 4 characters | Not applicable | Yes | `IPT` |

## Sources

- `LID_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `LID DATA LAYOUT.pdf` for FAA field definitions and stated units
- `LID.csv` from the 2026-08-06 cycle for example values
