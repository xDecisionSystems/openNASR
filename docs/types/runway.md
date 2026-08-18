# Runway

Runway data is attached to an `AirportRecord`. `RunwayRecord` describes the
complete landing surface; `RunwayEndRecord` describes one physical end.

## FAA source tables

| Table | Content |
| --- | --- |
| `APT_RWY` | Runway identifier, dimensions, surface, and status |
| `APT_RWY_END` | End identifier, threshold position, elevation, and declared distances |

## Access

```python
airport = nasr.airports.get("ATL")

for runway in airport.runways:
    print(runway["RWY_ID"])

for runway_end in airport.runway_ends:
    print(runway_end["RWY_END_ID"])
```

The legacy `RWY` adapters remain documented for existing callers, but new code
should use the lossless record tuples on `AirportRecord`.

## Plotting

Each runway record plots the surveyed threshold-to-threshold segment:

```python
runway = airport.runways[0]
figure, axes = runway.plot(
    nasr,
    projection="nautical_miles",
    projection_center=(airport.latitude, airport.longitude),
)
```

The method accepts the same axes, geographic/nautical-mile/Web Mercator
projection, legend, and reusable `PlottingIndex` options as other modern
plotting methods.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.rwy.RunwayRecord
.. autoclass:: openNASR.rwy.RunwayEndRecord
.. autoclass:: openNASR.rwy.RWY
.. autoclass:: openNASR.rwy.RWYitem
.. autoclass:: openNASR.rwy.RWYEnd
.. autoclass:: openNASR.rwy.RWYEnditem
```
