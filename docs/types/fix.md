# Fix

`FixRecord` is a lossless `FIX_BASE` row with typed identifier, name,
coordinate, state, country, and ARTCC properties.

## Lookup

The primary identifier is `FIX_ID`.

```python
fix = nasr.fixes.get("AABEE")

fix.identifier
fix.latitude
fix.longitude
```

Use `nasr.fixes.find(...)` when a search may legitimately return multiple
records. `FIX` is retained as the legacy adapter.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.fix.FixRecord
.. autoclass:: openNASR.repository.FixRepository
.. autoclass:: openNASR.fix.FIX
```
