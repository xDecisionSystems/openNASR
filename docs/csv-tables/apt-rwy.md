# `APT_RWY`

Airport runway identity, dimensions, surface, lighting, and operational information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00103.` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `0J0` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `ABBEVILLE` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `RWY_ID` | Runway Identification | Text, up to 7 characters | Not applicable | No | `18/36` |
| `RWY_LEN` | Physical Runway Length (Nearest Foot) | Numeric (5,0) (precision, scale) | feet | No | `5000` |
| `RWY_WIDTH` | Physical Runway Width (Nearest Foot) | Numeric (4,0) (precision, scale) | Not applicable | No | `75` |
| `SURFACE_TYPE_CODE` | Runway Surface Type (The value will usually be one of those described below or a combination of two types when the runway is composed of distinct sections.) | Text, up to 10 characters | Not applicable | Yes | `ASPH` |
| `COND` | Runway Surface Condition | Text, up to 9 characters | Not specified by FAA | Yes | `FAIR` |
| `TREATMENT_CODE` | Runway Surface Treatment | Text, up to 4 characters | Not applicable | Yes | `AFSC` |
| `PCN` | Pavement Classification Number (PCN) See FAA Advisory Circular 150/5335-5 for Code Definitions and PCN Determination Formula. | Numeric (3,0) (precision, scale) | Not specified by FAA | Yes | `10` |
| `PAVEMENT_TYPE_CODE` | Pavement Type | Text, up to 1 character | Not applicable | Yes | `F` |
| `SUBGRADE_STRENGTH_CODE` | Subgrade Strength (Letters A-F) | Text, up to 1 character | Not applicable | Yes | `C` |
| `TIRE_PRES_CODE` | Tire Pressure Code (Letters W-Z) | Text, up to 1 character | Not applicable | Yes | `X` |
| `DTRM_METHOD_CODE` | Determination Method | Text, up to 1 character | Not applicable | Yes | `T` |
| `RWY_LGT_CODE` | Runway Lights Edge Intensity | Text, up to 4 characters | Not applicable | Yes | `MED` |
| `RWY_LEN_SOURCE` | Runway Length Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `LENGTH_SOURCE_DATE` | Runway Length Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2025/06/17` |
| `GROSS_WT_SW` | Runway Weight-Bearing Capacity for Single Wheel type Landing Gear | Numeric (5,1) (precision, scale) | Not specified by FAA | Yes | `16` |
| `GROSS_WT_DW` | Runway Weight-Bearing Capacity for Dual Wheel type Landing Gear | Numeric (5,1) (precision, scale) | Not specified by FAA | Yes | `90` |
| `GROSS_WT_DTW` | Runway Weight-Bearing Capacity for Two Dual Wheels in tandem type Landing Gear | Numeric (5,1) (precision, scale) | Not specified by FAA | Yes | `130` |
| `GROSS_WT_DDTW` | Runway Weight-Bearing Capacity for Two Dual Wheels in tandem/two dual wheels in double tandem body gear type Landing Gear | Numeric (5,1) (precision, scale) | Not specified by FAA | Yes | `992` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_RWY.csv` from the 2026-08-06 cycle for example values
