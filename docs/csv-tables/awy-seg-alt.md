# `AWY_SEG_ALT`

Ordered airway segments, navigation points, courses, changeover points, and altitude constraints.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/07/09` |
| `REGULATORY` | Identifies Airways published under 14 CFR (Code of Federal Regulation) Part-71 and Part- 95 – Y/N. | Text, up to 1 character | Not specified by FAA | No | `N` |
| `AWY_LOCATION` | Airway Type which identifies the General Location of the Airway. | Text, up to 1 character | Not specified by FAA | No | `C` |
| `AWY_ID` | Airway Identifier. | Text, up to 12 characters | Not applicable | No | `A216` |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Airway. | Numeric (3,0) (precision, scale) | Not applicable | No | `10` |
| `FROM_POINT` | NAVAID Facility Identifier, FIX Name or Border crossing. A Unique system generated number is added to each Border crossing Segment Value. This number while unique is not necessarily sequential. | Text, up to 30 characters | Not specified by FAA | No | `MONPI` |
| `FROM_PT_TYPE` | NAVAID Facility or FIX Type. | Text, up to 25 characters | Not applicable | Yes | `WP` |
| `NAV_NAME` | NAVAID Facility Name | Text, up to 30 characters | Not applicable | Yes | `NIMITZ` |
| `NAV_CITY` | The NAVIAD Facility City which is part of the key for all NAV_*.csv files. | Text, up to 40 characters | Not applicable | Yes | `AGANA` |
| `ARTCC` | Identifier of Low ARTCC Altitude Boundary That the FROM_POINT FIX/NAVAID Falls Within. | Text, up to 4 characters | Not specified by FAA | Yes | `ZAK` |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Point Types only. | Text, up to 2 characters | Not applicable | Yes | `P` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `OP` |
| `COUNTRY_CODE` | Country Post Office Code | Text, up to 2 characters | Not applicable | Yes | `US` |
| `TO_POINT` | The To Point that directly follows the current From Point on an individual segment. | Text, up to 30 characters | Not specified by FAA | Yes | `OATSS` |
| `MAG_COURSE` | Segment Magnetic Course | Numeric (5,2) (precision, scale) | Not specified by FAA | Yes | `163.39` |
| `OPP_MAG_COURSE` | Segment Magnetic Course - Opposite Direction | Numeric (5,2) (precision, scale) | Not specified by FAA | Yes | `342.23` |
| `MAG_COURSE_DIST` | Distance to Next Point in Segment in Nautical Miles. | Numeric (5,2) (precision, scale) | nautical miles | Yes | `269.2` |
| `CHGOVR_PT` | NAVAID Changeover Point Facility Identifier | Text, up to 4 characters | Not specified by FAA | Yes | `RWO` |
| `CHGOVR_PT_NAME` | NAVAID Changeover Point Facility Name | Text, up to 30 characters | Not applicable | Yes | `WOODY ISLAND` |
| `CHGOVR_PT_DIST` | This Field Contains The Distance In Nautical Miles Of The Changeover Point Between This NAVAID Facility And The Next NAVAID Facility When The Changeover Point Is More Than One Mile From Half-Way Point. | Numeric (3,0) (precision, scale) | nautical miles | Yes | `90` |
| `AWY_SEG_GAP_FLAG` | Airway Gap Flag Indicator for when Airway Discontinued – Y/N. | Text, up to 1 character | Not applicable | No | `N` |
| `SIGNAL_GAP_FLAG` | Gap in Signal Coverage Indicator for when Mea established With a Gap in Navigation Signal Coverage - Y/N. | Text, up to 1 character | Not applicable | No | `N` |
| `DOGLEG` | A Turn Point Not At A NAVAID – Y/N. Note: GPS RNAV Routes [Q, T, TK] will have Dogleg=Y at First Point, End Point, And All Turn Points in between. | Text, up to 1 character | Not specified by FAA | No | `N` |
| `NEXT_MEA_PT` | The To MEA_PT that directly follows the From MEA_PT for an individual Altitude record. | Text, up to 30 characters | Not specified by FAA | No | `OATSS` |
| `MIN_ENROUTE_ALT` | Point To Point Minimum Enroute Altitude (MEA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `18000` |
| `MIN_ENROUTE_ALT_DIR` | Point To Point Minimum Enroute Direction (MEA) | Text, up to 7 characters | Not specified by FAA | Yes | `NE BND` |
| `MIN_ENROUTE_ALT_OPPOSITE` | Point To Point Minimum Enroute Altitude (MEA-Opposite Direction) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `5000` |
| `MIN_ENROUTE_ALT_OPPOSITE_DIR` | Point To Point Minimum Enroute Direction (MEA-Opposite Direction) | Text, up to 7 characters | Not specified by FAA | Yes | `SW BND` |
| `GPS_MIN_ENROUTE_ALT` | Point To Point GNSS Minimum Enroute Altitude (Global Navigation Satellite System MEA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `5000` |
| `GPS_MIN_ENROUTE_ALT_DIR` | Point To Point GNSS Minimum Enroute Direction (Global Navigation Satellite System MEA) | Text, up to 7 characters | Not specified by FAA | Yes | `SW BND` |
| `GPS_MIN_ENROUTE_ALT_OPPOSITE` | Point To Point GNSS Minimum Enroute Altitude (Global Navigation Satellite System MEA-Opposite Direction) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `3500` |
| `GPS_MEA_OPPOSITE_DIR` | Point To Point GNSS Minimum Enroute Direction (Global Navigation Satellite System MEA-Opposite Direction) | Text, up to 7 characters | Not specified by FAA | Yes | `NE BND` |
| `DD_IRU_MEA` | Point To Point DME/DME/IRU Minimum Enroute Altitude (MEA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `24000` |
| `DD_IRU_MEA_DIR` | Point To Point DME/DME/IRU Minimum Enroute Direction (MEA) | Text, up to 7 characters | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `DD_I_MEA_OPPOSITE` | Point To Point DME/DME/IRU Minimum Enroute Altitude (MEA- Opposite Direction) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `DD_I_MEA_OPPOSITE_DIR` | Point To Point DME/DME/IRU Minimum Enroute Direction (MEA- Opposite Direction) | Text, up to 7 characters | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `MIN_OBSTN_CLNC_ALT` | Point To Point Minimum Obstruction Clearance Altitude (MOCA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `1300` |
| `MIN_CROSS_ALT` | Minimum Crossing Altitude (MCA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `25000` |
| `MIN_CROSS_ALT_DIR` | Minimum Crossing Direction (MCA) | Text, up to 7 characters | Not specified by FAA | Yes | `W BND` |
| `MIN_CROSS_ALT_NAV_PT` | Minimum Crossing Altitude (MCA) Point | Text, up to 30 characters | Not specified by FAA | Yes | `AUGER` |
| `MIN_CROSS_ALT_OPPOSITE` | Minimum Crossing Altitude (MCA- Opposite Direction) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `2600` |
| `MIN_CROSS_ALT_OPPOSITE_DIR` | Minimum Crossing Direction (MCA- Opposite Direction) | Text, up to 7 characters | Not specified by FAA | Yes | `N BND` |
| `MIN_RECEP_ALT` | FIX Minimum Reception Altitude (MRA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `8000` |
| `MAX_AUTH_ALT` | Point To Point Maximum Authorized Altitude (MAA) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `60000` |
| `MEA_GAP` | Identifies whether a given Airway Segment is Unusable – “U” or contains No MEA information – “N”. | Text, up to 1 character | Not specified by FAA | Yes | `N` |
| `REQD_NAV_PERFORMANCE` | Required Navigation Performance (RNP) value. | Numeric (4,2) (precision, scale) | Not specified by FAA | Yes | `1` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 1500 characters | Not applicable | Yes | `VIRGINIA KEY R-058 UNUSABLE JANUS TO VALLY` |

## Sources

- `AWY_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `AWY DATA LAYOUT.pdf` for FAA field definitions and stated units
- `AWY_SEG_ALT.csv` from the 2026-08-06 cycle for example values
