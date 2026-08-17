# Radar

A `Radar` wraps one standalone `RDR` row. Exact lookup uses the complete
published facility and radar identity.

## Composite key

(`FACILITY_ID`, `FACILITY_TYPE`, `STATE_CODE`, `COUNTRY_CODE`, `RADAR_TYPE`,
`RADAR_NO`)

```python
radar = nasr.radars.get(radar_key)
record = radar.record
```

Use `find()` to enumerate source-ordered radar records or to handle a search
that may return more than one result.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.atc.Radar
.. autoclass:: openNASR.atc.RadarRecord
.. autoclass:: openNASR.atc.RadarRepository
```
