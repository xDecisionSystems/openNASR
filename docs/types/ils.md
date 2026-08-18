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

## Plotting a localizer

Each `IlsRecord` can plot its surveyed transmitter and approach-course wedge:

```python
localizer = airport.ils[0]
figure, axes = localizer.plot(
    nasr,
    plot_wedge=True,
    wedge_distance_nm=20,
    projection="nautical_miles",
)
```

The wedge is 700 feet wide at the surveyed runway threshold and expands at a
2.5-degree half-angle. `wedge_distance_nm` controls how far it extends into
the approach area and defaults to 20 NM. Set `plot_wedge=False` to show only
the localizer transmitter. This visualization is for data exploration, not
operational navigation.

Pass a second Matplotlib axes as `side_axes=` to add the runway elevation
profile and FAA-published glide-slope angle. When a matching `ILS_GS` record is
available, the top view also includes its surveyed site:

```python
figure, (top_axes, side_axes) = plt.subplots(1, 2)
localizer.plot(nasr, axes=top_axes, side_axes=side_axes)
```

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
