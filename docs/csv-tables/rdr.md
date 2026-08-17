# `RDR`

Radar site identity, location, type, status, and owning-facility information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. | Text, up to 4 characters | Not applicable | No | `ABE` |
| `FACILITY_TYPE` | Type of Facility associated with the RADAR data – either AIRPORT or TRACON. | Text, up to 7 characters | Not applicable | No | `AIRPORT` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `PA` |
| `COUNTRY_CODE` | Country Post Office Code Airport or TRACON is Located. | Text, up to 2 characters | Not applicable | No | `US` |
| `RADAR_TYPE` | RADAR Type Code. | Text, up to 10 characters | Not applicable | No | `ASR` |
| `RADAR_NO` | Unique Sequence Number assigned to each Radar at a Facility. | Numeric (3,0) (precision, scale) | Not specified by FAA | No | `1` |
| `RADAR_HRS` | RADAR Hours of Operation. | Text, up to 200 characters | hours | No | `24` |
| `REMARK` | Remark associated with RADAR Operations. | Text, up to 1500 characters | Not applicable | Yes | `(RADAR_TYPE) RADAR - PAR - NO NOTAM MP: 1500-1730Z++ MON-FRI.` |

## Sources

- `RDR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `RDR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `RDR.csv` from the 2026-08-06 cycle for example values
