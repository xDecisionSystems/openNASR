# `STAR_BASE`

Standard Terminal Arrival Route identity, controlling ARTCC, and published metadata.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `ARRIVAL_NAME` | STAR Name. Name Assigned to the Standard Terminal Arrival. | Text, up to 30 characters | Not applicable | No | `BLAID` |
| `AMENDMENT_NO` | Amendment Number (spelled out) of the STAR that will be Active on the Effective Date. | Text, up to 5 characters | Not specified by FAA | No | `TWO` |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. | Text, up to 12 characters | Not specified by FAA | Yes | `ZLA` |
| `STAR_AMEND_EFF_DATE` | The First Effective Date for which the STAR Amendment became Active. | Text, up to 10 characters | Not applicable | No | `2024/01/25` |
| `RNAV_FLAG` | Y/N Flag determines whether a STAR is RNAV required. | Text, up to 1 character | Not applicable | No | `N` |
| `STAR_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the STAR. EX. GLAND.BLUMS5 | Text, up to 12 characters | Not applicable | No | `AALAN.BLAID2` |
| `SERVED_ARPT` | List of Airports Served by the STAR. | Text, up to 200 characters | Not specified by FAA | No | `LAS` |

## Sources

- `STAR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `STAR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `STAR_BASE.csv` from the 2026-08-06 cycle for example values
