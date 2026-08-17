# Preferred routes

A `PreferredRoute` combines one preferred-route identity record with its route
format records and FAA-ordered segments.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `PFR_BASE` | Preferred-route identity |
| `PFR_RMT_FMT` | Route-format variants |
| `PFR_SEG` | Ordered route segments |

The composite key is (`ORIGIN_ID`, `DSTN_ID`, `PFR_TYPE_CODE`, `ROUTE_NO`).

```python
key = (origin, destination, route_type, route_number)
route = nasr.preferred_routes.get(key)

route.record
route.formats
route.segments
```

Use `find()` to enumerate preferred routes in FAA source order. Exact lookup
raises `RecordNotFoundError` for no match and `AmbiguousRecordError` if the
selected cycle contains duplicate complete keys.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.departure.PreferredRoute
.. autoclass:: openNASR.departure.PreferredRouteRecord
.. autoclass:: openNASR.departure.PreferredRouteFormatRecord
.. autoclass:: openNASR.departure.PreferredRouteSegmentRecord
.. autoclass:: openNASR.departure.PreferredRouteRepository
```
