# Military operation

A `MilitaryOperation` models one airport-linked `MIL_OPS` row. It joins to an
airport through the complete FAA site identity rather than a short airport ID.

## FAA source table and key

| Table | Composite key |
| --- | --- |
| `MIL_OPS` | (`SITE_NO`, `SITE_TYPE_CODE`) |

```python
operation = nasr.military_operations.get((site_no, site_type_code))

operation.record
operation.airport_site_key
operation.airport_id
```

Use `find(airport_id=...)` when searching by a potentially non-unique short
identifier.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.military.MilitaryOperation
.. autoclass:: openNASR.military.MilitaryOperationRecord
.. autoclass:: openNASR.military.MilitaryOperationRepository
```

