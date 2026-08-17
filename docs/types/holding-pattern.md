# Holding pattern

A `HoldingPattern` groups one published pattern with ordered charts, remarks,
speed/altitude restrictions, and an optional fully resolved fix.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `HPF_BASE` | Holding-pattern identity and geometry |
| `HPF_CHRT` | Chart references |
| `HPF_RMK` | Remarks |
| `HPF_SPD_ALT` | Speed and altitude restrictions |

The composite key is (`HP_NAME`, `HP_NO`, `STATE_CODE`, `COUNTRY_CODE`).

```python
key = (name, number, state, country)
pattern = nasr.holding_patterns.get(key)

pattern.record
pattern.charts
pattern.remarks
pattern.speed_altitude_limits
pattern.fix
```

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} HoldingPatternRecord raw fields — HPF_BASE (15)
`HoldingPatternRecord` preserves one complete `HPF_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `FIX_ID` | Fix with which Holding is Associated. |
| `ICAO_REGION_CODE` | ICAO Region Code of the Fix with which the Holding is Associated. |
| `NAV_ID` | NAVAID with which Holding is Associated. |
| `NAV_TYPE` | Facility Type of the NAVAID with which the Holding is Associated. |
| `HOLD_DIRECTION` | Direction of Holding on the NAVAID or Fix |
| `HOLD_DEG_OR_CRS` | Magnetic Bearing, Radial (Degrees) or Course Direction of Holding |
| `AZIMUTH` | Azimuth (Degrees Shown Above is a Radial, Course, Bearing, or RNAV Track) |
| `COURSE_INBOUND_DEG` | Inbound Course. |
| `TURN_DIRECTION` | Turning Direction |
| `LEG_LENGTH_DIST` | Leg Length Outbound DME (NM) |

[Complete `HPF_BASE` column reference](../csv-tables/hpf-base.md)
```

```{faa-dropdown} HoldingPatternChartRecord raw fields — HPF_CHRT (6)
`HoldingPatternChartRecord` preserves one complete `HPF_CHRT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `CHARTING_TYPE_DESC` | Chart on Which Holding Pattern is To Be Depicted. |

[Complete `HPF_CHRT` column reference](../csv-tables/hpf-chrt.md)
```

```{faa-dropdown} HoldingPatternRemarkRecord raw fields — HPF_RMK (9)
`HoldingPatternRemarkRecord` preserves one complete `HPF_RMK` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `TAB_NAME` | NASR table associated with Remark. |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks are identified as GENERAL_REMARK. |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark. |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) |

[Complete `HPF_RMK` column reference](../csv-tables/hpf-rmk.md)
```

```{faa-dropdown} HoldingPatternSpeedAltitudeRecord raw fields — HPF_SPD_ALT (7)
`HoldingPatternSpeedAltitudeRecord` preserves one complete `HPF_SPD_ALT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `HP_NAME` | Holding Pattern Identifier (NAVAID_NAME FACILITY_TYPE*STATE_CODE) OR (FIX_NAME FIX_TYPE*STATE_CODE*ICAO_REGION_CODE). |
| `HP_NO` | Pattern Number to Uniquely Identify Holding Pattern |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `SPEED_RANGE` | Speed Range for Holding Altitude of Record. |
| `ALTITUDE` | Holding Altitude for Speed Range of Record. |

[Complete `HPF_SPD_ALT` column reference](../csv-tables/hpf-spd-alt.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.holding.HoldingPattern
.. autoclass:: openNASR.holding.HoldingPatternRecord
.. autoclass:: openNASR.holding.HoldingPatternChartRecord
.. autoclass:: openNASR.holding.HoldingPatternRemarkRecord
.. autoclass:: openNASR.holding.HoldingPatternSpeedAltitudeRecord
.. autoclass:: openNASR.holding.HoldingPatternRepository
```

