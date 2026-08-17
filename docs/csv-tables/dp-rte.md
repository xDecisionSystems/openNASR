# `DP_RTE`

Ordered departure-procedure routes, transitions, and route points.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `DP_NAME` | Name Assigned to the Departure Procedure. | Text, up to 30 characters | Not applicable | No | `ACCRA` |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. | Text, up to 12 characters | Not specified by FAA | Yes | `ZAU` |
| `DP_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the DP. EX. ADELL6.ADELL | Text, up to 12 characters | Not applicable | No | `ACCRA5.ACCRA` |
| `ROUTE_PORTION_TYPE` | The Segment is identified as either a Transition or Body. | Text, up to 10 characters | Not applicable | No | `BODY` |
| `ROUTE_NAME` | The Transition or Body Name. | Text, up to 110 characters | Not applicable | No | `FANZI-ACCRA` |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given DP, the BODY_SEQ will uniquely identify the Segment. | Numeric (1,0) (precision, scale) | Not applicable | No | `1` |
| `TRANSITION_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the TRANSITION. | Text, up to 20 characters | Not applicable | Yes | `ACONY3.SAPPO` |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Segment. | Numeric (3,0) (precision, scale) | Not applicable | No | `10` |
| `POINT` | The FIX or NAVAID adapted on the Segment. | Text, up to 10 characters | Not specified by FAA | No | `ACCRA` |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Point Types only. | Text, up to 2 characters | Not applicable | Yes | `K5` |
| `POINT_TYPE` | Specific FIX or NAVAID Type. | Text, up to 25 characters | Not applicable | No | `WP` |
| `NEXT_POINT` | The Point that directly follows the current Point on an individual segment. | Text, up to 10 characters | Not specified by FAA | Yes | `HHHUL` |
| `ARPT_RWY_ASSOC` | The list of APT and/or APT/RWY associated with a given Segment. | Text, up to 1500 characters | Not specified by FAA | Yes | `57C/08, 57C/26, BUU/11, BUU/29, ENW, ETB, HXF/09, HXF/27, MKE/01L, MKE/01R, MKE/` |

## Sources

- `DP_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `DP DATA LAYOUT.pdf` for FAA field definitions and stated units
- `DP_RTE.csv` from the 2026-08-06 cycle for example values
