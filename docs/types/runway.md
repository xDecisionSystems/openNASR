# Runway

Runway data is attached to an `AirportRecord`. `RunwayRecord` describes the
complete landing surface; `RunwayEndRecord` describes one physical end.

## FAA source tables

| Table | Content |
| --- | --- |
| `APT_RWY` | Runway identifier, dimensions, surface, and status |
| `APT_RWY_END` | End identifier, threshold position, elevation, and declared distances |

## Access

```python
airport = nasr.airports.get("ATL")

for runway in airport.runways:
    print(runway["RWY_ID"])

for runway_end in airport.runway_ends:
    print(runway_end["RWY_END_ID"])
```

The legacy `RWY` adapters remain documented for existing callers, but new code
should use the lossless record tuples on `AirportRecord`.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} RunwayRecord raw fields — APT_RWY (25)
`RunwayRecord` preserves one complete `APT_RWY` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `RWY_ID` | Runway Identification |
| `RWY_LEN` | Physical Runway Length (Nearest Foot) |
| `RWY_WIDTH` | Physical Runway Width (Nearest Foot) |
| `SURFACE_TYPE_CODE` | Runway Surface Type (The value will usually be one of those described below or a combination of two types when the runway is composed of distinct sections.) |
| `COND` | Runway Surface Condition |
| `TREATMENT_CODE` | Runway Surface Treatment |
| `PCN` | Pavement Classification Number (PCN) See FAA Advisory Circular 150/5335-5 for Code Definitions and PCN Determination Formula. |
| `PAVEMENT_TYPE_CODE` | Pavement Type |
| `SUBGRADE_STRENGTH_CODE` | Subgrade Strength (Letters A-F) |
| `TIRE_PRES_CODE` | Tire Pressure Code (Letters W-Z) |
| `DTRM_METHOD_CODE` | Determination Method |
| `RWY_LGT_CODE` | Runway Lights Edge Intensity |
| `RWY_LEN_SOURCE` | Runway Length Source |
| `LENGTH_SOURCE_DATE` | Runway Length Source Date (YYYY/MM/DD) |
| `GROSS_WT_SW` | Runway Weight-Bearing Capacity for Single Wheel type Landing Gear |
| `GROSS_WT_DW` | Runway Weight-Bearing Capacity for Dual Wheel type Landing Gear |
| `GROSS_WT_DTW` | Runway Weight-Bearing Capacity for Two Dual Wheels in tandem type Landing Gear |
| `GROSS_WT_DDTW` | Runway Weight-Bearing Capacity for Two Dual Wheels in tandem/two dual wheels in double tandem body gear type Landing Gear |

[Complete `APT_RWY` column reference](../csv-tables/apt-rwy.md)
```

```{faa-dropdown} RunwayEndRecord raw fields — APT_RWY_END (80)
`RunwayEndRecord` preserves one complete `APT_RWY_END` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `RWY_ID` | Runway Identification |
| `RWY_END_ID` | Runway End Identifier |
| `TRUE_ALIGNMENT` | Runway End True Alignment (True Heading of the Runway – to the nearest Degree.) |
| `ILS_TYPE` | Instrument Landing System (ILS) Type |
| `RIGHT_HAND_TRAFFIC_PAT_FLAG` | Right Hand Traffic Pattern for Landing Aircraft |
| `RWY_MARKING_TYPE_CODE` | Runway Markings (Type) |
| `RWY_MARKING_COND` | Runway Markings (Condition) |
| `RWY_END_LAT_DEG` | Latitude Degrees of Physical Runway End |
| `RWY_END_LAT_MIN` | Latitude Minutes of Physical Runway End |
| `RWY_END_LAT_SEC` | Latitude Seconds of Physical Runway End |
| `RWY_END_LAT_HEMIS` | Latitude Hemisphere of Physical Runway End |
| `LAT_DECIMAL` | Latitude of Physical Runway End in Decimal Format |
| `RWY_END_LONG_DEG` | Longitude Degrees of Physical Runway End |
| `RWY_END_LONG_MIN` | Longitude Minutes of Physical Runway End |
| `RWY_END_LONG_SEC` | Longitude Seconds of Physical Runway End |
| `RWY_END_LONG_HEMIS` | Longitude Hemisphere of Physical Runway End |
| `LONG_DECIMAL` | Longitude of Physical Runway End in Decimal Format |
| `RWY_END_ELEV` | Elevation (Feet MSL) at Physical Runway End |
| `THR_CROSSING_HGT` | Threshold Crossing Height (Feet AGL) Height that the Effective Visual Glide Path Crosses Above the Runway Threshold. |
| `VISUAL_GLIDE_PATH_ANGLE` | Visual Glide Path Angle (Hundredths of Degrees) |
| `DISPLACED_THR_LAT_DEG` | Latitude Degrees at Displace Threshold |
| `DISPLACED_THR_LAT_MIN` | Latitude Minutes at Displace Threshold |
| `DISPLACED_THR_LAT_SEC` | Latitude Seconds at Displace Threshold |
| `DISPLACED_THR_LAT_HEMIS` | Latitude Hemisphere at Displace Threshold |
| `LAT_DISPLACED_THR_DECIMAL` | Latitude at Displace Threshold in Decimal Format |
| `DISPLACED_THR_LONG_DEG` | Longitude Degrees at Displace Threshold |
| `DISPLACED_THR_LONG_MIN` | Longitude Minutes at Displace Threshold |
| `DISPLACED_THR_LONG_SEC` | Longitude Seconds at Displace Threshold |
| `DISPLACED_THR_LONG_HEMIS` | Longitude Hemisphere at Displace Threshold |
| `LONG_DISPLACED_THR_DECIMAL` | Longitude at Displace Threshold in Decimal Format |
| `DISPLACED_THR_ELEV` | Elevation at Displaced Threshold (Feet MSL) |
| `DISPLACED_THR_LEN` | Displaced Threshold - Length in Feet from Runway End |
| `TDZ_ELEV` | Elevation at Touchdown Zone (Feet MSL) |
| `VGSI_CODE` | Visual Glide Slope Indicators |
| `RWY_VISUAL_RANGE_EQUIP_CODE` | Runway Visual Range Equipment (RVR) indicates location(s) at which RVR equipment is installed. Can be any one or a combination of the following three one letter codes: |
| `RWY_VSBY_VALUE_EQUIP_FLAG` | Runway Visibility Value Equipment (RVV) indicates presence of RVV equipment |
| `APCH_LGT_SYSTEM_CODE` | Approach Light System |
| `RWY_END_LGTS_FLAG` | Runway End Identifier Lights (REIL) Availability |
| `CNTRLN_LGTS_AVBL_FLAG` | Runway Centerline Lights Availability |
| `TDZ_LGT_AVBL_FLAG` | Runway End Touchdown Lights Availability |
| `OBSTN_TYPE` | Controlling Object Description |
| `OBSTN_MRKD_CODE` | Controlling Object Marked/Lighted |
| `FAR_PART_77_CODE` | FAA CFR Part 77 (Objects Affecting Navigable Airspace) Runway Category |
| `OBSTN_CLNC_SLOPE` | Controlling Object Clearance Slope value, expressed as a ratio of N:1, of the Clearance that is available to approaching aircraft. If the Clearance Slope is greater than 50:1, then 50 or will be entered. |
| `OBSTN_HGT` | Controlling Object Height Above Runway (In Feet AGL) The Object Is Above The Physical Runway End. |
| `DIST_FROM_THR` | Controlling Object Distance from Runway End Distance, in feet, from the Physical Runway End to the Controlling Object. This is measured using the extended runway centerline to a point abeam the object. |
| `CNTRLN_OFFSET` | Controlling Object Centerline Offset Distance, in feet, that the Controlling Object is located away from the extended Runway Centerline as measured horizontally on a line perpendicular to the extended Runway Centerline. |
| `CNTRLN_DIR_CODE` | Controlling Object Centerline Offset Direction indicates the direction (left or right) to the object from the centerline as seen by an approaching pilot. |
| `RWY_GRAD` | Runway End Gradient |
| `RWY_GRAD_DIRECTION` | Runway End Gradient Direction (Up Or Down) |
| `RWY_END_PSN_SOURCE` | Runway End Position Source |
| `RWY_END_PSN_DATE` | Runway End Position Source Date (YYYY/MM/DD) |
| `RWY_END_ELEV_SOURCE` | Runway End Elevation Source |
| `RWY_END_ELEV_DATE` | Runway End Elevation Source Date (YYYY/MM/DD) |
| `DSPL_THR_PSN_SOURCE` | Displaced Threshold Position Source |
| `RWY_END_DSPL_THR_PSN_DATE` | Displaced Threshold Position Source Date (YYYY/MM/DD) |
| `DSPL_THR_ELEV_SOURCE` | Displaced Threshold Elevation Source |
| `RWY_END_DSPL_THR_ELEV_DATE` | Displaced Threshold Elevation Source Date (YYYY/MM/DD) |
| `TDZ_ELEV_SOURCE` | Source used to determine the touchdown-zone elevation. |
| `RWY_END_TDZ_ELEV_DATE` | Date on which the runway-end touchdown-zone elevation was determined. |
| `TKOF_RUN_AVBL` | Takeoff Run Available (TORA), In Feet |
| `TKOF_DIST_AVBL` | Takeoff Distance Available (TODA), In Feet |
| `ACLT_STOP_DIST_AVBL` | Aclt Stop Distance Available (ASDA), In Feet |
| `LNDG_DIST_AVBL` | Landing Distance Available (LDA), In Feet |
| `LAHSO_ALD` | Available Landing Distance for Land and Hold Short Operations (LAHSO) |
| `RWY_END_INTERSECT_LAHSO` | Identifier of the intersecting runway that defines the land-and-hold-short point. |
| `LAHSO_DESC` | Description of Entity Defining Hold Short Point If Not an Intersecting Runway |
| `LAHSO_LAT` | Latitude of LAHSO Hold Short Point (Formatted) |
| `LAT_LAHSO_DECIMAL` | Latitude of LAHSO Hold Short Point in Decimal Format |
| `LAHSO_LONG` | Longitude of LAHSO Hold Short Point (Formatted) |
| `LONG_LAHSO_DECIMAL` | Longitude of LAHSO Hold Short Point in Decimal Format |
| `LAHSO_PSN_SOURCE` | LAHSO Hold Short Point Lat/Long Source |
| `RWY_END_LAHSO_PSN_DATE` | Hold Short Point Lat/Long Source Date (YYYY/MM/DD) |

[Complete `APT_RWY_END` column reference](../csv-tables/apt-rwy-end.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.rwy.RunwayRecord
.. autoclass:: openNASR.rwy.RunwayEndRecord
.. autoclass:: openNASR.rwy.RWY
.. autoclass:: openNASR.rwy.RWYitem
.. autoclass:: openNASR.rwy.RWYEnd
.. autoclass:: openNASR.rwy.RWYEnditem
```

