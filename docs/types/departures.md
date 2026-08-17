# Departures

The departures API covers coded departure routes, departure procedures, and
preferred routes. Each repository preserves the FAA's complete identity key
and source-defined child ordering.

## Coded departure routes

`CDR` contains standalone routes keyed by `RCode`.

```python
coded_route = nasr.coded_departure_routes.get(route_code)
```

```{eval-rst}
.. autoclass:: openNASR.departure.CodedDepartureRoute
.. autoclass:: openNASR.departure.CodedDepartureRouteRecord
.. autoclass:: openNASR.departure.CodedDepartureRouteRepository
```

## Departure procedures

| Table | Content |
| --- | --- |
| `DP_BASE` | Procedure identity |
| `DP_APT` | Airport associations |
| `DP_RTE` | Ordered routes and points |

The composite key is (`DP_NAME`, `ARTCC`, `DP_COMPUTER_CODE`).

```python
procedure = nasr.departures.get((procedure_name, artcc, computer_code))
procedure.airports
procedure.routes
```

```{eval-rst}
.. autoclass:: openNASR.departure.DepartureProcedure
.. autoclass:: openNASR.departure.DepartureProcedureRecord
.. autoclass:: openNASR.departure.DepartureAirportRecord
.. autoclass:: openNASR.departure.DepartureRouteRecord
.. autoclass:: openNASR.departure.DepartureProcedureRepository
```

## Preferred routes

Preferred routes have their own source tables, composite lookup key, route
formats, and ordered segments. See the dedicated {doc}`preferred-route` page.

