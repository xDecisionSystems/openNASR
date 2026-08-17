# `PFR_RMT_FMT`

Published route-format variants for a preferred route.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `Orig` | Origin Facility Location Identifier (Depending on NAR Type and Direction, Origin ID Is either Coastal Fix or Inland NAV Facility or Fix) | Text, up to 5 characters | Not specified by FAA | No | `ABE` |
| `Route String` | Preferred Route String which starts with Orig and ends with Dest. *Canadian DPs and STARs will use the generic format of “-DP” and “-STAR”. See the Canadian Aeronautical Data for the correct amendment number for filing. | Text, up to 300 characters | Not specified by FAA | Yes | `ABE FJC ARD CYN ACY` |
| `Dest` | Destination Facility Location Identifier (Depending on NAR Type and Direction, Destination ID Is either Airport, Coastal Fix or Inland NAV Facility or Fix) | Text, up to 5 characters | Not specified by FAA | No | `ACY` |
| `Hours1` | Effective Hours (GMT) Description * All Preferred IFR Routes are in Effect Continuously Unless Otherwise Noted. | Text, up to 15 characters | hours | Yes | `1100-0400` |
| `Type` | Type Code of Preferred Route Description. | Text, up to 3 characters | Not applicable | No | `TEC` |
| `Area` | Preferred Route Area Description. | Text, up to 75 characters | Not specified by FAA | Yes | `TO ALB,SCH` |
| `Altitude` | Preferred Route Altitude Description. | Text, up to 40 characters | Not specified by FAA | Yes | `5000` |
| `Aircraft` | Aircraft Allowed/Limitations Description | Text, up to 50 characters | Not specified by FAA | Yes | `PROPS LESS THAN 210 KTS IAS` |
| `Direction` | Route Direction Limitations Description | Text, up to 20 characters | Not specified by FAA | Yes | `WESTBOUND` |
| `Seq` | Route Identifier Sequence Number (1-99) | Numeric (2,0) (precision, scale) | Not applicable | No | `1` |
| `DCNTR` | Departure ARTCC associated with a given PFR. | Text, up to 4 characters | Not specified by FAA | Yes | `ZNY` |
| `ACNTR` | Arrival ARTCC associated with a given PFR. | Text, up to 4 characters | Not specified by FAA | Yes | `ZDC` |

## Sources

- `PFR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `PFR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `PFR_RMT_FMT.csv` from the 2026-08-06 cycle for example values
