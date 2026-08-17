# `APT_RWY_END`

Physical runway-end coordinates, elevations, declared distances, markings, and approach information.

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
| `RWY_END_ID` | Runway End Identifier | Text, up to 3 characters | Not applicable | No | `18` |
| `TRUE_ALIGNMENT` | Runway End True Alignment (True Heading of the Runway – to the nearest Degree.) | Numeric (3,0) (precision, scale) | degrees | Yes | `172` |
| `ILS_TYPE` | Instrument Landing System (ILS) Type | Text, up to 10 characters | Not applicable | Yes | `ILS` |
| `RIGHT_HAND_TRAFFIC_PAT_FLAG` | Right Hand Traffic Pattern for Landing Aircraft | Text, up to 1 character | Not applicable | Yes | `N` |
| `RWY_MARKING_TYPE_CODE` | Runway Markings (Type) | Text, up to 4 characters | Not applicable | Yes | `BSC` |
| `RWY_MARKING_COND` | Runway Markings (Condition) | Text, up to 4 characters | Not specified by FAA | Yes | `GOOD` |
| `RWY_END_LAT_DEG` | Latitude Degrees of Physical Runway End | Numeric (2,0) (precision, scale) | degrees | Yes | `31` |
| `RWY_END_LAT_MIN` | Latitude Minutes of Physical Runway End | Numeric (2,0) (precision, scale) | minutes | Yes | `36` |
| `RWY_END_LAT_SEC` | Latitude Seconds of Physical Runway End | Numeric (6,4) (precision, scale) | seconds | Yes | `30.6998` |
| `RWY_END_LAT_HEMIS` | Latitude Hemisphere of Physical Runway End | Text, up to 1 character | Not applicable | Yes | `N` |
| `LAT_DECIMAL` | Latitude of Physical Runway End in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | Yes | `31.60852772` |
| `RWY_END_LONG_DEG` | Longitude Degrees of Physical Runway End | Numeric (3,0) (precision, scale) | degrees | Yes | `85` |
| `RWY_END_LONG_MIN` | Longitude Minutes of Physical Runway End | Numeric (2,0) (precision, scale) | minutes | Yes | `14` |
| `RWY_END_LONG_SEC` | Longitude Seconds of Physical Runway End | Numeric (6,4) (precision, scale) | seconds | Yes | `22.7315` |
| `RWY_END_LONG_HEMIS` | Longitude Hemisphere of Physical Runway End | Text, up to 1 character | Not applicable | Yes | `W` |
| `LONG_DECIMAL` | Longitude of Physical Runway End in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | Yes | `-85.23964763` |
| `RWY_END_ELEV` | Elevation (Feet MSL) at Physical Runway End | Numeric (6,1) (precision, scale) | feet MSL | Yes | `464.7` |
| `THR_CROSSING_HGT` | Threshold Crossing Height (Feet AGL) Height that the Effective Visual Glide Path Crosses Above the Runway Threshold. | Numeric (3,0) (precision, scale) | feet AGL | Yes | `44` |
| `VISUAL_GLIDE_PATH_ANGLE` | Visual Glide Path Angle (Hundredths of Degrees) | Numeric (3,2) (precision, scale) | Not applicable | Yes | `3` |
| `DISPLACED_THR_LAT_DEG` | Latitude Degrees at Displace Threshold | Numeric (2,0) (precision, scale) | degrees | Yes | `32` |
| `DISPLACED_THR_LAT_MIN` | Latitude Minutes at Displace Threshold | Numeric (2,0) (precision, scale) | minutes | Yes | `55` |
| `DISPLACED_THR_LAT_SEC` | Latitude Seconds at Displace Threshold | Numeric (6,4) (precision, scale) | seconds | Yes | `13.7182` |
| `DISPLACED_THR_LAT_HEMIS` | Latitude Hemisphere at Displace Threshold | Text, up to 1 character | Not applicable | Yes | `N` |
| `LAT_DISPLACED_THR_DECIMAL` | Latitude at Displace Threshold in Decimal Format | Numeric (10,8) (precision, scale) | Not specified by FAA | Yes | `32.92047727` |
| `DISPLACED_THR_LONG_DEG` | Longitude Degrees at Displace Threshold | Numeric (3,0) (precision, scale) | degrees | Yes | `85` |
| `DISPLACED_THR_LONG_MIN` | Longitude Minutes at Displace Threshold | Numeric (2,0) (precision, scale) | minutes | Yes | `57` |
| `DISPLACED_THR_LONG_SEC` | Longitude Seconds at Displace Threshold | Numeric (6,4) (precision, scale) | seconds | Yes | `47.6853` |
| `DISPLACED_THR_LONG_HEMIS` | Longitude Hemisphere at Displace Threshold | Text, up to 1 character | Not applicable | Yes | `W` |
| `LONG_DISPLACED_THR_DECIMAL` | Longitude at Displace Threshold in Decimal Format | Numeric (11,8) (precision, scale) | Not specified by FAA | Yes | `-85.96324591` |
| `DISPLACED_THR_ELEV` | Elevation at Displaced Threshold (Feet MSL) | Numeric (6,1) (precision, scale) | feet MSL | Yes | `674.9` |
| `DISPLACED_THR_LEN` | Displaced Threshold - Length in Feet from Runway End | Numeric (4,0) (precision, scale) | feet | Yes | `400` |
| `TDZ_ELEV` | Elevation at Touchdown Zone (Feet MSL) | Numeric (6,1) (precision, scale) | feet MSL | Yes | `468.3` |
| `VGSI_CODE` | Visual Glide Slope Indicators | Text, up to 4 characters | Not applicable | Yes | `P2L` |
| `RWY_VISUAL_RANGE_EQUIP_CODE` | Runway Visual Range Equipment (RVR) indicates location(s) at which RVR equipment is installed. Can be any one or a combination of the following three one letter codes: | Text, up to 3 characters | Not applicable | Yes | `TMR` |
| `RWY_VSBY_VALUE_EQUIP_FLAG` | Runway Visibility Value Equipment (RVV) indicates presence of RVV equipment | Text, up to 1 character | Not applicable | Yes | `Y` |
| `APCH_LGT_SYSTEM_CODE` | Approach Light System | Text, up to 8 characters | Not applicable | Yes | `MALSR` |
| `RWY_END_LGTS_FLAG` | Runway End Identifier Lights (REIL) Availability | Text, up to 1 character | Not applicable | Yes | `Y` |
| `CNTRLN_LGTS_AVBL_FLAG` | Runway Centerline Lights Availability | Text, up to 1 character | Not applicable | Yes | `Y` |
| `TDZ_LGT_AVBL_FLAG` | Runway End Touchdown Lights Availability | Text, up to 1 character | Not applicable | Yes | `N` |
| `OBSTN_TYPE` | Controlling Object Description | Text, up to 11 characters | Not applicable | Yes | `TREES` |
| `OBSTN_MRKD_CODE` | Controlling Object Marked/Lighted | Text, up to 2 characters | Not applicable | Yes | `L` |
| `FAR_PART_77_CODE` | FAA CFR Part 77 (Objects Affecting Navigable Airspace) Runway Category | Text, up to 5 characters | Not applicable | Yes | `A(V)` |
| `OBSTN_CLNC_SLOPE` | Controlling Object Clearance Slope value, expressed as a ratio of N:1, of the Clearance that is available to approaching aircraft. If the Clearance Slope is greater than 50:1, then 50 or will be entered. | Numeric (2,0) (precision, scale) | Not specified by FAA | Yes | `9` |
| `OBSTN_HGT` | Controlling Object Height Above Runway (In Feet AGL) The Object Is Above The Physical Runway End. | Numeric (5,0) (precision, scale) | feet AGL | Yes | `32` |
| `DIST_FROM_THR` | Controlling Object Distance from Runway End Distance, in feet, from the Physical Runway End to the Controlling Object. This is measured using the extended runway centerline to a point abeam the object. | Numeric (5,0) (precision, scale) | feet | Yes | `499` |
| `CNTRLN_OFFSET` | Controlling Object Centerline Offset Distance, in feet, that the Controlling Object is located away from the extended Runway Centerline as measured horizontally on a line perpendicular to the extended Runway Centerline. | Numeric (4,0) (precision, scale) | feet | Yes | `237` |
| `CNTRLN_DIR_CODE` | Controlling Object Centerline Offset Direction indicates the direction (left or right) to the object from the centerline as seen by an approaching pilot. | Text, up to 3 characters | Not applicable | Yes | `R` |
| `RWY_GRAD` | Runway End Gradient | Numeric (4,3) (precision, scale) | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `RWY_GRAD_DIRECTION` | Runway End Gradient Direction (Up Or Down) | Text, up to 4 characters | Not specified by FAA | Yes | `No non-empty value in 2026-08-06 cycle` |
| `RWY_END_PSN_SOURCE` | Runway End Position Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `RWY_END_PSN_DATE` | Runway End Position Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2025/06/17` |
| `RWY_END_ELEV_SOURCE` | Runway End Elevation Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `RWY_END_ELEV_DATE` | Runway End Elevation Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2025/06/17` |
| `DSPL_THR_PSN_SOURCE` | Displaced Threshold Position Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `RWY_END_DSPL_THR_PSN_DATE` | Displaced Threshold Position Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2010/01/19` |
| `DSPL_THR_ELEV_SOURCE` | Displaced Threshold Elevation Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `RWY_END_DSPL_THR_ELEV_DATE` | Displaced Threshold Elevation Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2010/01/19` |
| `TDZ_ELEV_SOURCE` | Source used to determine the touchdown-zone elevation. | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `RWY_END_TDZ_ELEV_DATE` | Date on which the runway-end touchdown-zone elevation was determined. | Text, up to 10 characters | Not applicable | Yes | `2025/06/17` |
| `TKOF_RUN_AVBL` | Takeoff Run Available (TORA), In Feet | Numeric (5,0) (precision, scale) | feet | Yes | `4023` |
| `TKOF_DIST_AVBL` | Takeoff Distance Available (TODA), In Feet | Numeric (5,0) (precision, scale) | feet | Yes | `4023` |
| `ACLT_STOP_DIST_AVBL` | Aclt Stop Distance Available (ASDA), In Feet | Numeric (5,0) (precision, scale) | feet | Yes | `12007` |
| `LNDG_DIST_AVBL` | Landing Distance Available (LDA), In Feet | Numeric (5,0) (precision, scale) | feet | Yes | `12007` |
| `LAHSO_ALD` | Available Landing Distance for Land and Hold Short Operations (LAHSO) | Numeric (5,0) (precision, scale) | Not specified by FAA | Yes | `8700` |
| `RWY_END_INTERSECT_LAHSO` | Identifier of the intersecting runway that defines the land-and-hold-short point. | Text, up to 7 characters | Not specified by FAA | Yes | `18/36` |
| `LAHSO_DESC` | Description of Entity Defining Hold Short Point If Not an Intersecting Runway | Text, up to 40 characters | Not specified by FAA | Yes | `RWY 01/19` |
| `LAHSO_LAT` | Latitude of LAHSO Hold Short Point (Formatted) | Text, up to 14 characters | Not specified by FAA | Yes | `33-34-06.0223N` |
| `LAT_LAHSO_DECIMAL` | Latitude of LAHSO Hold Short Point in Decimal Format | Numeric (10,8) (precision, scale) | Not specified by FAA | Yes | `33.56833952` |
| `LAHSO_LONG` | Longitude of LAHSO Hold Short Point (Formatted) | Text, up to 15 characters | Not specified by FAA | Yes | `086-44-52.9867W` |
| `LONG_LAHSO_DECIMAL` | Longitude of LAHSO Hold Short Point in Decimal Format | Numeric (11,8) (precision, scale) | Not specified by FAA | Yes | `-86.74805186` |
| `LAHSO_PSN_SOURCE` | LAHSO Hold Short Point Lat/Long Source | Text, up to 16 characters | Not specified by FAA | Yes | `FAA-EST` |
| `RWY_END_LAHSO_PSN_DATE` | Hold Short Point Lat/Long Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2007/07/11` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_RWY_END.csv` from the 2026-08-06 cycle for example values
