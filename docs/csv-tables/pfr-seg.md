# `PFR_SEG`

Ordered segments and navigation elements for a preferred route.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `ORIGIN_ID` | Origin Facility Location Identifier (Depending on NAR Type and Direction, Origin ID Is either Coastal Fix or Inland NAV Facility or Fix) | Text, up to 5 characters | Not applicable | No | `ABE` |
| `DSTN_ID` | Destination Facility Location Identifier (Depending on NAR Type and Direction, Destination ID Is either Airport, Coastal Fix or Inland NAV Facility or Fix) | Text, up to 5 characters | Not applicable | No | `ACY` |
| `PFR_TYPE_CODE` | Type Code of Preferred Route Description. | Text, up to 3 characters | Not applicable | No | `TEC` |
| `ROUTE_NO` | Route Identifier Sequence Number (1-99) | Numeric (2,0) (precision, scale) | Not specified by FAA | No | `1` |
| `SEGMENT_SEQ` | A sequencing number in multiples of five for each SEG_VALUE. Segment Values are in order adapted for each Preferred Route. | Numeric (3,0) (precision, scale) | Not applicable | No | `5` |
| `SEG_VALUE` | The Segment ID Value for each Element of the Route String from PFR_BASE. | Text, up to 30 characters | Not specified by FAA | No | `FJC` |
| `SEG_TYPE` | The Segment Type of the Segment ID Value. | Text, up to 6 characters | Not applicable | No | `NAVAID` |
| `STATE_CODE` | This is the two letter state ID of the Segment Values that are within the US and are Type FIX, FRD, NAVAID or RADIAL. Segment Values outside the US or Types AIRWAY, DP or STAR are NULL. | Text, up to 2 characters | Not applicable | Yes | `PA` |
| `COUNTRY_CODE` | Country Code for Types FIX, FRD, NAVAID or RADIAL. Segment Value Types AIRWAY, DP or STAR are NULL. | Text, up to 2 characters | Not applicable | Yes | `US` |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Segment Types only. | Text, up to 2 characters | Not applicable | Yes | `K6` |
| `NAV_TYPE` | Specific NAVAID Type for Segment Value Types NAVAID, RADIAL or FRD. | Text, up to 25 characters | Not applicable | Yes | `VORTAC` |
| `NEXT_SEG` | The Segment ID Value of the Element that directly follows the current Segment Value. | Text, up to 30 characters | Not specified by FAA | Yes | `ARD` |

## Sources

- `PFR_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `PFR DATA LAYOUT.pdf` for FAA field definitions and stated units
- `PFR_SEG.csv` from the 2026-08-06 cycle for example values
