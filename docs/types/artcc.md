# ARTCC

An `Artcc` represents one Air Route Traffic Control Center and its published
high- and low-altitude boundary geometry.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `ARB_BASE` | Center identity and reference position |
| `ARB_SEG` | Ordered altitude-specific boundary vertices |

The lookup key is `LOCATION_ID`.

```python
center = nasr.artccs.get("ZOB")

center.record
center.high
center.low
center.high.getShape

# Plot the high-altitude boundary and its map layers (the default).
figure, axes = center.plot(nasr)

# Plot the low-altitude boundary instead.
figure, axes = center.plot(nasr, level="low")
```

Boundary coordinate properties explicitly distinguish `latlon` from `lonlat`.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} ArtccRecord raw fields — ARB_BASE (20)
`ArtccRecord` preserves one complete `ARB_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `LOCATION_ID` | Location Identifier. 3-4 character alphanumeric identifier. |
| `LOCATION_NAME` | Center Name. |
| `COMPUTER_ID` | Location Computer Identifier |
| `ICAO_ID` | ICAO Identifier |
| `LOCATION_TYPE` | Location Type (ARTCC or CERAP). |
| `CITY` | Location City Name |
| `STATE` | Location State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Location Country Post Office Code |
| `LAT_DEG` | Location Reference Point Latitude Degrees |
| `LAT_MIN` | Location Reference Point Latitude Minutes |
| `LAT_SEC` | Location Reference Point Latitude Seconds |
| `LAT_HEMIS` | Location Reference Point Latitude Hemisphere |
| `LAT_DECIMAL` | Location Reference Point Latitude in Decimal Format |
| `LONG_DEG` | Location Reference Point Longitude Degrees |
| `LONG_MIN` | Location Reference Point Longitude Minutes |
| `LONG_SEC` | Location Reference Point Longitude Seconds |
| `LONG_HEMIS` | Location Reference Point Longitude Hemisphere |
| `LONG_DECIMAL` | Location Reference Point Longitude in Decimal Format |
| `CROSS_REF` | Cross Reference Text (Free Form Text that further describes a specific Information Item.) |

[Complete `ARB_BASE` column reference](../csv-tables/arb-base.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.Artcc
.. autoclass:: openNASR.airspace.ArtccBoundary
.. autoclass:: openNASR.airspace.ArtccRecord
.. autoclass:: openNASR.airspace.ArtccRepository
.. autoclass:: openNASR.arb.Boundary
.. autoclass:: openNASR.arb.ARB
```
