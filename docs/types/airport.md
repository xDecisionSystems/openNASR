# Airport

An `AirportRecord` preserves one airport base row and attaches its runway,
runway-end, ILS, class-airspace, and military-operation relationships.

## FAA source tables

| Table | Related data |
| --- | --- |
| `APT_BASE` | Identity, name, position, elevation, and status |
| `APT_RWY` / `APT_RWY_END` | Runways and physical runway ends |
| `ILS_BASE` / `ILS_DME` / `ILS_GS` / `ILS_MKR` | Landing-system components |
| `CLS_ARSP` / `MIL_OPS` | Relationships through the complete airport site key |

## Lookup

```python
airport = nasr.airports.get("ATL")
same_airport = nasr.airports.get("KATL")

airport.faa_id
airport.runways
airport.ils
airport.class_airspace

# Plot runways, departures, and arrivals for this airport.
figure, axes = airport.plot(nasr)
```

FAA and ICAO identifiers are normalized case-insensitively. The modern
repository returns `AirportRecord`; `Airport` is the compatibility aggregate.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airport.AirportRecord
.. autoclass:: openNASR.repository.AirportRepository
.. autoclass:: openNASR.airport.Airport
```
