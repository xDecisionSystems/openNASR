# Examples

These examples are complete, runnable scripts that load a locally cached FAA
NASR cycle and produce the figures shown in the documentation. The scripts and
their generated PNG files are checked into the repository's `examples/`
directory.

Install the plotting dependencies and download a cycle before running them:

```bash
python -m pip install "openNASR[plot]"
opennasr download latest
```

Each script has a short configuration block near the top. Edit its cycle,
cache directory, output path, display choice, and example-specific identifiers
before running it. The checked-in defaults reproduce the figures from the
2026-05-14 cycle; details can vary between effective cycles.

- [Plotting an airport](plotting-airport.md) separates runways, ILS component
  sites, arrivals, and departures into readable panels.
- [Plotting an ILS](plotting-ils.md) shows a runway, localizer course, and glide
  slope in top and side views.
- [Plotting an ARTCC](plotting-artcc.md) draws an ARTCC boundary with airports
  and high- and low-altitude airways.
- [Converting a flight plan to a path](flight-plan-path.md) resolves FAA route
  text into ordered latitude/longitude coordinates and plots the result.
