# `STAR_APT`

Airports and runway ends associated with a Standard Terminal Arrival Route.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `STAR_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the STAR. EX. GLAND.BLUMS5 | Text, up to 12 characters | Not applicable | No | `AALAN.BLAID2` |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. | Text, up to 12 characters | Not specified by FAA | Yes | `ZLA` |
| `BODY_NAME` | The Name of the Body for which the Airport/Runway End are associated. The Body Name is the first and last Fix of the Segment. | Text, up to 110 characters | Not applicable | No | `AALAN-BLAID` |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given STAR, the BODY_SEQ will uniquely identify the Segment. | Numeric (1,0) (precision, scale) | Not applicable | No | `1` |
| `ARPT_ID` | The associated Airport Identifier. | Text, up to 4 characters | Not applicable | No | `LAS` |
| `RWY_END_ID` | The Runway End Identifier if applicable. | Text, up to 3 characters | Not applicable | Yes | `ALL` |

## Sources

- `STAR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `STAR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `STAR_APT.csv` from the 2026-08-06 cycle for example values
