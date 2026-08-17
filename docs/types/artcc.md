# ARTCC

An `Artcc` represents one Air Route Traffic Control Center and its published
high- and low-altitude boundary geometry.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `ARB_BASE` | Center identity and reference position |
| `ARB_SEG` | Ordered altitude-specific boundary vertices |

The lookup key is `LOCATION_ID`.

```python
center = nasr.artccs.get("ZOB")

center.record
center.high
center.low
center.high.getShape
```

Boundary coordinate properties explicitly distinguish `latlon` from `lonlat`.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.Artcc
.. autoclass:: openNASR.airspace.ArtccBoundary
.. autoclass:: openNASR.airspace.ArtccRecord
.. autoclass:: openNASR.airspace.ArtccRepository
.. autoclass:: openNASR.arb.Boundary
.. autoclass:: openNASR.arb.ARB
```

