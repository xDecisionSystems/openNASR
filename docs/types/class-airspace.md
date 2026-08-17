# Class airspace

`ClassAirspace` models the airport-linked `CLS_ARSP` family. Relationships use
the complete FAA site key rather than a potentially non-unique display ID.

## FAA source table and key

| Table | Composite key |
| --- | --- |
| `CLS_ARSP` | (`SITE_NO`, `SITE_TYPE_CODE`) |

```python
airspace = nasr.class_airspaces.get((site_no, site_type_code))

airspace.record
airspace.airport_site_key
airspace.classes
```

Use `find(airport_id=...)` for a non-unique short airport-ID search.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.ClassAirspace
.. autoclass:: openNASR.airspace.ClassAirspaceRecord
.. autoclass:: openNASR.airspace.ClassAirspaceRepository
```

