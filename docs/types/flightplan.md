# Flight planning

`RouteResolver` converts supported domestic FAA route-field text into an
ordered tuple of `(latitude, longitude)` source coordinates. It resolves
airports, fixes, navaids, airways, departure procedures, STARs, and transitions
from one selected cycle.

## Resolve one route

```python
from openNASR import flight_plan_path

coordinates = flight_plan_path(nasr, "KATL VXV V97 BNA KBNA")
```

## Reuse indexes for a batch

```python
from openNASR import RouteResolver

resolver = RouteResolver(nasr)
first = resolver.path("KATL VXV V97 BNA KBNA")
second = resolver.path("KBWI TERPZ6.OTT DCT KIAD")
```

A resolver snapshots one table mapping. Construct a new resolver after
changing tables, cycle, or storage backend. This API resolves published route
data but does not validate an operational flight plan.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.flightplan.RouteResolver
.. autofunction:: openNASR.flightplan.flight_plan_path
```
