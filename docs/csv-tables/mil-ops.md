# `MIL_OPS`

Military operations and services associated with an airport.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00124.` |
| `SITE_TYPE_CODE` | Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `79J` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `ANDALUSIA` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `MIL_OPS_OPER_CODE` | Military Agency Type Code that Operates the Control Facility. | Text, up to 1 character | Not applicable | Yes | `R` |
| `MIL_OPS_CALL` | Radio Call Name for Military Operations at this Control Facility. | Text, up to 26 characters | Not specified by FAA | Yes | `DIXIE` |
| `MIL_OPS_HRS` | Hours of Military Operations Conducted each Day. | Text, up to 200 characters | hours | Yes | `0700-1730 TUE-SUN` |
| `AMCP_HRS` | Hours of Operation of the Military Aircraft Command Post (AMCP) Located at the Facility. | Text, up to 200 characters | hours | Yes | `0600-2300` |
| `PMSV_HRS` | Hours of Operation of The Military Pilot-To-Metro Service (PMSV) Located at the Facility. | Text, up to 200 characters | hours | Yes | `PART TIME` |
| `REMARK` | Remark associated with Military Operations. | Text, up to 1500 characters | Not applicable | Yes | `(PMSV_HRS) FULL SVC AVBL 1400-0400Z++ WKD; 1600-0000Z++ WKEND; CLSD FEDERAL HOL.` |

## Sources

- `MIL_OPS_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MIL_OPS DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MIL_OPS.csv` from the 2026-08-06 cycle for example values
