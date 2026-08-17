# Instrument landing system

Instrument landing system records are attached to an `AirportRecord` and
preserve the FAA's separate base, DME, glide-slope, and marker rows.

## FAA source tables

| Table | Record type |
| --- | --- |
| `ILS_BASE` | `IlsRecord` |
| `ILS_DME` | `DmeRecord` |
| `ILS_GS` | `GlideSlopeRecord` |
| `ILS_MKR` | `MarkerRecord` |

## Access

```python
airport = nasr.airports.get("ATL")

airport.ils
airport.dmes
airport.glide_slopes
airport.markers
```

The related tuples preserve FAA source order and raw source values.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.ils.IlsRecord
.. autoclass:: openNASR.ils.DmeRecord
.. autoclass:: openNASR.ils.GlideSlopeRecord
.. autoclass:: openNASR.ils.MarkerRecord
.. autoclass:: openNASR.ils.ILSBase
.. autoclass:: openNASR.ils.ILSDME
.. autoclass:: openNASR.ils.ILSGS
.. autoclass:: openNASR.ils.ILSMKR
```
