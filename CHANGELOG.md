# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow Semantic Versioning.

## [Unreleased]

## [1.5.0] - 2026-08-16

### Security

- Nested FAA CSV archives are now validated before extraction and reject
  absolute or path-traversal member paths.

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

### Changed

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
