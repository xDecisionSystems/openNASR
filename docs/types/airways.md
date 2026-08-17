# Airways

An `Airway` combines one airway identity record with FAA-sequence-ordered
segments and their altitude constraints. Segment relationships may resolve to
a fix or navaid through the complete published key.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `AWY_BASE` | Airway identity |
| `AWY_SEG_ALT` | Ordered points and altitude constraints |

The composite key is (`REGULATORY`, `AWY_LOCATION`, `AWY_ID`).

```python
key = (regulatory, airway_location, airway_id)
airway = nasr.airways.get(key)

airway.record
airway.segments

# Plot only this airway's uniquely resolved segments.
figure, axes = airway.plot(nasr)
```

Each segment exposes its point sequence, minimum enroute altitude, maximum
authorized altitude, and resolved navigation record when available.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} AirwayRecord raw fields — AWY_BASE (8)
`AirwayRecord` preserves one complete `AWY_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `REGULATORY` | Identifies Airways published under 14 CFR (Code of Federal Regulation) Part-71 and Part- 95 – Y/N. |
| `AWY_DESIGNATION` | Airway Designation. |
| `AWY_LOCATION` | Airway Type which identifies the General Location of the Airway. |
| `AWY_ID` | Airway Identifier. |
| `UPDATE_DATE` | The Last Date for which the AIRWAY Data amended. |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) |
| `AIRWAY_STRING` | List of FIX and NAVAID that make up the AIRWAY in order adapted. |

[Complete `AWY_BASE` column reference](../csv-tables/awy-base.md)
```

```{faa-dropdown} AirwaySegmentRecord raw fields — AWY_SEG_ALT (47)
`AirwaySegmentRecord` preserves one complete `AWY_SEG_ALT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `REGULATORY` | Identifies Airways published under 14 CFR (Code of Federal Regulation) Part-71 and Part- 95 – Y/N. |
| `AWY_LOCATION` | Airway Type which identifies the General Location of the Airway. |
| `AWY_ID` | Airway Identifier. |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Airway. |
| `FROM_POINT` | NAVAID Facility Identifier, FIX Name or Border crossing. A Unique system generated number is added to each Border crossing Segment Value. This number while unique is not necessarily sequential. |
| `FROM_PT_TYPE` | NAVAID Facility or FIX Type. |
| `NAV_NAME` | NAVAID Facility Name |
| `NAV_CITY` | The NAVIAD Facility City which is part of the key for all NAV_*.csv files. |
| `ARTCC` | Identifier of Low ARTCC Altitude Boundary That the FROM_POINT FIX/NAVAID Falls Within. |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Point Types only. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `TO_POINT` | The To Point that directly follows the current From Point on an individual segment. |
| `MAG_COURSE` | Segment Magnetic Course |
| `OPP_MAG_COURSE` | Segment Magnetic Course - Opposite Direction |
| `MAG_COURSE_DIST` | Distance to Next Point in Segment in Nautical Miles. |
| `CHGOVR_PT` | NAVAID Changeover Point Facility Identifier |
| `CHGOVR_PT_NAME` | NAVAID Changeover Point Facility Name |
| `CHGOVR_PT_DIST` | This Field Contains The Distance In Nautical Miles Of The Changeover Point Between This NAVAID Facility And The Next NAVAID Facility When The Changeover Point Is More Than One Mile From Half-Way Point. |
| `AWY_SEG_GAP_FLAG` | Airway Gap Flag Indicator for when Airway Discontinued – Y/N. |
| `SIGNAL_GAP_FLAG` | Gap in Signal Coverage Indicator for when Mea established With a Gap in Navigation Signal Coverage - Y/N. |
| `DOGLEG` | A Turn Point Not At A NAVAID – Y/N. Note: GPS RNAV Routes [Q, T, TK] will have Dogleg=Y at First Point, End Point, And All Turn Points in between. |
| `NEXT_MEA_PT` | The To MEA_PT that directly follows the From MEA_PT for an individual Altitude record. |
| `MIN_ENROUTE_ALT` | Point To Point Minimum Enroute Altitude (MEA) |
| `MIN_ENROUTE_ALT_DIR` | Point To Point Minimum Enroute Direction (MEA) |
| `MIN_ENROUTE_ALT_OPPOSITE` | Point To Point Minimum Enroute Altitude (MEA-Opposite Direction) |
| `MIN_ENROUTE_ALT_OPPOSITE_DIR` | Point To Point Minimum Enroute Direction (MEA-Opposite Direction) |
| `GPS_MIN_ENROUTE_ALT` | Point To Point GNSS Minimum Enroute Altitude (Global Navigation Satellite System MEA) |
| `GPS_MIN_ENROUTE_ALT_DIR` | Point To Point GNSS Minimum Enroute Direction (Global Navigation Satellite System MEA) |
| `GPS_MIN_ENROUTE_ALT_OPPOSITE` | Point To Point GNSS Minimum Enroute Altitude (Global Navigation Satellite System MEA-Opposite Direction) |
| `GPS_MEA_OPPOSITE_DIR` | Point To Point GNSS Minimum Enroute Direction (Global Navigation Satellite System MEA-Opposite Direction) |
| `DD_IRU_MEA` | Point To Point DME/DME/IRU Minimum Enroute Altitude (MEA) |
| `DD_IRU_MEA_DIR` | Point To Point DME/DME/IRU Minimum Enroute Direction (MEA) |
| `DD_I_MEA_OPPOSITE` | Point To Point DME/DME/IRU Minimum Enroute Altitude (MEA- Opposite Direction) |
| `DD_I_MEA_OPPOSITE_DIR` | Point To Point DME/DME/IRU Minimum Enroute Direction (MEA- Opposite Direction) |
| `MIN_OBSTN_CLNC_ALT` | Point To Point Minimum Obstruction Clearance Altitude (MOCA) |
| `MIN_CROSS_ALT` | Minimum Crossing Altitude (MCA) |
| `MIN_CROSS_ALT_DIR` | Minimum Crossing Direction (MCA) |
| `MIN_CROSS_ALT_NAV_PT` | Minimum Crossing Altitude (MCA) Point |
| `MIN_CROSS_ALT_OPPOSITE` | Minimum Crossing Altitude (MCA- Opposite Direction) |
| `MIN_CROSS_ALT_OPPOSITE_DIR` | Minimum Crossing Direction (MCA- Opposite Direction) |
| `MIN_RECEP_ALT` | FIX Minimum Reception Altitude (MRA) |
| `MAX_AUTH_ALT` | Point To Point Maximum Authorized Altitude (MAA) |
| `MEA_GAP` | Identifies whether a given Airway Segment is Unusable – “U” or contains No MEA information – “N”. |
| `REQD_NAV_PERFORMANCE` | Required Navigation Performance (RNP) value. |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) |

[Complete `AWY_SEG_ALT` column reference](../csv-tables/awy-seg-alt.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airway.Airway
.. autoclass:: openNASR.airway.AirwayRecord
.. autoclass:: openNASR.airway.AirwaySegmentRecord
.. autoclass:: openNASR.airway.AirwayRepository
```
