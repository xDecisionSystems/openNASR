# `MAA_SHP`

Ordered geometry points defining a Miscellaneous Activity Area.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. | Text, up to 6 characters | Not applicable | No | `AAL001` |
| `POINT_SEQ` | Unique Sequence number for MAA Polygon Coordinates. | Numeric (2,0) (precision, scale) | Not applicable | No | `1` |
| `LATITUDE` | MAA Polygon Coordinate Latitude (Formatted) | Text, up to 14 characters | Not specified by FAA | No | `33-54-12.8500N` |
| `LONGITUDE` | MAA Polygon Coordinate Longitude (Formatted) | Text, up to 15 characters | Not specified by FAA | No | `087-19-53.7600W` |

## Sources

- `MAA_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `MAA DATA LAYOUT.pdf` for FAA field definitions and stated units
- `MAA_SHP.csv` from the 2026-08-06 cycle for example values
