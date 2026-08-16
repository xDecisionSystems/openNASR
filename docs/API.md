# API reference

## Main entry points

- `NASR(useDate=None, update=False, preloadAll=False, diagnostic=False)` loads a
  local FAA cycle. Tables remain available by FAA name, for example
  `nasr["APT_BASE"]`.
- `Airport(identifier, nasr)`, `FIX(identifier, nasr)`, `NAVAID(identifier,
  nasr, ...)`, and `ARB(nasr)` are the legacy compatibility constructors.
- `CycleManager(cache_dir=None, provider=None)` manages cached archive and
  extracted-cycle data. Use `import_archive(path)`, `get(effective_date)`, and
  `check_for_updates(force=False)` for cycle operations.

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

Use repository `find(...)` methods for searches. Identifiers are normalized by
stripping surrounding whitespace and uppercasing. Exact duplicate matches raise
`AmbiguousRecordError`.

## Records and tables

- `FaaRecord` is the lossless mapping base class; use `raw` or `as_dict()` to
  access source fields.
- `AirportRecord`, `FixRecord`, `NavaidRecord`, `ClassAirspaceRecord`, and
  `MilitaryOperationRecord` expose typed convenience properties while
  preserving raw FAA values.
- `AirportRecord.class_airspace` returns one `ClassAirspace` only when the
  complete `(SITE_NO, SITE_TYPE_CODE)` relationship is unambiguous.
  `AirportRecord.military_operations` returns an immutable tuple of matching
  `MilitaryOperation` objects.
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
