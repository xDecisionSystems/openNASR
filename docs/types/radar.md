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

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} RadarRecord raw fields — RDR (9)
`RadarRecord` preserves one complete `RDR` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. |
| `FACILITY_TYPE` | Type of Facility associated with the RADAR data – either AIRPORT or TRACON. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code Airport or TRACON is Located. |
| `RADAR_TYPE` | RADAR Type Code. |
| `RADAR_NO` | Unique Sequence Number assigned to each Radar at a Facility. |
| `RADAR_HRS` | RADAR Hours of Operation. |
| `REMARK` | Remark associated with RADAR Operations. |

[Complete `RDR` column reference](../csv-tables/rdr.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.atc.Radar
.. autoclass:: openNASR.atc.RadarRecord
.. autoclass:: openNASR.atc.RadarRepository
```

