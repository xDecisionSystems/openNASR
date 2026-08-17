# API reference

## Main entry points

- `NASR(useDate=None, update=False, preloadAll=False, diagnostic=False,
  cycle=None, storage="csv")` loads a local FAA cycle. `storage="duckdb"`
  opens a previously built exact-date DuckDB artifact and never falls back to
  CSV or another cycle. Tables remain available by FAA name, for example
  `nasr["APT_BASE"]`.
- `Airport(identifier, nasr)`, `FIX(identifier, nasr)`, `NAVAID(identifier,
  nasr, ...)`, and `ARB(nasr)` are the legacy compatibility constructors.
- `CycleManager(cache_dir=None, provider=None)` manages cached archive,
  extracted-cycle, and optional per-cycle DuckDB data. Use
  `import_archive(path)`, `get(effective_date)`, `build_duckdb(cycle)`,
  `duckdb_path(cycle)`, and `check_for_updates(force=False)` for cycle
  operations. `remove(..., duckdb=True)` removes only the derivative.

The command-line equivalents are `opennasr build-duckdb YYYY-MM-DD` (or
`latest`) and `opennasr list --storage`.

## Route-field paths

`flight_plan_path(nasr, route)` returns an ordered tuple of source
`(latitude, longitude)` coordinates. For batches, construct
`RouteResolver(nasr)` once and call `.path(route)`; a resolver is a snapshot
of one selected NASR cycle, so construct a new resolver after changing a
table, backend, or cycle.

The domestic parser accepts whitespace-separated and FAA dotted forms, `..`
or `DCT` direct segments, and an optional trailing `/speed-altitude` suffix.
It resolves domestic airports, fixes, navaids, published airways, DPs, STARs,
and transitions from the selected cycle. Returned coordinates retain source
order and are not an operational route validation or clearance.

Foreign airports, external airways/procedures, oceanic coordinates, and
radial-distance points are outside the domestic NASR contract and raise
`UnsupportedRouteContentError`. Coordinate tokens are deliberately not parsed
locally in this release because NASR cannot validate their surrounding route
structure. Unknown domestic records raise `RecordNotFoundError`, ambiguous
records raise `AmbiguousRecordError`, and a published procedure/airway pair
with no valid source-backed join raises `RouteConnectivityError`.

## Plotting and reusable lookup indexes

The optional plotting helpers return Matplotlib `(figure, axes)` pairs:

```python
from openNASR import PlottingIndex, plot_airport_procedures, plot_airspace

plotting_index = PlottingIndex(nasr)
figure, axes = plot_airport_procedures(
    nasr, "ATL", index=plotting_index, plot_legend=False
)
```

`PlottingIndex` is a public, snapshot-scoped lookup session. It covers the
navigation, airway, airport, procedure, and runway tables used by
`plot_airspace`, `plot_airport_procedures`, and `plot_flight_plan`. Derived
feature indexes and the route resolver are lazy, so a caller pays only for
the layers it uses. Pass the same keyword-only `index=` to repeated plotting
calls to reuse those lookups—for example, to plot a batch of airports—rather
than constructing a session for every figure.

The index belongs to the exact NASR table mapping passed to its constructor;
passing it with another mapping raises `ValueError`. Each cached lookup is
built lazily, the first time it is needed, from whatever the mapping contains
at that moment—construction itself copies nothing. Treat the tables as
immutable for the lifetime of the session and construct a new
`PlottingIndex(nasr)` after changing a table, switching cycles, or switching
storage backends; mutating a table in place partway through a session's
lifetime can leave already-cached lookups reflecting the old data while
not-yet-accessed lookups pick up the new data. This preserves source-row
order, raw coordinate values, and the existing duplicate/ambiguous endpoint
behavior. The index is an optional optimization: omitting `index=` preserves
the plotting helper API and creates a session for that call.

## Repository facade

`NASR` provides plural repositories and singular convenience lookups:

- `nasr.airports.get(identifier)` / `nasr.airport(identifier)`
- `nasr.fixes.get(identifier)` / `nasr.fix(identifier)`
- `nasr.navaids.get(identifier, *, state=None, country=None, artcc=None,
  nav_type=None)` / `nasr.navaid(...)`
- `nasr.class_airspaces.get((site_no, site_type_code))` returns a
  `ClassAirspace`; `find(airport_id=...)` supports non-unique short airport-ID
  searches.
- `nasr.military_operations.get((site_no, site_type_code))` returns a
  `MilitaryOperation`; `find(airport_id=...)` supports non-unique short
  airport-ID searches.
- `nasr.artccs.get(location_id)` / `nasr.artcc(...)` return an `Artcc` with
  `high`/`low` `ArtccBoundary` geometry backed by the same `Boundary` class
  the legacy `ARB` path uses.
- `nasr.maas.get(maa_id)` / `nasr.maa(...)` return a `Maa` (the FAA's
  "Miscellaneous Activity Area" family: aerobatic practice, glider, hang
  glider, space launch, ultralight, and unmanned-aircraft areas) with
  `contacts`, `remarks`, and a `geometry` Shapely polygon built from ordered
  `MAA_SHP` points, or `None` for radius-only areas with no published shape.
- `nasr.parachute_jump_areas.get(pja_id)` / `nasr.parachute_jump_area(...)`
  return a `ParachuteJumpArea` with `contacts` and an optional `airport` link
  (present on roughly two thirds of real areas).
- `nasr.military_training_routes.get((route_type_code, route_id))` /
  `nasr.military_training_route(...)` return a `MilitaryTrainingRoute` with
  FAA-sequence-ordered `agencies`, `points`, `procedures`, `terrain`, and
  `widths`. Route points carry a distinct `identifier` (`ROUTE_PT_ID`) from
  their display `sequence` (`ROUTE_PT_SEQ`), per the FAA's own documentation.
- `nasr.airways.get((regulatory, airway_location, airway_id))` /
  `nasr.airway(...)` return an `Airway` with FAA-sequence-ordered `segments`.
- `nasr.holding_patterns.get((name, number, state, country))` /
  `nasr.holding_pattern(...)` return a `HoldingPattern` with `charts`,
  `remarks`, and `speed_altitude_limits`.
- `nasr.communication_outlets.get(identifier)` /
  `nasr.communication_outlet(...)` return standalone `CommunicationOutlet`
  records. Communication location IDs are not assumed unique.
- `nasr.frequencies.get((facility, serviced_facility, serviced_site_type,
  serviced_state, serviced_country, frequency, sectorization, frequency_use))`
  /
  `nasr.frequency(...)` return a `Frequency`; `find(serviced_facility=(...))`
  requires the complete serviced-facility context.
- `nasr.coded_departure_routes.get(route_code)`, `nasr.departures.get(key)`,
  `nasr.preferred_routes.get(key)`, and `nasr.stars.get(key)` expose rich FAA
  procedure and route objects; route collections retain FAA sequence order.

Use repository `find(...)` methods for searches. Identifiers are normalized by
stripping surrounding whitespace and uppercasing. Exact duplicate matches raise
`AmbiguousRecordError`.

## Records and tables

- `FaaRecord` is the lossless mapping base class; use `raw` or `as_dict()` to
  access source fields.
- `AirportRecord`, `FixRecord`, `NavaidRecord`, `ClassAirspaceRecord`,
  `MilitaryOperationRecord`, `AirwayRecord`, `AirwaySegmentRecord`,
  `HoldingPatternRecord`, `CommunicationOutletRecord`, `FrequencyRecord`,
  `ArtccRecord`, `MaaRecord`, `ParachuteJumpAreaRecord`, and
  `MilitaryTrainingRouteRecord` expose typed convenience properties while
  preserving raw FAA values.
- `AirportRecord.class_airspace` returns one `ClassAirspace` only when the
  complete `(SITE_NO, SITE_TYPE_CODE)` relationship is unambiguous.
  `AirportRecord.military_operations` returns an immutable tuple of matching
  `MilitaryOperation` objects.
- Airway-point, holding-pattern, and communication-outlet links resolve only
  when all documented key fields match. Frequency records retain a composite
  serviced-facility lookup and never join on a display name alone.
- `TableRepository(cycle_path)` lazily discovers and loads CSV tables;
  `table(name, copy=False)` returns the cached table.

## Coordinates and boundaries

- `coordinates.ll2xy(latitudes, longitudes, ...)` projects to local east/north
  coordinates in nautical miles.
- `coordinates.xy2ll(x, y, ...)` returns latitude/longitude values.
- `Boundary` exposes `lonlat`, `latlon`, `bbox`, and the Shapely geometry via
  `getShape`.

## Errors

All public failures derive from `OpenNASRError`. Common subclasses include
`CycleNotFoundError`, `DownloadError`, `ArchiveError`, `TableNotFoundError`,
`SchemaMismatchError`, `FieldConversionError`, `RecordNotFoundError`, and
`AmbiguousRecordError`.
