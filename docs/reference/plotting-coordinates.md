# Plotting and coordinates

Plotting functions return Matplotlib `(Figure, Axes)` pairs. Install the
`plot` extra before calling them. Coordinate projection distances are nautical
miles; geographic coordinate pairs are explicitly documented as either
latitude/longitude or longitude/latitude.

All public plotting functions support three output coordinate systems:

- `projection="geographic"` (the default): longitude and latitude in degrees.
- `projection="nautical_miles"`: local gnomonic east/north nautical miles,
  centered automatically or with `projection_center=(latitude, longitude)`.
- `projection="web_mercator"`: EPSG:3857-compatible x/y meters for Google Maps
  and other Web Mercator tile layers. Latitudes are clipped to the standard
  Web Mercator limit of approximately 85.051129 degrees.

`project_to_nm=True` remains supported as an alias for
`projection="nautical_miles"`. Web Mercator is a fixed global projection and
therefore does not accept `projection_center`.

```python
figure, axes = plot_airspace(
    nasr,
    boundary,
    projection="web_mercator",
)
```

## Plotting

```{eval-rst}
.. automodule:: openNASR.plotting
```

## Coordinate projections

```{eval-rst}
.. automodule:: openNASR.coordinates
```

## Legacy coordinate implementation

```{eval-rst}
.. automodule:: openNASR.cfcn
```
