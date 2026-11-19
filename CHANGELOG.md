# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow Semantic Versioning.

## [Unreleased]

## [2.1.31]

### Changed

- ARTCC search shows matching centers and removable selection tags.

## [2.1.30]

### Fixed

- Removing an airport keeps the current map center and zoom.

## [2.1.29]

### Fixed

- Airport procedure overlays stay enabled as airports are added or removed.

## [2.1.28]

### Changed

- Maps use a taller, near-square layout across the explorer.

## [2.1.27]

### Changed

- Airport matches sort by distance to the nearest selected airport, then longest runway.

## [2.1.26]

### Changed

- Plots keep their view when layers change and have no fixed zoom bounds.

## [2.1.25]

### Fixed

- Airport search matches common FAA name abbreviations and punctuation variants.

## [2.1.24]

### Changed

- ARTCC fix and navaid overlays draw FAA chart symbols by feature type.

## [2.1.23]

### Added

- Search for airports and plot multiple matches using removable selection tags.

## [2.1.22]

### Changed

- The ARTCC and Other Airspace menus support multiple selections.

## [2.1.21]

### Changed

- ARTCC class airspace overlays fetch only the selected classes in the current map view and ARTCC.

## [2.1.20]

### Changed

- The ARTCC tab groups FIR, CTA, UTA, and CTA/FIR in an Other Airspace dropdown.

## [2.1.19]

### Changed

- The ARTCC tab lists centers by FAA code and name and focuses the map on selection.

## [2.1.18]

### Fixed

- Airspace overlays reduce outline detail at wider views.

## [2.1.17]

### Added

- Airport maps can show airspace outlines in the current view as users pan and zoom.

## [2.1.16]

### Added

- Airport maps can show the published airspace boundaries containing the airport.

## [2.1.15]

### Changed

- Double-click zoom centers the plot on the clicked location.

## [2.1.14]

### Fixed

- The Airspace overview keeps Alaska and the Aleutians west of the contiguous U.S.

## [2.1.13]

### Fixed

- The explorer revalidates its HTML and loads versioned assets to avoid mixing releases.

## [2.1.12]

### Changed

- Airport map checkboxes share a wrapping row. ILS toggles wedges and transmitter locations together and starts off.

## [2.1.11]

### Fixed

- Plots hide labels for points outside the visible map.

## [2.1.10]

### Changed

- Every explorer tab rotates its Try example at random.

## [2.1.9]

### Added

- Double-click any plot to zoom in, or Shift-double-click to zoom out at the pointer.

## [2.1.8]

### Added

- Airspace maps can overlay fixes, VOR-family stations, NDBs, and other navaids.

## [2.1.7]

### Added

- Airport maps can overlay all published arrivals and departures for the selected airport.

## [2.1.6]

### Added

- Airspace opens with all ARTCC outlines and offers other airspace boundaries as overlays.

## [2.1.5]

### Added

- Drag a box with Zoom area to focus any explorer plot on the selected area.
- Plot layer checkboxes appear below the plot on every tab.

## [2.1.4]

### Added

- The Routes tab plots published jetways and airways with waypoint labels and
  reports gaps or unresolved positions. The Flight Plan tab resolves routes.
- All explorer plots support zooming, panning, and fitting to the data.

## [2.1.3]

### Added

- Airspace queries plot the matching FAA ARTCC outlines. Map checkboxes load
  airports, departures, arrivals, and jetways or airways within those outlines.

## [2.1.2]

### Added

- Airport results and printouts display surveyed ILS localizers and illustrative
  course wedges. The Airport tab can hide wedges for a closer view of the layout.

## [2.1.1]

### Added

- Arrival and departure lookups return separate published branches with
  waypoint positions. The explorer plots and labels each branch and lets
  users show or hide individual branches.
- The Airport tab plots runway centerlines and labels their ends, marks and
  labels helipads, and identifies records with unavailable geometry.

## [2.1.0]

### Added

- The API's main page now provides a graphical explorer for airports, airspace,
  routes, arrivals, and departures. Arrival and departure queries also have
  dedicated HTTP endpoints with published procedure points.

- Builder 2 publishes each cycle's FAA Class B/C/D/E shapefile ZIP and derived
  Parquet alongside the existing NASR artifacts.
- `/v1/airspace/at` returns the available Class B/C/D/E polygons with their
  published lower and upper altitude limits. Cycle data from builder 1 remains
  usable for the existing boundary queries.
- Ambiguous route identifiers include all matching candidates in their
  diagnostic details.

### Changed

- The core package and its build metadata now live under `core/` in the
  repository. The installed package is still imported as `openNASR`.
- Route resolution uses separate modules behind the existing `flightplan.py`
  import interface.

### Fixed

- Route validation excludes informational diagnostics when classifying
  malformed routes.

## [2.0.1]

### Changed

- Signed deployment releases include hash-pinned dependencies for the API and
  archiver. The updater verifies the lockfiles and retains each guest's DuckDB
  version pin.
- Before activating a new archiver release, the updater checks that it can read
  the configured bucket as the service account.
- After a successful switch, the updater prunes superseded virtual environments
  while keeping the active and rollback environments. Cleanup waits when the
  archiver is running.

## [2.0.0] - 2026-11-18

### Breaking (2.0)

- `NASR` serves every cycle from a read-only DuckDB artifact; CSV storage was
  removed (`storage="csv"` raises `ConfigurationError`). The artifact is built on
  first use, and a cycle holding only `nasr.duckdb` plus its sidecar can be served
  without any archive or CSVs.
- `duckdb` is a required dependency, capped below 2.0 (the 2.0.0 wheel crashes on
  CPUs without AVX2); the `openNASR[duckdb]` extra was removed.
- DuckDB sidecar format 2 records the FAA `schema_id` identified at build time;
  format-1 artifacts are rebuilt when sources are present.
- Removed `openNASR.tables.TableRepository` and the CSV query fallback.
- Raw tables are always source text; legacy `Airport` coordinate, elevation,
  runway-size and bearing accessors now convert numeric text to numbers.

### Fixed

- The schema manifests ship inside the package (`openNASR/schema_manifests/`); an installed wheel previously could not open any
  cycle because it looked for them under `tests/`. Version is now 2.0.0.
- `deploy/proxmox/install.sh` creates an archiver or API container and picks a DuckDB version that actually runs on the CPU.
- The API can run without keys only when `OPENNASR_API_AUTH=none` is set explicitly; the archiver prunes old published cycles from its cache.

- `opennasr route`, `opennasr serve` and `opennasr fetch` (local mode): the same route resolution and JSON as
  the HTTP API, run from the local cycle cache; see `docs/local-mode.md`.

- New packages in this repository: `contract/` (bucket layout, manifest, bucket clients, reader),
  `archiver/` (publish, backfill, run loop, alerts, CLI) and `api/` (FastAPI service). Route results now
  carry per-point provenance (`RouteResult.waypoints`), ICAO FPL messages can be resolved, and ignored
  speed/level groups are reported as info diagnostics.

- `RouteResolver.resolve(route)` returns a `RouteResult` (points, cycle, structured
  `RouteDiagnostic` list, `complete`). Route problems become diagnostics instead of
  exceptions, and an arrival or departure whose published branches depend on
  runway or airport configuration is flagged `procedure_branches` (where it splits
  and each branch) with only the shared portion included. `path()` is unchanged.

- Departure and arrival procedures were traversed backwards. FAA `DP_RTE` and
  `STAR_RTE` rows are stored in flight order; the resolver reversed them. Checked
  against a full cycle (airport at the first point of 1,021 of 1,024 DP bodies and
  the last point of 1,179 of 1,186 STAR bodies).
- A procedure name shared by several airports (`VIEWS.DEHAN3`) is now narrowed by
  the route's origin and destination airports, using `STAR_APT` and `DP_APT`.
- ICAO lat/lon waypoints (`3800N07730W`, `37S078E`) resolve.
- Each FAA schema declares how `DP_RTE`/`STAR_RTE` rows are ordered (flight order,
  per the FAA layout documents). The built sidecar records it as
  `procedure_order`, and the route resolver refuses a cycle that declares otherwise.

- Download timeouts raised from 2 s to 30 s (pages) / 60 s (archive); downloads over
  2 GiB and extractions over 16 GiB are rejected; plain `pytest` now works.

### Changed

- Query exceptions are transport-neutral and no longer expose protocol status
  metadata.
- Documentation now presents openNASR exclusively as a local Python library.
- Replaced the broad API guide with a task-oriented "Using the library" guide
  covering downloads, the CLI, cache locations, CSV-versus-DuckDB guidance,
  coordinates and boundaries, best practices, and errors.
- The flight-plan example now uses a longer canonical KLAX-to-KDFW route that
  demonstrates the DOTSS2 departure, J74/J72 jet routes, and JOVEM6 arrival.
- Example scripts now expose simple configuration variables near the top
  instead of wrapping their values in command-line argument parsers.
- Read the Docs now provides a dedicated guide and generated API page for each
  major NASR domain type, including its FAA tables, lookup key, relationships,
  and usage example.
- Read the Docs now includes one reference page for each of the 63 operational
  FAA CSV tables, documenting all 1,151 columns with descriptions, formats,
  units, nullability, and representative cycle values.
- Major domain pages now provide collapsed field catalogs for all 53 named
  `FaaRecord` subclasses, making each complex record's complete FAA source
  fields visible without overwhelming the generated class API.

### Removed

- Removed the redundant `ARB`/uppercase `ARTCC` compatibility API and
  `NASR.loadARTCC()`. Use `nasr.artccs.get(identifier)` or
  `nasr.artcc(identifier)` instead. The shared `Boundary` geometry type now
  lives in `openNASR.airspace` and remains available from the package root.

### Added

- Modern airport, STAR, airway, and ARTCC domain objects now provide `plot()`
  convenience methods backed by the shared plotting helpers. Public
  `plot_star()`, `plot_airway()`, and `plot_artcc()` helpers support the same
  axes, projection, legend, and reusable-index options.
- All public plotting helpers now accept `projection="web_mercator"` for
  EPSG:3857-compatible x/y meters suitable for Google Maps overlays. Existing
  geographic and centered nautical-mile output remain available.
- Added runnable airport, ILS, ARTCC, and flight-plan examples with generated
  figures and a dedicated Read the Docs Examples section.
- Added `IlsRecord.plot()` and `plot_ils_localizer()` with an optional standard
  700-foot threshold-width, 2.5-degree half-angle localizer wedge. The wedge
  distance defaults to 20 NM, while the airport overview example uses 1 NM.
- Added `RunwayRecord.plot()` and `plot_runway()` for one surveyed
  threshold-to-threshold runway segment. The ILS example now consists of the
  runway and localizer class plotting calls instead of manual geometry code.

## [1.5.0] - 2026-08-17

### Security

- Nested FAA CSV archives are now validated before extraction and reject
  absolute or path-traversal member paths.
- Importing `openNASR` no longer performs an update check, contacts the network,
  or writes to the user's cache. Update checks and downloads are explicit.

### Fixed

- Airport lookups no longer fail for helipads and other airports with a
  single-token (non-reciprocal) `RWY_ID`, such as `"H1"`; the reciprocal-end
  check now requires two ends only when the ID is actually reciprocal.
- Schema identification (`SchemaCatalog.identify_schema`) now matches a real
  FAA schema-description file's own column spelling instead of the
  data-file's spelling, fixing rejection of otherwise-supported cycles whose
  `CDR`/`FIX_BASE` schema files use FAA's original declared casing.
- `APT_BASE`, `APT_RWY`, `APT_RWY_END`, and `ILS_BASE`/`DME`/`GS`/`MKR` are
  now registered with their real record classes in `TableRegistry` instead
  of falling back to the generic `FaaRecord`.
- `MarkerRecord.call_sign`/`.operating_hours` (which read nonexistent
  `MIL_OPS_CALL`/`MIL_OPS_HRS` columns copied from an unrelated table) were
  replaced with `marker_id_beacon`/`compass_locator_name`, matching
  `ILS_MKR`'s actual FAA columns.
- The legacy `NAVAID(..., inCountry=...)` filter now matches `COUNTRY_CODE`,
  consistent with the modern `NavaidRepository`'s `country` filter (it
  previously matched `COUNTRY_NAME`, silently disagreeing with the modern API).
- Legacy `isAirport`/`isFix`/`isNavaid` and the `Airport`/`FIX`/`NAVAID`
  constructors now resolve identifiers case-insensitively, matching the
  modern repository-based facade.
- `CycleManager.remove()` now returns a `RemovalResult` reporting which
  representations (archive, extracted data) were actually removed, and the
  `opennasr remove` command uses it directly instead of duplicating path
  construction to check existence beforehand.

### Added

- `CycleManager.available_cycles()` and `CycleManager.latest()`.
- `CycleManager.remove()` accepts `archive=`/`extracted=` keywords.
- `CycleManager` is exported from the package root
  (`from openNASR import CycleManager`).
- `opennasr check`/`opennasr download` default to a working `FaaCycleProvider`
  that discovers the current FAA cycle from the real subscription page, and
  the CLI maps failures to typed, documented exit codes.
- `nasr.artccs`/`nasr.artcc(identifier)`: a modern, repository-based ARTCC
  facade (`Artcc`, `ArtccBoundary`, `ArtccRecord`, `ArtccRepository`),
  matching the pattern every other rich-object family already had. Wraps
  the existing boundary geometry directly; the legacy `ARB`/
  `nasr.loadARTCC()`/`nasr.artcc` (singular attribute) path is unchanged.

### Performance

- `AirportRepository` and the generic `RecordRepository` base now build and
  cache a lookup index per table/column instead of rescanning the full
  column on every lookup.
- Added `PlottingIndex` for reuse across plot calls, eliminating repeated table
  scans for airway, procedure, runway, and airport geometry.

### Changed

- Modernized PyPI metadata, package descriptions, and release validation.
- Added automated pull-request CI and a tag-driven PyPI Trusted Publishing
  workflow that builds the distribution once and publishes that exact artifact.
- `NASR(update=True)` now emits a deprecation warning; use the download CLI or
  `CycleManager` for explicit data acquisition.
- `TableRepository` moved to `openNASR/tables.py`;
  `openNASR/repository.py` re-exports it for compatibility.
- **`NASR` now resolves its cycle through `CycleManager` instead of reading
  `Path(__file__).parent`.** `NASR()` accepts the documented `cycle=` and
  `cache_dir=` keyword arguments (`useDate=` is kept as a deprecated alias);
  it resolves the cache directory using the documented
  `cache_dir` -> `OPENNASR_CACHE_DIR` -> platform-default precedence and no
  longer reads or writes inside the installed package.
- **An explicitly requested cycle that is not present in the cache now
  raises `CycleNotFoundError`** naming the requested date, instead of
  silently substituting an earlier cached cycle with only a warning.
- **`NASR` now loads tables lazily.** Constructing `NASR()` no longer reads
  every CSV in the cycle; a table is read only the first time it is
  requested, directly or through a repository. Per-table schema validation
  is deferred the same way, so drift in one table no longer prevents
  constructing `NASR` or using a different, unrelated table.
- Fixed a latent bug (surfaced by the lazy-loading change above):
  `FixRepository`/`NavaidRepository` eagerly loaded `FIX_BASE`/`NAV_BASE` in
  their constructors regardless of whether the caller ever used them.

### Added

- `nasr.maas`/`nasr.maa(identifier)`: rich `Maa` objects for the FAA's
  Miscellaneous Activity Area family (`MAA_BASE`/`MAA_CON`/`MAA_RMK`/
  `MAA_SHP`) — aerobatic practice, glider, hang glider, space launch,
  ultralight, and unmanned-aircraft areas, confirmed from the FAA's own
  `MAA DATA LAYOUT.pdf`. Contacts, remarks, and shape points are ordered by
  their verified FAA keys. `Maa.geometry` returns a Shapely polygon (or
  multipolygon) built from `MAA_SHP`'s ordered points, closing the ring
  since FAA source data leaves it open (unlike `ARB_SEG`), or `None` for
  radius-only areas with no shape rows.
- `openNASR.records.dms_coordinate`: converts an FAA formatted
  `DD-MM-SS.ssssH` coordinate string to decimal degrees, for tables such as
  `MAA_SHP` that publish no `*_DECIMAL` column.
- `nasr.parachute_jump_areas`/`nasr.parachute_jump_area(identifier)`: rich
  `ParachuteJumpArea` objects for `PJA_BASE`/`PJA_CON`. Contacts are ordered
  by `(PJA_ID, FAC_NAME)`, and `ParachuteJumpArea.airport` is an optional
  link (present on only about two thirds of real rows) rather than a
  required relationship.
- `nasr.military_training_routes`/`nasr.military_training_route(identifier)`:
  rich `MilitaryTrainingRoute` objects for all six `MTR_*` tables, keyed by
  `(ROUTE_TYPE_CODE, ROUTE_ID)`. `MilitaryTrainingRoutePointRecord` exposes
  separate `identifier` (`ROUTE_PT_ID`) and `sequence` (`ROUTE_PT_SEQ`)
  properties, matching the FAA's own documentation that `MTR_PT`'s identity
  key and its display order use different columns.

## [1.4.0] - Unreleased

### Added

- Rich ATC, radar, weather, flight-service-station, and location-identifier
  repositories using verified FAA composite keys and child collections.

## [1.3.0] - Unreleased

### Added

- Rich coded-departure, departure-procedure, preferred-route, and STAR
  repositories with composite-key lookup and FAA sequence ordering.

## [1.2.0] - Unreleased

### Added

- Rich airway, holding-pattern, communication-outlet, and frequency APIs with
  ordered airway/remark collections and public repository exports.
- Verified composite-key links from airway points, holding patterns, and
  communication outlets to their matching fix or navaid records.
- Synthetic navigation-network fixtures and coverage checks for both supported
  FAA schema generations.

### Fixed

- Frequency lookups now require their complete serviced-facility context;
  communication and frequency links never rely on display names alone.

## [1.1.0] - Unreleased

### Added

- Airport-linked `ClassAirspace` and `MilitaryOperation` records, repositories,
  and airport relationships using the verified `(SITE_NO, SITE_TYPE_CODE)` key.
- Lossless FAA records with shared typed converters and contextual conversion errors.
- Cycle discovery, caching, archive validation, and update-status handling.
- Airport, Fix, and Navaid repositories with normalized lookups and typed fields.
- ARTCC boundary mappings, multipolygon preservation, and coordinate validation.
- Public API reference, migration guide, and README example validation.

### Changed

- Designated `1.0.0` as the first supported release while retaining the
  pre-release package version until all release blockers are resolved.
- Airport plotting returns its `Figure` and `Axes` and no longer closes all figures
  by default.
- Coordinate helpers expose explicit latitude/longitude ordering and nautical-mile
  projection distances.

### Fixed

- Empty fields and leading-zero identifiers remain unchanged in raw records.
- Ambiguous lookups preserve candidate records without printing to stdout.
- Optional plotting dependencies no longer prevent core package access.
