# Navaid

`NavaidRecord` preserves one `NAV_BASE` row and exposes common navigation-aid
identity, type, frequency, coordinate, and ARTCC fields.

## Lookup

The primary identifier is `NAV_ID`. State, country, ARTCC, and navaid type can
disambiguate identifiers that occur more than once.

```python
navaid = nasr.navaids.get("DCA", state="VA", nav_type="VOR/DME")

navaid.identifier
navaid.frequency
navaid.latitude
navaid.longitude
```

`NAVAID` is retained as the legacy adapter.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} NavaidRecord raw fields — NAV_BASE (72)
`NavaidRecord` preserves one complete `NAV_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `NAV_ID` | NAVAID Facility Identifier. |
| `NAV_TYPE` | NAVAID Facility Type. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `CITY` | NAVAID Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code NAVAID Located |
| `NAV_STATUS` | Navigation Aid Status |
| `NAME` | Name of NAVAID |
| `STATE_NAME` | Associated State Name |
| `REGION_CODE` | FAA Region responsible for NAVAID (code) |
| `COUNTRY_NAME` | Country Name NAVAID Located |
| `FAN_MARKER` | Name of FAN MARKER |
| `OWNER` | A Concatenation of the NAVAID OWNER CODE - NAVAID OWNER NAME |
| `OPERATOR` | A Concatenation of the NAVAID OPERATOR CODE - NAVAID OPERATOR NAME |
| `NAS_USE_FLAG` | Common System Usage (Y or N) Defines how the NAVAID is used. |
| `PUBLIC_USE_FLAG` | NAVAID PUBLIC USE (Y or N) Defines by whom the NAVAID is used. |
| `NDB_CLASS_CODE` | Class of NDB |
| `OPER_HOURS` | HOURS of Operation of NAVAID. |
| `HIGH_ALT_ARTCC_ID` | Identifier of ARTCC with High Altitude Boundary That the NAVAID Falls Within. |
| `HIGH_ARTCC_NAME` | Name of ARTCC with High Altitude Boundary That the NAVAID Falls Within. |
| `LOW_ALT_ARTCC_ID` | Identifier of ARTCC with Low Altitude Boundary That the NAVAID Falls Within. |
| `LOW_ARTCC_NAME` | Name of ARTCC with Low Altitude Boundary That the NAVAID Falls Within. |
| `LAT_DEG` | NAVAID Latitude Degrees |
| `LAT_MIN` | NAVAID Latitude Minutes |
| `LAT_SEC` | NAVAID Latitude Seconds |
| `LAT_HEMIS` | NAVAID Latitude Hemisphere |
| `LAT_DECIMAL` | NAVAID Latitude in Decimal Format |
| `LONG_DEG` | NAVAID Longitude Degrees |
| `LONG_MIN` | NAVAID Longitude Minutes |
| `LONG_SEC` | NAVAID Longitude Seconds |
| `LONG_HEMIS` | NAVAID Longitude Hemisphere |
| `LONG_DECIMAL` | NAVAID Longitude in Decimal Format |
| `SURVEY_ACCURACY_CODE` | Latitude/Longitude Survey Accuracy (Code) |
| `TACAN_DME_STATUS` | Status of TACAN or DME Equipment. |
| `TACAN_DME_LAT_DEG` | Latitude Degrees of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LAT_MIN` | Latitude Minutes of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LAT_SEC` | Latitude Seconds of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LAT_HEMIS` | Latitude Hemisphere of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LAT_DECIMAL` | Latitude in Decimal Format of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LONG_DEG` | Longitude Degrees of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LONG_MIN` | Longitude Minutes of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LONG_SEC` | Longitude Seconds of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LONG_HEMIS` | Longitude Hemisphere of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `TACAN_DME_LONG_DECIMAL` | Longitude in Decimal Format of TACAN Portion of VORTAC when TACAN is not sited with VOR |
| `ELEV` | Elevation in Tenth of a Foot (MSL). |
| `MAG_VARN` | Magnetic Variation Degrees (DME, VOT and FM NAVAID Types do not have MAG VAR. Any value in this column for those NAVAID Types should be ignored.) |
| `MAG_VARN_HEMIS` | Direction (east or west) of magnetic variation. |
| `MAG_VARN_YEAR` | Magnetic Variation Epoch Year (DME, VOT and FM NAVAID Types do not have MAG VAR YEAR. Any value in this column for those NAVAID Types should be ignored.) |
| `SIMUL_VOICE_FLAG` | Simultaneous Voice Feature |
| `PWR_OUTPUT` | Power Output (In Watts) |
| `AUTO_VOICE_ID_FLAG` | Automatic Voice Identification Feature |
| `MNT_CAT_CODE` | Monitoring Category |
| `VOICE_CALL` | Radio Voice Call (Name) or Trans Signal |
| `CHAN` | Channel (TACAN) NAVAID Transmits On |
| `FREQ` | Frequency the NAVAID Transmits On (Except TACAN) |
| `MKR_IDENT` | Transmitted Fan Marker/Marine Radio Beacon Identifier |
| `MKR_SHAPE` | Fan Marker Type (E - ELLIPTICAL) |
| `MKR_BRG` | True Bearing of Major Axis of Fan Marker |
| `ALT_CODE` | VOR Standard Service Volume |
| `DME_SSV` | DME Standard Service Volume |
| `LOW_NAV_ON_HIGH_CHART_FLAG` | Low Altitude Facility Used in High Structure |
| `Z_MKR_FLAG` | NAVAID Z Marker Available |
| `FSS_ID` | Associated/Controlling FSS (IDENT) |
| `FSS_NAME` | Associated/Controlling FSS (Name) |
| `FSS_HOURS` | Hours of Operation of Controlling FSS |
| `NOTAM_ID` | NOTAM Accountability Code (IDENT) |
| `QUAD_IDENT` | Quadrant Identification and Range Leg Bearing (LFR Only) |
| `PITCH_FLAG` | Pitch Flag |
| `CATCH_FLAG` | Catch Flag |
| `SUA_ATCAA_FLAG` | SUA/ATCAA Flag |
| `RESTRICTION_FLAG` | NAVAID Restriction Flag |
| `HIWAS_FLAG` | HIWAS Flag |

[Complete `NAV_BASE` column reference](../csv-tables/nav-base.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.nav.NavaidRecord
.. autoclass:: openNASR.repository.NavaidRepository
.. autoclass:: openNASR.nav.NAVAID
```

