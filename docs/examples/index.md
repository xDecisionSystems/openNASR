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
- [Plotting an ILS](plotting-ils.md) combines the runway and localizer class
  plotting methods in one concise example.
- [Plotting an ARTCC](plotting-artcc.md) draws an ARTCC boundary with airports
  and high- and low-altitude airways.
- [Plotting the National Airspace System](plotting-nas.md) draws all ARTCC
  boundaries and the airway network, with an Alaska inset.
- [Plotting an FIR](plotting-fir.md) draws the Honolulu CTA/FIR through the
  typed airspace-boundary API.
- [Listing entities in an ARTCC](printing-airspace-entities.md) prints the
  airports, fixes, and airways inside Cleveland Center.
- [Converting a flight plan to a path](flight-plan-path.md) resolves FAA route
  text into ordered latitude/longitude coordinates and plots the result.
