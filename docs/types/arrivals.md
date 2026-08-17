# Arrivals

The arrivals API models FAA Standard Terminal Arrival Routes (STARs). A
`StarProcedure` combines one published procedure with its airport associations
and FAA-ordered route points.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `STAR_BASE` | STAR identity |
| `STAR_APT` | Airport associations |
| `STAR_RTE` | Ordered routes and points |

The composite key is (`STAR_COMPUTER_CODE`, `ARTCC`).

```python
key = (computer_code, artcc)
arrival = nasr.stars.get(key)

arrival.record
arrival.airports
arrival.routes
```

## Generated API

```{eval-rst}
.. autoclass:: openNASR.arrivals.StarProcedure
.. autoclass:: openNASR.arrivals.StarProcedureRecord
.. autoclass:: openNASR.arrivals.StarAirportRecord
.. autoclass:: openNASR.arrivals.StarRouteRecord
.. autoclass:: openNASR.arrivals.StarProcedureRepository
```

