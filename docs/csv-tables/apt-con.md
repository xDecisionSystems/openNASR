# `APT_CON`

Airport owner, manager, and other published contact information.

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
| `TITLE` | Title of Contact (MANAGER, OWNER, ASST-MGR, etc.) | Text, up to 10 characters | Not specified by FAA | No | `MANAGER` |
| `NAME` | Facility Contact Name for Title | Text, up to 35 characters | Not applicable | Yes | `MELISSA WILSON` |
| `ADDRESS1` | Title Address1 | Text, up to 35 characters | Not specified by FAA | Yes | `PO BOX 427` |
| `ADDRESS2` | Title Address2 | Text, up to 35 characters | Not specified by FAA | Yes | `101 E. WASHINGTON ST` |
| `TITLE_CITY` | Title City | Text, up to 30 characters | Not applicable | Yes | `ABBEVILLE` |
| `STATE` | Title State | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ZIP_CODE` | Title Zip Code | Text, up to 5 characters | Not applicable | Yes | `36310` |
| `ZIP_PLUS_FOUR` | Title Zip Plus Four | Text, up to 4 characters | Not specified by FAA | Yes | `6516` |
| `PHONE_NO` | Title Phone Number | Text, up to 16 characters | Not specified by FAA | Yes | `334-585-6444` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_CON.csv` from the 2026-08-06 cycle for example values
