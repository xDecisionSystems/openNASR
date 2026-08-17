# `CDR`

Coded departure route identifiers and their published route strings.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `RCode` | Each CDR is uniquely identified by an eight-character alphanumeric code. The Route Code is a concatenation of the Origin, Destination and an alphanumeric route identifier. | Text, up to 8 characters | Not applicable | No | `ABECLTGV` |
| `Orig` | The CDR Point of Origin is a 3 or 4 character departure airport designator. | Text, up to 4 characters | Not specified by FAA | No | `KABE` |
| `Dest` | The CDR Point of Destination is a 3 or 4 character arrival airport designator. | Text, up to 4 characters | Not specified by FAA | No | `KCLT` |
| `DepFix` | The Departure Fix associated with a given CDR. | Text, up to 6 characters | Not specified by FAA | No | `LRP` |
| `Route String` | The preplanned route of flight associated with a given CDR. | Text, up to 200 characters | Not specified by FAA | No | `KABE LRP EMI GVE AIROW CHSLY8 KCLT` |
| `DCNTR` | Departure ARTCC associated with a given CDR. | Text, up to 3 characters | Not specified by FAA | No | `ZNY` |
| `ACNTR` | Arrival ARTCC associated with a given CDR. | Text, up to 3 characters | Not specified by FAA | No | `ZTL` |
| `TCNTRs` | A list of all Traversed ARTCCs for a given CDR. | Text, up to 100 characters | Not specified by FAA | Yes | `ZDC ZNY ZTL` |
| `CoordReq` | Y/N indicator as to whether Coordination is required. | Text, up to 1 character | Not specified by FAA | No | `N` |
| `Play` | The Playbook Play name for a given CDR. | Text, up to 25 characters | Not specified by FAA | Yes | `ATL NO CHPPR GLAVN` |
| `NavEqp` | Navigation Equipment Designator. | Numeric (1,0) (precision, scale) | Not specified by FAA | No | `1` |
| `Length` | Length of CDR in Nautical Miles | Numeric (5,0) (precision, scale) | nautical miles | Yes | `421` |

## Sources

- `CDR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `CDR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `CDR.csv` from the 2026-08-06 cycle for example values
