# `APT_RMK`

Remarks associated with an airport or a specific airport field.

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
| `LEGACY_ELEMENT_NUMBER` | Legacy Remark Element Number. The Legacy element number field is equivalent to the LEGACY_ELEMENT_NAME field referenced in the TXT APT.txt NASR Subscriber File. | Text, up to 30 characters | Not specified by FAA | No | `E111` |
| `TAB_NAME` | NASR Table name associated with Remark. | Text, up to 30 characters | Not applicable | No | `AIRPORT` |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks are identified as GENERAL_REMARK. | Text, up to 30 characters | Not applicable | No | `ASP_ANLYS_DTRM_CODE` |
| `ELEMENT` | Specific Element that Remark Text Pertains to. Not all Tables require Element to be Unique. | Text, up to 30 characters | Not specified by FAA | Yes | `05` |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark. | Numeric (3,0) (precision, scale) | Not applicable | No | `1` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 1500 characters | Not applicable | No | `EXISTED PRIOR TO MAY 15, 1959.` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_RMK.csv` from the 2026-08-06 cycle for example values
