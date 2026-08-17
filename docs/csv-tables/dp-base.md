# `DP_BASE`

Departure procedure identity, controlling ARTCC, and published metadata.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `DP_NAME` | Name Assigned to the Departure Procedure. | Text, up to 30 characters | Not applicable | No | `ACCRA` |
| `AMENDMENT_NO` | Amendment Number (spelled out) of the DP that will be Active on the Effective Date. | Text, up to 5 characters | Not specified by FAA | No | `FIVE` |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. | Text, up to 12 characters | Not specified by FAA | Yes | `ZAU` |
| `DP_AMEND_EFF_DATE` | The First Effective Date for which the DP Amendment became Active. | Text, up to 10 characters | Not applicable | No | `2020/03/26` |
| `RNAV_FLAG` | Y/N Flag determines whether a DP is RNAV required. | Text, up to 1 character | Not applicable | No | `Y` |
| `DP_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the DP. EX. ADELL6.ADELL | Text, up to 12 characters | Not applicable | No | `ACCRA5.ACCRA` |
| `GRAPHICAL_DP_TYPE` | Identifies whether the Graphical DP is type SID or OBSTACLE. | Text, up to 9 characters | Not applicable | No | `SID` |
| `SERVED_ARPT` | List of Airports Served by the DP. | Text, up to 200 characters | Not specified by FAA | No | `57C BUU ENW ETB HXF MKE MWC RAC UES` |

## Sources

- `DP_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `DP DATA LAYOUT.pdf` for FAA field definitions and stated units
- `DP_BASE.csv` from the 2026-08-06 cycle for example values
