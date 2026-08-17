# Flight Service Station

A `FlightServiceStation` combines one `FSS_BASE` station record with its
source-ordered `FSS_RMK` remarks.

## Composite key

(`FSS_ID`, `NAME`, `CITY`, `STATE_CODE`, `COUNTRY_CODE`)

```python
station = nasr.flight_service_stations.get(fss_key)

station.record
station.remarks
```

Using the complete key avoids treating a short station identifier as globally
unique.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.fss.FlightServiceStation
.. autoclass:: openNASR.fss.FlightServiceStationRecord
.. autoclass:: openNASR.fss.FlightServiceStationRemarkRecord
.. autoclass:: openNASR.fss.FlightServiceStationRepository
```

