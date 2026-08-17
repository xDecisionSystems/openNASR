# `CLS_ARSP`

Airport-linked Class B, C, D, or E airspace configuration and descriptive information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00128.` |
| `SITE_TYPE_CODE` | Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `ANB` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `ANNISTON` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `CLASS_B_AIRSPACE` | Terminal Communication Facility containing Class B Airspace with be designated with ‘Y’ else null. | Text, up to 1 character | Not specified by FAA | Yes | `Y` |
| `CLASS_C_AIRSPACE` | Terminal Communication Facility containing Class C Airspace with be designated with ‘Y’ else null. | Text, up to 1 character | Not specified by FAA | Yes | `Y` |
| `CLASS_D_AIRSPACE` | Terminal Communication Facility containing Class D Airspace with be designated with ‘Y’ else null. | Text, up to 1 character | Not specified by FAA | Yes | `Y` |
| `CLASS_E_AIRSPACE` | Terminal Communication Facility containing Class E Airspace with be designated with ‘Y’ else null. | Text, up to 1 character | Not specified by FAA | Yes | `Y` |
| `AIRSPACE_HRS` | Airspace Hours of Terminal Communication Facility. | Text, up to 300 characters | hours | Yes | `CLASS D SVC 0700-2100 MON-FRI; 0800-1700 SAT & SUN; OTHER TIMES CLASS G` |
| `REMARK` | Remark associated with Class Airspace. | Text, up to 1500 characters | Not applicable | Yes | `(CLASS_B_AIRSPACE) EXPECT TO LEAVE AND RE-ENTER CLASS B ASP DURG MOD TO HVY ARR ` |

## Sources

- `CLS_ARSP_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `CLS_ARSP DATA LAYOUT.pdf` for FAA field definitions and stated units
- `CLS_ARSP.csv` from the 2026-08-06 cycle for example values
