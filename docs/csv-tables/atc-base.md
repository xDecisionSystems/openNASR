# `ATC_BASE`

Core airport traffic control facility identity, location, and operating information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. | Text, up to 9 characters | Not specified by FAA | Yes | `24226.1` |
| `SITE_TYPE_CODE` | Facility Type Code. | Text, up to 1 character | Not applicable | Yes | `A` |
| `FACILITY_TYPE` | Facility Type. | Text, up to 12 characters | Not applicable | No | `NON-ATCT` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `TX` |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. | Text, up to 4 characters | Not applicable | No | `00R` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `LIVINGSTON` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `ICAO_ID` | ICAO Identifier | Text, up to 7 characters | Not applicable | Yes | `PAKX` |
| `FACILITY_NAME` | Official Facility Name | Text, up to 50 characters | Not applicable | No | `LIVINGSTON MUNI` |
| `REGION_CODE` | FAA Region Code. | Text, up to 3 characters | Not applicable | Yes | `ASW` |
| `TWR_OPERATOR_CODE` | Operator Code of the Agency that Operates the Tower. | Text, up to 6 characters | Not applicable | Yes | `P` |
| `TWR_CALL` | Radio Call used by Pilot to Contact Tower. | Text, up to 26 characters | Not specified by FAA | Yes | `GWINN` |
| `TWR_HRS` | Hours of Tower Operation in Local Time. | Text, up to 200 characters | hours | Yes | `0800-1600 MON-FRI.` |
| `PRIMARY_APCH_RADIO_CALL` | Radio Call of Facility That Furnishes Primary Approach Control. | Text, up to 26 characters | Not specified by FAA | Yes | `HOUSTON ARTCC` |
| `APCH_P_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Primary Approach Control Facility/Functions | Text, up to 700 characters | Not applicable | Yes | `ZHU` |
| `APCH_P_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Primary Approach Control Facility/Functions. | Text, up to 1 character | Not applicable | Yes | `C` |
| `SECONDARY_APCH_RADIO_CALL` | Radio Call of Facility That Furnishes Secondary Approach Control. | Text, up to 26 characters | Not specified by FAA | Yes | `ATLANTA ARTCC` |
| `APCH_S_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Secondary Approach Control Facility/Functions | Text, up to 700 characters | Not applicable | Yes | `ZTL` |
| `APCH_S_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Secondary Approach Control Facility/Functions. | Text, up to 1 character | Not applicable | Yes | `C` |
| `PRIMARY_DEP_RADIO_CALL` | Radio Call of Facility That Furnishes Primary Departure Control. | Text, up to 26 characters | Not specified by FAA | Yes | `HOUSTON ARTCC` |
| `DEP_P_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Primary Departure Control Facility/Functions | Text, up to 700 characters | Not applicable | Yes | `ZHU` |
| `DEP_P_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Primary Departure Control Facility/Functions. | Text, up to 1 character | Not applicable | Yes | `C` |
| `SECONDARY_DEP_RADIO_CALL` | Radio Call of Facility That Furnishes Secondary Departure Control. | Text, up to 26 characters | Not specified by FAA | Yes | `ATLANTA ARTCC` |
| `DEP_S_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Secondary Departure Control Facility/Functions | Text, up to 700 characters | Not applicable | Yes | `ZTL` |
| `DEP_S_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Secondary Departure Control Facility/Functions. | Text, up to 1 character | Not applicable | Yes | `C` |
| `CTL_FAC_APCH_DEP_CALLS` | Approach Departure Call associated with a Control Facility. | Text, up to 54 characters | Not specified by FAA | Yes | `ANCHORAGE` |
| `APCH_DEP_OPER_CODE` | Agency Type Code that Operates the Control Facility | Text, up to 1 character | Not applicable | Yes | `F` |
| `CTL_PRVDING_HRS` | Hours of Operation of the Primary Control Facility. | Text, up to 200 characters | hours | Yes | `24` |
| `SECONDARY_CTL_PRVDING_HRS` | Hours of Operation of the Secondary Control Facility. | Text, up to 200 characters | hours | Yes | `0000-0600` |

## Sources

- `ATC_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `ATC DATA LAYOUT.pdf` for FAA field definitions and stated units
- `ATC_BASE.csv` from the 2026-08-06 cycle for example values
