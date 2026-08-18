# Plotting an ILS

This example selects ATL runway 08L/26R and the ILS associated with runway end
08L. It plots the runway with `RunwayRecord.plot()` and overlays the localizer
with `IlsRecord.plot()`. The top view contains the runway, localizer
transmitter, localizer wedge, and surveyed glide-slope site. The side view
contains the runway elevation profile and FAA-published glide-slope angle. The
wedge is 700 feet wide at the runway threshold, expands at a 2.5-degree
half-angle, and extends 20 NM by default. Edit `wedge_distance_nm` to change
the distance or set `plot_wedge = False` to hide it.

The source rows come from `APT_RWY`, `APT_RWY_END`, `ILS_BASE`, and `ILS_GS`. The diagram
is intended for data exploration and is not an operational approach chart.

Run it with:

```bash
python examples/plot_ils.py
```

The configuration block exposes `airport_id`, `runway_id`, `runway_end_id`,
`cycle`, `cache_dir`, `plot_wedge`, `wedge_distance_nm`, `output_path`, and
`show_plot`.

## Script

```{literalinclude} ../../examples/plot_ils.py
:language: python
:linenos:
```

## Result

![ATL runway 08L ILS top and side views](../../examples/plot_ils.png)
