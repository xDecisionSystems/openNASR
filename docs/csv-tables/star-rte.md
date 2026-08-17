# `STAR_RTE`

Ordered arrival routes, transitions, and route points.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `STAR_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the STAR. EX. GLAND.BLUMS5 | Text, up to 12 characters | Not applicable | No | `AALAN.BLAID2` |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. | Text, up to 12 characters | Not specified by FAA | Yes | `ZLA` |
| `ROUTE_PORTION_TYPE` | The Segment is identified as either a Transition or Body. | Text, up to 10 characters | Not applicable | No | `BODY` |
| `ROUTE_NAME` | The Transition or Body Name. | Text, up to 110 characters | Not applicable | No | `AALAN-BLAID` |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given STAR, the BODY_SEQ will uniquely identify the Segment. | Numeric (1,0) (precision, scale) | Not applicable | No | `1` |
| `TRANSITION_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the TRANSITION. | Text, up to 20 characters | Not applicable | Yes | `BCE.BLAID2` |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Segment. | Numeric (3,0) (precision, scale) | Not applicable | No | `10` |
| `POINT` | The FIX or NAVAID adapted on the Segment. | Text, up to 10 characters | Not specified by FAA | No | `BLAID` |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Point Types only. | Text, up to 2 characters | Not applicable | Yes | `K2` |
| `POINT_TYPE` | Specific FIX or NAVAID Type. | Text, up to 25 characters | Not applicable | No | `RP` |
| `NEXT_POINT` | The Point that directly follows the current Point on an individual segment. | Text, up to 10 characters | Not specified by FAA | Yes | `AALAN` |
| `ARPT_RWY_ASSOC` | The list of APT and/or APT/RWY associated with a given Segment. | Text, up to 200 characters | Not specified by FAA | Yes | `LAS` |

## Sources

- `STAR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `STAR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `STAR_RTE.csv` from the 2026-08-06 cycle for example values
