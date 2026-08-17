# Fix

`FixRecord` is a lossless `FIX_BASE` row with typed identifier, name,
coordinate, state, country, and ARTCC properties.

## Lookup

The primary identifier is `FIX_ID`.

```python
fix = nasr.fixes.get("AABEE")

fix.identifier
fix.latitude
fix.longitude
```

Use `nasr.fixes.find(...)` when a search may legitimately return multiple
records. `FIX` is retained as the legacy adapter.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} FixRecord raw fields — FIX_BASE (26)
`FixRecord` preserves one complete `FIX_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `FIX_ID` | Fixed Geographical Position Identifier. |
| `ICAO_REGION_CODE` | International Civil Aviation Organization (ICAO) Code. In General, the First Letter of an ICAO Code refers to the Country. The Second Letter discerns the Region within the Country. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `LAT_DEG` | FIX Latitude Degrees |
| `LAT_MIN` | FIX Latitude Minutes |
| `LAT_SEC` | FIX Latitude Seconds |
| `LAT_HEMIS` | FIX Latitude Hemisphere |
| `LAT_DECIMAL` | FIX Latitude in Decimal Format |
| `LONG_DEG` | FIX Longitude Degrees |
| `LONG_MIN` | FIX Longitude Minutes |
| `LONG_SEC` | FIX Longitude Seconds |
| `LONG_HEMIS` | FIX Longitude Hemisphere |
| `LONG_DECIMAL` | FIX Longitude in Decimal Format |
| `FIX_ID_OLD` | Previous Name(s) of the Fix before It was Renamed. |
| `CHARTING_REMARK` | Charting Information. |
| `FIX_USE_CODE` | FIX Type. |
| `ARTCC_ID_HIGH` | Denotes High ARTCC Area Of Jurisdiction. |
| `ARTCC_ID_LOW` | Denotes Low ARTCC Area Of Jurisdiction. |
| `PITCH_FLAG` | Pitch (Y = YES or N = NO) |
| `CATCH_FLAG` | Catch (Y = YES or N = NO) |
| `SUA_ATCAA_FLAG` | SUA/ATCAA (Y = YES or N = NO) |
| `MIN_RECEP_ALT` | Fix Minimum Reception Altitude (MRA) |
| `COMPULSORY` | Compulsory FIX identified as HIGH or LOW or LOW/HIGH. Null in this field identifies Non-Compulsory FIX. |
| `CHARTS` | Concatenated list of the information found in the FIX_CHRT file separated by a comma. |

[Complete `FIX_BASE` column reference](../csv-tables/fix-base.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.fix.FixRecord
.. autoclass:: openNASR.repository.FixRepository
.. autoclass:: openNASR.fix.FIX
```

