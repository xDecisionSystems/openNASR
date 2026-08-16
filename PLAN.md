# openNASR Implementation Plan

## Purpose

This document is the implementation specification for coding agents improving
`openNASR`. It is intended to be sufficient context for an agent that has not
seen previous conversations about the project.

The project goal is to provide a dependable Python library for downloading,
caching, loading, querying, and representing FAA National Airspace System
Resources (NASR) 28-day subscription data.

The library must support two complementary workflows:

1. Convenient domain objects for common aviation entities such as airports,
   runways, fixes, navaids, ILS facilities, and ARTCC boundaries.
2. Direct access to the source FAA CSV tables as pandas `DataFrame` objects.

The library is not an operational navigation product. It must clearly preserve
that limitation in its documentation.

## Instructions for coding agents

### Recommended-agent legend

Every task checkbox includes the recommended primary agent. Use these default
configurations unless the task itself documents a stronger requirement:

- **Agent: Sol** — GPT-5.6 Sol, high reasoning, 256K context. Use for schema
  interpretation, architecture, security-sensitive archive handling, complex
  geometry, and release decisions where a subtle error would propagate.
- **Agent: Terra** — GPT-5.6 Terra, high reasoning, 256K context. This is the
  default for implementation, debugging, integration, and tests.
- **Agent: Luna** — GPT-5.6 Luna, medium reasoning, 128K context. Use for
  bounded, mechanical work with an established pattern, especially routine
  configuration, fixtures, documentation, and reporting.

The named agent owns implementation and focused verification for that task.
Use Sol for a follow-up review when a Terra or Luna task reveals an unresolved
schema, security, geometry, or public-API design question. Start a fresh agent
session for each task and provide only the relevant milestone plus referenced
architecture and naming sections; the agent must still read the complete plan
before editing.

Before changing code:

1. Read this entire file, `README.md`, `pyproject.toml` or `setup.py`, and every
   source file affected by the task.
2. Inspect `git status` and preserve unrelated user changes.
3. Do not add FAA archives, extracted subscription files, generated figures,
   caches, credentials, or virtual environments to Git.
4. Work on the earliest incomplete milestone unless the user explicitly
   requests a different milestone. Milestones are numbered in the order
   they should be attempted, including lettered milestones (e.g. `1B` runs
   after `1` and before `2`).
5. Within a milestone, tasks are numbered (e.g. `1.3`, `1B.6`) and each is
   sized to be one reviewable change. Prefer completing and testing one
   numbered task at a time over batching several into one commit, unless
   two tasks are trivial and tightly coupled (e.g. adding a dataclass field
   and the one test that reads it).
6. Keep each change narrowly scoped and leave the repository in a testable
   state.
7. Add or update tests for every behavior change and regression fix.
8. Update this plan's checkboxes and decision log when a task changes the
   implementation state or an architectural decision.
9. Update the README whenever the public API, installation process, data
   location, or supported behavior changes.

Before reporting completion:

1. Run the relevant focused tests.
2. Run the complete test suite when dependencies and time permit.
3. Run formatting, linting, type checking, and package-build validation after
   those tools are introduced.
4. Report the commands run, their results, and any checks that could not run.
5. Report remaining known limitations without claiming unfinished work is
   complete.

Do not silently redesign public interfaces. When a breaking change is needed,
add a compatibility path and a deprecation notice unless this plan explicitly
authorizes the break.

## Current repository state

At the time this plan was written:

- The package source is under `openNASR/`. The prior top-level `nasr/`
  package tree has already been deleted from the working tree (visible in
  `git status` as deletions) in favor of `openNASR/`. This rename is
  intentional and complete; do not restore `nasr/`. Any remaining reference
  to the old `nasr` package name in source, tests, or docs (see
  `openNASR/flightplan.py` below) is a leftover defect, not evidence the
  migration is incomplete.
- The public exports are `NASR`, `Airport`, `ARB`, `FIX`, and `NAVAID`.
- `NASR` eagerly loads all CSV files from a locally stored ZIP cycle.
- Data is expected inside the installed source tree under
  `openNASR/data/zip/` and `openNASR/data/uncompressed/`.
- Automatic downloading is not implemented.
- The existing `main_test_*.py` files are executable examples, not automated
  pytest tests.
- `setup.py` is the active packaging configuration.

Known defects that must be treated as regressions, not desired behavior:

- `RawDict` calls an undefined `getRecords()` function.
- NAVAID criteria are combined with OR instead of narrowing the identifier
  match, and the selected filtered record is discarded.
- `preloadAll=True` calls an obsolete `ARB` constructor and then a nonexistent
  `loadAirports()` method.
- `openNASR.flightplan` retains imports and names from the old `nasr` package.
- Several code paths raise strings, which produces `TypeError` in Python 3.
- Missing local cycles cause unhelpful `IndexError` failures.
- Supplying an exact cycle date currently selects a previous cycle because the
  comparison uses `<` instead of `<=`.
- `Raw.__getattr__` refers to an undefined `_attributes` member.
- Collection methods refer to undefined `_map` and `_raw` members.
- Source files contain inconsistent naming, formatting, and type conventions.

## Product requirements

### Required workflows

The completed API should support the following:

```python
from openNASR import NASR

nasr = NASR()                         # newest cached cycle
nasr = NASR(cycle="2026-08-06")      # exact cached cycle
nasr = NASR(cache_dir="/data/nasr")  # caller-controlled cache

print(nasr.cycle)
print(nasr.available_tables)
print(nasr.table("APT_BASE").head())

airport = nasr.airports.get("KBWI")
maryland_airports = nasr.airports.find(state="MD")
airport = nasr.airport("KBWI")
fix = nasr.fix("AABEE")
navaid = nasr.navaid("AI", state="IN")
artcc = nasr.artcc("ZOB")
```

Downloading should be explicit and testable:

```python
from openNASR import CycleManager

cycles = CycleManager()
cycles.download("2026-08-06")
cycles.download_latest()
print(cycles.available_cycles())
```

The legacy construction style should continue to work during the compatibility
period:

```python
from openNASR import Airport, FIX, NAVAID

airport = Airport("BWI", nasr)
fix = FIX("AABEE", nasr)
navaid = NAVAID("ABR", nasr)
```

### Behavioral requirements

- Cycle dates use ISO `YYYY-MM-DD` strings at API boundaries and `date` objects
  internally.
- An explicitly requested cycle means an exact cycle. It must never silently
  select a different date.
- `NASR()` with no cycle selects the newest valid cached cycle.
- If no cycle is cached, the error must explain how to download or import one.
- Importing `openNASR` performs a metadata-only network check for a newer FAA
  NASR cycle and displays a user-facing message when one is available.
- Importing never downloads a cycle archive. `CycleManager.download()` and
  `CycleManager.download_latest()` are the only automatic-download entry points
  and must be called explicitly.
- Import-time update-check failures are silent and must never prevent package
  import. Network, timeout, TLS, DNS, response-parsing, and update-cache errors
  are available only through diagnostic logging or an explicitly invoked check
  method.
- Successful update-check results are cached outside the installed package for
  24 hours. Failed checks must not overwrite the last successful result and
  must not be represented as successful cache entries.
- `CycleManager.check_for_updates(force=True)` bypasses the 24-hour cache and
  performs an immediate metadata check.
- Constructing `NASR` performs no additional network access.
- Tables are loaded lazily and cached within the `NASR` instance.
- Missing tables produce a typed exception that includes the table and cycle.
- Entity identifiers are stripped and normalized to uppercase.
- Duplicate identifiers are never resolved by arbitrary row order.
- Optional filters narrow a lookup using logical AND.
- The original source row remains accessible from every domain object.
- Raw tables and records preserve the exact FAA CSV text; typed conversion occurs
  only in rich-object properties.
- Public failures use typed exceptions rather than `print()` plus sentinel
  values.
- Plotting must not mutate global Matplotlib state unnecessarily.
- Geometry functions must document coordinate order and units.

## Architectural decisions

These decisions should be followed unless repository evidence requires a
change. Record any change in the decision log.

### Package layout

Target layout:

```text
openNASR/
    __init__.py
    client.py              # NASR facade and domain lookup methods
    nasr.py                # compatibility forwarding module for client.py
    cycles.py              # cycle discovery, import, download, extraction
    tables.py              # lazy CSV table repository and indexes
    schemas.py             # supported-schema manifests and validation
    registry.py            # table, identity, ordering, and relationship specs
    records.py             # lossless raw records and typed converters
    indexes.py             # lazy repository indexes
    exceptions.py          # public exception hierarchy
    coordinates.py         # projection helpers and unit documentation
    airport.py
    runway.py
    ils.py
    fix.py
    navaid.py
    airspace.py
    airway.py
    routes.py
    atc.py
    weather.py
    communications.py
    fss.py
    holding.py
    locations.py
    military.py
    plotting.py            # optional plotting helpers, when extracted
    cli.py                 # opennasr data-management command
```

The existing filenames may be migrated incrementally. Do not perform a large
file move in the same commit as behavioral changes unless tests make the move
safe.

### Data location

Default data must live outside the installed package. Use `platformdirs` to
resolve a user cache directory, with the application name `openNASR`.

Recommended structure:

```text
<cache>/openNASR/
    archives/
        28DaySubscription_Effective_2026-08-06.zip
    cycles/
        2026-08-06/
            csv/
                APT_BASE.csv
                NAV_BASE.csv
                ...
            metadata.json
    downloads/
        temporary partial files
```

The cache root can be overridden by:

1. An explicit `cache_dir` argument.
2. `OPENNASR_CACHE_DIR`.
3. The platform-specific default.

Do not use the package directory as a writable runtime location.

### Data ownership and licensing

- Do not bundle full FAA cycles in wheels or source distributions.
- Test fixtures must be small and purpose-built.
- Preserve FAA-provided field names in raw tables.
- Record the cycle date, original archive filename, source URL, import time,
  archive size, and SHA-256 digest in `metadata.json`.
- Retain the aviation-use disclaimer in user-facing documentation.

### Dependencies

Core dependencies:

- `pandas`
- `numpy`
- `shapely`
- `platformdirs`

Optional dependencies:

- `matplotlib` in a `plot` extra
- development and test tools in a `dev` extra

Prefer the Python standard library for HTTP downloads initially. Network code
must accept an injected opener or transport so tests never require live FAA
access.

### Public naming

New class names use standard Python capitalization:

- `Fix`
- `Navaid`
- `Artcc`
- `ArtccBoundary`

Keep compatibility aliases `FIX`, `NAVAID`, and `ARB`, the legacy constructors,
and forwarding modules throughout `1.x`. They may be removed no earlier than
`2.0.0`, after documented deprecation warnings and migration guidance.

### Exception hierarchy

Create the following public exceptions:

```python
class OpenNASRError(Exception): ...
class ConfigurationError(OpenNASRError): ...
class CycleNotFoundError(OpenNASRError): ...
class DownloadError(OpenNASRError): ...
class ArchiveError(OpenNASRError): ...
class TableNotFoundError(OpenNASRError): ...
class SchemaMismatchError(OpenNASRError): ...
class FieldConversionError(OpenNASRError): ...
class RecordNotFoundError(OpenNASRError): ...
class AmbiguousRecordError(OpenNASRError): ...
class InvalidGeometryError(OpenNASRError): ...
```

Exceptions must carry useful structured context where applicable, such as
`cycle`, `table`, `identifier`, and lookup filters.

## Complete FAA CSV coverage plan

This section defines how every CSV in the supported NASR schema generations is
loaded and represented. `FILESTYPES.md` is authoritative for approved Python
module, class, repository, and convenience-method names; this plan is
authoritative for implementation order and acceptance criteria.

The supported 2026 FAA packages contain 87 CSV files:

- 63 operational data tables;
- 24 `*_CSV_DATA_STRUCTURE` files describing table columns.

The earlier 65-table/89-file planning inventory included `AWY_ALT` and
`AWY_SEG`, which are absent from both official supported packages. Their data
is represented by `AWY_SEG_ALT`; they are not part of the compatibility
contract. The registry must use the two checked-in official schema manifests:

1. `pre_2026_09`, derived from the FAA cycle effective August 6, 2026;
2. `nasr_2026_09`, derived from the FAA test/subscription files effective
   September 3, 2026.

If either supported manifest adds, removes, or renames tables, update the
coverage counts and matrix rather than forcing the 2024 totals to remain true.

Coverage has three layers. A table is not considered fully supported merely
because pandas can read it.

1. **Raw coverage:** the table is discoverable and loadable as a DataFrame.
2. **Record coverage:** each row can be represented by a named, typed record
   class with raw-field access.
3. **Domain coverage:** related tables can be joined through an aggregate or
   repository API using documented keys.

Every operational table must reach all three layers. Tables without a reliable
parent relationship receive standalone rich objects and repositories rather
than speculative joins. Schema-description tables require raw and schema-model
coverage, but not aviation domain aggregates.

### Relationship to the initial 1.0.0 release

Full three-layer coverage of every supported operational table is **not**
required for the initial `1.0.0` release. It is a longer-running objective that continues
past `1.0.0`. The Milestone 7 release acceptance criteria are authoritative
for what `1.0.0` actually requires; if this section and Milestone 7 ever
disagree, Milestone 7 wins and this section should be corrected to match.

Required for `1.0.0` (see Milestone 1B for the explicit mapping):

- **Raw coverage for all tables**, including every table with no record class
  yet. Nothing may be silently dropped or require an unrelated table to be
  present.
- **Record and domain coverage** only for the families already exposed by the
  legacy API: airports (`APT_*`), runways, ILS (`ILS_*`), fixes (`FIX_*`),
  navaids (`NAV_*`), and ARTCC boundaries (`ARB_*`).
- **Both supported schema generations:** the current FAA schema and the format
  effective September 3, 2026 must pass strict schema validation and their
  versioned manifests must be tested.
- **Cycle management:** external caching, explicit exact/latest downloads,
  safe extraction, metadata, and import-time update notification must work.
- **Command-line management:** `opennasr check`, `download`, `list`, and
  `remove` must be installed, documented, and tested.
- **Release quality:** fixture-based automated tests, documentation, wheel and
  sdist validation, linting, type checking, and CI must pass.

Scheduled after `1.0.0` in numbered `1.x` milestones:

- Record and domain coverage for every other family in the matrix below
  (`atc.py`, `weather.py`, `airway.py`, `routes.py`, `communications.py`,
  `fss.py`, `holding.py`, `locations.py`, `military.py`, `CLS_ARSP`, `MAA_*`,
  `PJA_*`).

Milestones 8-12 own this follow-on work. An agent proceeds through them in order
without requiring another user request.

### Files required for complete coverage

Create these infrastructure modules before implementing all domain classes:

```text
openNASR/
    client.py              # NASR facade and domain repository access
    cycles.py              # archive, cache, cycle, and extraction handling
    tables.py              # lazy DataFrame loading
    schemas.py             # FAA schema-file parsing and validation
    registry.py            # complete table-to-record/keys/relationship registry
    records.py             # common immutable record behavior
    indexes.py             # reusable lazy single- and multi-column indexes
    exceptions.py          # public typed errors
```

Create or normalize these domain modules:

```text
openNASR/
    airport.py             # APT_* records and Airport aggregate
    airspace.py            # ARB_*, CLS_ARSP, MAA_*, and PJA_*
    atc.py                 # ATC_* and RDR
    weather.py             # AWOS and WXL_*
    airway.py              # AWY_*
    routes.py              # CDR, DP_*, PFR_*, and STAR_*
    fix.py                 # FIX_*
    communications.py      # COM and FRQ
    fss.py                 # FSS_*
    holding.py             # HPF_*
    ils.py                 # ILS_*
    locations.py           # LID
    military.py            # MIL_OPS and MTR_*
    navaid.py              # NAV_*
```

Canonical ownership follows `FILESTYPES.md`: runway types live in `runway.py`,
departure/STAR/preferred-route types live in `routes.py`, and `NASR` lives in
`client.py`. Compatibility forwarding modules retain `nasr.py`, `arb.py`,
`nav.py`, `rwy.py`, `departure.py`, and `cfcn.py` through `1.x`. Do not keep
duplicate implementations in both old and new files.

### Core metadata classes

Implement these classes before table-specific models:

```python
@dataclass(frozen=True)
class ColumnSchema:
    name: str
    faa_type: str
    max_length: str | None
    nullable: bool

@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: tuple[ColumnSchema, ...]

@dataclass(frozen=True)
class TableVariantSpec:
    schema_id: str
    identity_key: tuple[str, ...] | None
    indexes: tuple[IndexSpec, ...]
    order_by: tuple[str, ...]
    relationships: tuple[RelationshipSpec, ...]
    required_columns: frozenset[str]
    optional: bool = False

@dataclass(frozen=True)
class TableSpec:
    name: str
    record_type: type[FaaRecord]
    variants: tuple[TableVariantSpec, ...]

class SchemaCatalog:
    def identify_schema(cycle_path: Path) -> str: ...
    def table(name: str, schema_id: str) -> TableSchema: ...
    def validate(name: str, frame: DataFrame, schema_id: str) -> ValidationReport: ...

class TableRegistry:
    def spec(name: str, schema_id: str) -> TableVariantSpec: ...
    def table(name: str) -> TableSpec: ...
    def supported_tables() -> frozenset[str]: ...
    def unmodeled_tables(available: Iterable[str]) -> frozenset[str]: ...

class FaaRecord(Mapping[str, object]):
    @property
    def raw(self) -> Mapping[str, object]: ...
    def as_dict(self) -> dict[str, object]: ...
```

`FaaRecord` must preserve FAA column names and values. Typed properties are a
convenience layer; they must not discard columns that lack explicit properties.
Do not dynamically create Python source files from a user's downloaded data at
runtime. Registry and model source changes remain reviewed code.

`TableRegistry.spec(name, schema_id)` selects the matching variant. No table is
assumed to have a primary key merely because one combination is
unique in a sample cycle. `identity_key=None` is valid for row collections with
no documented stable identity. Identity, lookup indexes, ordering fields, and
relationship join keys are separate concepts. Accept an identity or join key
only after it is supported by FAA documentation or validated against both
supported schema generations and representative data.

The raw layer must read values losslessly as strings, preserve leading zeros,
and retain empty CSV fields as empty strings. The typed layer must use shared,
tested converters for nullable strings, dates, integers, decimal values,
booleans/codes, coordinates, and enums. A nullable typed property converts an
empty raw field to `None`; it must not mutate the raw record. Invalid non-empty
values raise `FieldConversionError` containing the cycle, table, column, raw
value, record identity when available, and expected Python type.

### Generic loading contract for every CSV

`TableRepository` must:

- discover every immediate `*.csv` file in the normalized cycle CSV directory;
- use the filename stem as the canonical uppercase table name;
- expose all tables through `nasr.table(name)` and `nasr[name]`;
- lazily read a table only when requested;
- read every raw column as text using a centralized pandas policy equivalent to
  `dtype=str`, `keep_default_na=False`, and `na_filter=False`, unless fixture
  tests demonstrate a necessary adjustment that still preserves source text;
- preserve leading zeros and empty strings in every raw table;
- perform no automatic numeric or date conversion in the raw layer;
- cache loaded DataFrames per cycle and per `NASR` instance;
- load `*_CSV_DATA_STRUCTURE` tables into `SchemaCatalog`;
- compare actual columns and FAA-declared schema types with the versioned
  supported manifest;
- stop normal loading with `SchemaMismatchError` when a known table has missing
  required columns, unexpected columns, or an incompatible FAA-declared type;
- stop normal loading with `SchemaMismatchError` when an unknown future FAA
  table appears without a registry entry;
- provide an explicit diagnostic inspection mode that permits raw access to
  unfamiliar tables and columns solely for investigating and implementing the
  new schema;
- report unknown tables through `unmodeled_tables` so new coverage cannot be
  overlooked;
- never require all tables to be present merely to use one unrelated domain.

Add a `LoadPolicy` or equivalent configuration for pandas parsing. It should be
derived from `TableSchema`, covered by tests, and centralized rather than
repeated in each domain module.

Structural schema validation never compares pandas dtypes: raw DataFrames are
intentionally string-valued. It compares table names, column names,
nullability/length metadata where relevant, and FAA-declared types against the
selected supported manifest. Rich-property converters validate non-empty field
values on access and raise `FieldConversionError`. The CLI's validation command
may offer a deep scan that runs every registered converter without changing the
raw data.

### Complete operational-table class matrix

The following matrix assigns the 63 operational CSV tables present in both
supported 2026 inventories. `FILESTYPES.md` contains the approved names.

| Module | CSV table | Record class | Aggregate or relationship |
| --- | --- | --- | --- |
| `airport.py` | `APT_BASE` | `AirportRecord` | `Airport` base record |
| `airport.py` | `APT_ARS` | `AirportArrestingSystemRecord` | `Airport.arresting_systems`, keyed by airport/runway end |
| `airport.py` | `APT_ATT` | `AirportAttendanceRecord` | `Airport.attendance_schedules` |
| `airport.py` | `APT_CON` | `AirportContactRecord` | `Airport.contacts` |
| `airport.py` | `APT_RMK` | `AirportRemarkRecord` | `Airport.remarks` |
| `runway.py` | `APT_RWY` | `RunwayRecord` | `Airport.runways` and `Runway` |
| `runway.py` | `APT_RWY_END` | `RunwayEndRecord` | `Runway.ends` and `Airport.runway_ends` |
| `airspace.py` | `ARB_BASE` | `ArtccRecord` | `Artcc` base record |
| `airspace.py` | `ARB_SEG` | `ArtccBoundarySegmentRecord` | `Artcc.boundaries` grouped by type and altitude |
| `airspace.py` | `CLS_ARSP` | `ClassAirspaceRecord` | linked to `Airport` by airport/site identifiers |
| `airspace.py` | `MAA_BASE` | `MaaRecord` | `Maa` base record; retain FAA acronym until official expansion is verified |
| `airspace.py` | `MAA_CON` | `MaaContactRecord` | `Maa.contacts` |
| `airspace.py` | `MAA_RMK` | `MaaRemarkRecord` | `Maa.remarks` |
| `airspace.py` | `MAA_SHP` | `MaaShapePointRecord` | ordered geometry used by `Maa.geometry` |
| `airspace.py` | `PJA_BASE` | `ParachuteJumpAreaRecord` | `ParachuteJumpArea` base record |
| `airspace.py` | `PJA_CON` | `ParachuteJumpAreaContactRecord` | `ParachuteJumpArea.contacts` |
| `atc.py` | `ATC_BASE` | `AtcFacilityRecord` | `AtcFacility` base record |
| `atc.py` | `ATC_ATIS` | `AtisRecord` | `AtcFacility.atis_services` |
| `atc.py` | `ATC_RMK` | `AtcRemarkRecord` | `AtcFacility.remarks` |
| `atc.py` | `ATC_SVC` | `AtcServiceRecord` | `AtcFacility.services` |
| `atc.py` | `RDR` | `RadarRecord` | standalone `Radar` linked to a facility when keys permit |
| `weather.py` | `AWOS` | `AutomatedWeatherStationRecord` | standalone `AutomatedWeatherStation`, linkable to navaid/airport fields |
| `weather.py` | `WXL_BASE` | `WeatherLocationRecord` | `WeatherLocation` base record |
| `weather.py` | `WXL_SVC` | `WeatherServiceRecord` | `WeatherLocation.services` |
| `airway.py` | `AWY_BASE` | `AirwayRecord` | `Airway` base record |
| `airway.py` | `AWY_SEG_ALT` | `AirwaySegmentRecord` | ordered `Airway.segments`, including altitude constraints |
| `routes.py` | `CDR` | `CodedDepartureRouteRecord` | standalone `CodedDepartureRoute` |
| `routes.py` | `DP_BASE` | `DepartureProcedureRecord` | `DepartureProcedure` base record |
| `routes.py` | `DP_APT` | `DepartureAirportRecord` | `DepartureProcedure.airports` |
| `routes.py` | `DP_RTE` | `DepartureRouteRecord` | ordered `DepartureProcedure.routes` |
| `routes.py` | `PFR_BASE` | `PreferredRouteRecord` | `PreferredRoute` base record |
| `routes.py` | `PFR_RMT_FMT` | `PreferredRouteFormatRecord` | `PreferredRoute.formats` |
| `routes.py` | `PFR_SEG` | `PreferredRouteSegmentRecord` | ordered `PreferredRoute.segments` |
| `routes.py` | `STAR_BASE` | `StarProcedureRecord` | `StarProcedure` base record |
| `routes.py` | `STAR_APT` | `StarAirportRecord` | `StarProcedure.airports` |
| `routes.py` | `STAR_RTE` | `StarRouteRecord` | ordered `StarProcedure.routes` |
| `fix.py` | `FIX_BASE` | `FixRecord` | `Fix` base record |
| `fix.py` | `FIX_CHRT` | `FixChartRecord` | `Fix.charts` |
| `fix.py` | `FIX_NAV` | `FixNavaidRecord` | `Fix.navaids` association records |
| `communications.py` | `COM` | `CommunicationOutletRecord` | standalone `CommunicationOutlet` |
| `communications.py` | `FRQ` | `FrequencyRecord` | standalone `Frequency`; queryable by serviced facility |
| `fss.py` | `FSS_BASE` | `FlightServiceStationRecord` | `FlightServiceStation` base record |
| `fss.py` | `FSS_RMK` | `FlightServiceStationRemarkRecord` | `FlightServiceStation.remarks` |
| `holding.py` | `HPF_BASE` | `HoldingPatternRecord` | `HoldingPattern` base record |
| `holding.py` | `HPF_CHRT` | `HoldingPatternChartRecord` | `HoldingPattern.charts` |
| `holding.py` | `HPF_RMK` | `HoldingPatternRemarkRecord` | `HoldingPattern.remarks` |
| `holding.py` | `HPF_SPD_ALT` | `HoldingPatternSpeedAltitudeRecord` | `HoldingPattern.speed_altitude_limits` |
| `ils.py` | `ILS_BASE` | `IlsRecord` | `InstrumentLandingSystem` base record |
| `ils.py` | `ILS_DME` | `IlsDmeRecord` | `InstrumentLandingSystem.dme` |
| `ils.py` | `ILS_GS` | `IlsGlideSlopeRecord` | `InstrumentLandingSystem.glide_slope` |
| `ils.py` | `ILS_MKR` | `IlsMarkerRecord` | `InstrumentLandingSystem.markers` |
| `ils.py` | `ILS_RMK` | `IlsRemarkRecord` | `InstrumentLandingSystem.remarks` |
| `locations.py` | `LID` | `LocationIdentifierRecord` | standalone `LocationIdentifier` registry entry |
| `military.py` | `MIL_OPS` | `MilitaryOperationRecord` | linked to `Airport` by airport/site identifiers |
| `military.py` | `MTR_BASE` | `MilitaryTrainingRouteRecord` | `MilitaryTrainingRoute` base record |
| `military.py` | `MTR_AGY` | `MilitaryTrainingRouteAgencyRecord` | `MilitaryTrainingRoute.agencies` |
| `military.py` | `MTR_PT` | `MilitaryTrainingRoutePointRecord` | ordered `MilitaryTrainingRoute.points` |
| `military.py` | `MTR_SOP` | `MilitaryTrainingRouteProcedureRecord` | `MilitaryTrainingRoute.procedures` |
| `military.py` | `MTR_TERR` | `MilitaryTrainingRouteTerrainRecord` | `MilitaryTrainingRoute.terrain` |
| `military.py` | `MTR_WDTH` | `MilitaryTrainingRouteWidthRecord` | `MilitaryTrainingRoute.widths` |
| `navaid.py` | `NAV_BASE` | `NavaidRecord` | `Navaid` base record |
| `navaid.py` | `NAV_CKPT` | `NavaidCheckpointRecord` | `Navaid.checkpoints` |
| `navaid.py` | `NAV_RMK` | `NavaidRemarkRecord` | `Navaid.remarks` |

Before implementing a relationship, inspect the corresponding
`*_CSV_DATA_STRUCTURE.csv` and representative rows to establish the full
composite key. Do not join on a short identifier alone when the schema also
requires type, region, country, sequence, site number, or runway end.

### Schema-description table coverage

The following 24 files must be parsed through `SchemaCatalog` and must remain
available through raw table access:

```text
APT_CSV_DATA_STRUCTURE
ARB_CSV_DATA_STRUCTURE
ATC_CSV_DATA_STRUCTURE
AWOS_CSV_DATA_STRUCTURE
AWY_CSV_DATA_STRUCTURE
CDR_CSV_DATA_STRUCTURE
CLS_ARSP_CSV_DATA_STRUCTURE
COM_CSV_DATA_STRUCTURE
DP_CSV_DATA_STRUCTURE
FIX_CSV_DATA_STRUCTURE
FRQ_CSV_DATA_STRUCTURE
FSS_CSV_DATA_STRUCTURE
HPF_CSV_DATA_STRUCTURE
ILS_CSV_DATA_STRUCTURE
LID_CSV_DATA_STRUCTURE
MAA_CSV_DATA_STRUCTURE
MIL_OPS_CSV_DATA_STRUCTURE
MTR_CSV_DATA_STRUCTURE
NAV_CSV_DATA_STRUCTURE
PFR_CSV_DATA_STRUCTURE
PJA_CSV_DATA_STRUCTURE
RDR_CSV_DATA_STRUCTURE
STAR_CSV_DATA_STRUCTURE
WXL_CSV_DATA_STRUCTURE
```

Each schema file can describe multiple operational tables. `SchemaCatalog`
must group rows by the `CSV File` column and expose the correct `TableSchema`
for each table.

### Repository and aggregate access

Every domain module should expose a repository responsible for lookup and
relationship assembly. Domain objects must not scan DataFrames themselves.

Target examples:

```python
nasr.airports.get("KBWI")
nasr.airports.find(state="MD")
nasr.airways.get("V1")
nasr.atc_facilities.get("DCA")
nasr.departures.get("TERPZ7")
nasr.fixes.get("AABEE")
nasr.holding_patterns.find(fix_id="AABEE")
nasr.military_training_routes.get("IR012")
nasr.navaids.get("AI", state="IN")
nasr.stars.get("FROGZ4")
nasr.weather_locations.get("BWI")
```

All repositories should share a small generic base that provides:

- identifier normalization;
- lazy index creation;
- exact single-record lookup;
- filtered multi-record search;
- typed not-found and ambiguity errors;
- composite-key lookup;
- stable ordering for result sequences;
- access to the underlying table for advanced queries.

Every operational table must participate in the rich domain API. Tables such as
`CDR`, `COM`, `FRQ`, `LID`, and `RDR` that do not have a dependable parent
relationship must receive standalone rich objects and repositories. Add
cross-object relationships only where FAA keys or documentation establish a
sound join; rich behavior must not depend on speculative associations.

### Relationship implementation order

Implement complete CSV coverage in vertical slices so each merge remains
reviewable. Each slice below is mapped to the milestone that owns it so an
agent does not have to guess where this work belongs in the numbered
sequence. Slice 1 is required for `1.0.0` (Milestone 1B). Slices 2-6 are owned
by Milestones 8-12 and ship through the numbered `1.x` releases defined below.

1. **Inventory and schema layer** — owned by **Milestone 1B**, required for
   `1.0.0`.
   - load every CSV listed by either supported manifest lazily;
   - parse every schema-description file in both generations;
   - register every supported operational table;
   - produce a machine-readable coverage report.
2. **Airport and landing systems** — core `APT_*`/`ILS_*` work lands in
   Milestone 5; airport-linked `MIL_OPS` and `CLS_ARSP` land in Milestone 8.
   - `APT_*`, `ILS_*`, `MIL_OPS`, and `CLS_ARSP`;
   - validate airport, site, runway, and runway-end composite keys.
3. **Navigation network** — Milestone 9, extending fix/navaid coverage from
   Milestone 5.
   - `FIX_*`, `NAV_*`, `AWY_*`, `HPF_*`, `COM`, and `FRQ`;
   - support associations without recursively loading unrelated tables.
4. **Procedures and preferred routes** — Milestone 10 (`routes.py`).
   - `DP_*`, `STAR_*`, `PFR_*`, and `CDR`;
   - preserve FAA segment and sequence ordering.
5. **Facilities and weather** — Milestone 11 (`atc.py`, `fss.py`,
   `weather.py`, `locations.py`).
   - `ATC_*`, `FSS_*`, `RDR`, `AWOS`, `WXL_*`, and `LID`.
6. **Airspace and military activity** — Milestone 12, extending ARTCC coverage
   from Milestone 5 and adding `MAA_*`, `PJA_*`, and `MTR_*`.
   - `ARB_*`, `MAA_*`, `PJA_*`, and `MTR_*`;
   - build geometry only after record ordering and multipart semantics are
     verified from FAA schema documentation and representative cycles.

Each slice must include record classes, repository methods, relationships,
fixtures, tests, public exports, and documentation before starting the next.

### Complete-coverage tests

Use the two checked-in versioned manifests from Milestone 0B. Tests must verify:

- [ ] **Agent: Terra.** every filename in each supported manifest is discovered;
- [x] **Agent: Sol.** every schema-description file in both generations is parsed;
- [x] **Agent: Sol.** every operational table in either manifest has exactly one
      schema-version-aware `TableSpec`;
- [ ] **Agent: Terra.** every `TableSpec.record_type` subclasses `FaaRecord`;
- [x] **Agent: Sol.** every registered required column exists in the schema description;
- [x] **Agent: Sol.** every composite key column exists in its table;
- [x] **Agent: Sol.** every declared relationship references columns on both sides;
- [ ] **Agent: Terra.** every table loads independently from the minimal fixture cycle;
- [ ] **Agent: Terra.** at least one record can be constructed for every operational table;
- [ ] **Agent: Terra.** every aggregate loads its child tables only when the relationship is
      requested;
- [x] **Agent: Sol.** an unknown extra CSV raises `SchemaMismatchError` during normal loading,
      is reported as unmodeled, and remains available through raw access only
      in explicit diagnostic inspection mode;
- [ ] **Agent: Terra.** a missing optional table affects only its related optional property;
- [ ] **Agent: Terra.** a missing required base table raises `TableNotFoundError`;
- [ ] **Agent: Terra.** identifiers containing leading zeros remain strings;
- [ ] **Agent: Terra.** nulls do not change identifier types;
- [ ] **Agent: Terra.** route, point, boundary, and remark ordering is deterministic;
- [ ] **Agent: Terra.** the coverage test fails when a known table is removed from the registry.

Create narrow fixture rows for all tables rather than copying a complete FAA
cycle. A fixture-builder utility may generate rows from schema definitions, but
key fields and relationship values must be explicitly authored so tests verify
real joins rather than only successful parsing.

### Definition of complete CSV support

The "load all FAA CSV data" objective is complete only when:

- all CSV files in a cycle are discoverable and lazily loadable;
- all schema-description files contribute to validation;
- every operational table in either supported manifest has an approved record
  class and rich object or rich child collection;
- every table has a repository or a documented aggregate relationship;
- all record classes preserve the full source row;
- cross-table joins use tested composite keys;
- unknown future tables fail strict loading and remain inspectable as raw
  DataFrames only in explicit diagnostic mode;
- the generated coverage report has no unmodeled reference tables;
- the default automated test suite needs neither network access nor a full FAA
  cycle;
- the README documents both raw access and every supported domain family.

## Milestone 0: Establish a reproducible baseline

Goal: make the project installable and ensure future agents can run consistent
quality checks.

Ruff and mypy are **configured but not enforced as a gate** in this
milestone. Milestones 1-6 rewrite most of the source tree; running strict
lint/type checks against code that is about to be replaced wastes agent time
on churn. Enforcement (making `ruff check` and `mypy` required, non-warning
steps in the verification commands and in CI) moves to Milestone 7, Task
7.10 below, once the rewrite is substantially done. Until then, run them
informationally only (`--exit-zero` for Ruff, no CI gate for mypy) so
warnings are visible without blocking milestone progress.

Tasks:

- [x] **Agent: Terra.** **0.1** Record the minimum supported Python version. Default to Python
      3.10 unless compatibility evidence requires another version. Add it as
      `requires-python = ">=3.10"` once `pyproject.toml` exists (Task 0.2).
- [x] **Agent: Luna.** **0.2** Create `pyproject.toml` with a `[build-system]` table using
      `setuptools` and `setuptools.build_meta` as the build backend.
- [x] **Agent: Luna.** **0.3** Move package metadata (`name`, `version`, `authors`,
      `description`, `readme`, `license`, `keywords`, `urls`) from `setup.py`
      into `pyproject.toml`'s `[project]` table. Preserve the existing values
      (name `openNASR`, author Adan E Vela, GPLv3 license) rather than
      inventing new ones.
- [x] **Agent: Terra.** **0.4** Move `install_requires` from `setup.py` into
      `pyproject.toml`'s `[project.dependencies]`. Core runtime dependencies
      are `pandas`, `numpy`, `shapely` (per the "Dependencies" section
      above; `platformdirs` is added in Milestone 3 when it is first used,
      not here). Drop the `dependency_links` entry pointing at
      `pypi.adc-ucf.com` — it is marked "probably should be removed" in the
      current `setup.py` and is not a general-purpose index.
- [x] **Agent: Luna.** **0.5** Add an optional `plot` dependency group in
      `[project.optional-dependencies]` containing `matplotlib`.
- [x] **Agent: Luna.** **0.6** Add an optional `dev` dependency group in
      `[project.optional-dependencies]` containing `pytest`, `ruff`, and
      `mypy`.
- [x] **Agent: Terra.** **0.7** Reduce `setup.py` to the minimum shim needed for editable
      installs on the target setuptools version, or remove it entirely if
      `pyproject.toml` alone supports `pip install -e .` in CI. Verify
      whichever choice is made against the Python/setuptools version pinned
      in Task 0.1.
- [x] **Agent: Luna.** **0.8** Add a `[tool.pytest.ini_options]` table (or `pytest.ini`) with
      `testpaths = ["tests"]`.
- [x] **Agent: Terra.** **0.9** Add a `[tool.ruff]` configuration table covering formatting and
      linting. Do not enable strict/pedantic rule sets that will mostly fire
      on soon-to-be-rewritten Milestone-1-6 code; start with a conservative
      default rule set (e.g. Ruff's default `E`, `F`) and widen it in
      Milestone 7.
- [x] **Agent: Terra.** **0.10** Add a `[tool.mypy]` configuration with a conservative starting
      point (e.g. `ignore_missing_imports = true`, gradual typing rather than
      `strict = true`). Strict mode is a Milestone 7 decision, not this one.
- [x] **Agent: Luna.** **0.11** Add `.gitignore` entries for: pytest cache (`.pytest_cache/`),
      mypy cache (`.mypy_cache/`), build artifacts (`build/`, `dist/`,
      `*.egg-info/`), and local NASR data artifacts
      (`openNASR/data/zip/*.zip`, `openNASR/data/uncompressed/`) if not
      already covered by the existing `.gitignore`. Check the existing
      `.gitignore` first — several of these entries may already be present —
      and only add what is missing.
- [x] **Agent: Terra.** **0.12** Run `python -m build` in a clean checkout and confirm it
      produces a wheel and sdist without error.
- [x] **Agent: Terra.** **0.13** Inspect the built wheel's file listing (e.g. `unzip -l` or
      `python -m zipfile -l`) and confirm no path under `openNASR/data/`
      is included.
- [x] **Agent: Terra.** **0.14** Create a fresh virtual environment, install the wheel from
      Task 0.12 into it (not editable install), and run
      `python -c "import openNASR"` to confirm the package imports with only
      the core dependencies (no `plot` or `dev` extras) installed.

Acceptance criteria:

- `python -m pip install -e ".[dev,plot]"` succeeds.
- `python -m build` succeeds.
- The built wheel contains no path under `openNASR/data/`.
- `python -c "import openNASR"` succeeds after installation from the wheel
  with no optional extras installed.
- Build and cache artifacts do not appear in `git status`.
- `ruff check` and `mypy` run without erroring out (their findings are not
  required to be clean yet — see the enforcement note above).

## Milestone 0B: Bootstrap supported schemas and deterministic fixtures

Goal: establish the supported-schema evidence and smallest deterministic test
data before any correctness fix or registry implementation depends on it.

This milestone contains derived schema metadata and synthetic rows only. Full
FAA archives and operational records remain outside Git.

Tasks:

- [x] **Agent: Sol.** **0B.1** Obtain the official FAA CSV/schema packages for the cycle
      effective August 6, 2026 and the test/subscription format effective
      September 3, 2026. Store downloads outside the repository and record
      source URLs, effective dates, archive filenames, byte sizes, and SHA-256
      digests in fixture provenance metadata.
- [x] **Agent: Sol.** **0B.2** Add versioned, machine-readable schema manifests under
      `tests/fixtures/manifests/pre_2026_09.json` and
      `tests/fixtures/manifests/nasr_2026_09.json`. Each manifest lists every
      CSV table and each column's name, FAA-declared type, length, and
      nullability. Do not include operational row data.
- [x] **Agent: Sol.** **0B.3** Generate a reviewed schema-difference report between the two
      manifests and commit it as
      `tests/fixtures/manifests/2026_09_changes.json`. Every added, removed,
      renamed, or type-changed table/column must be represented in later
      registry and compatibility tests.
- [x] **Agent: Sol.** **0B.4** Reconcile the 65-table/89-file 2024 inventory and the class matrix
      against both supported manifests. Update counts and `FILESTYPES.md` if the
      supported schemas differ; do not preserve historical counts artificially.
- [x] **Agent: Terra.** **0B.5** Create a synthetic core fixture cycle containing the minimum
      tables and relationships required by Milestone 1: two airports with FAA
      and ICAO IDs, reciprocal runway ends, ILS components, one fix, one unique
      and one duplicated navaid identifier, and one ARTCC with valid high/low
      boundary polygons.
- [x] **Agent: Terra.** **0B.6** Create schema-only fixture cycles for both supported generations.
      They contain all expected CSV filenames and headers but no copied FAA
      operational rows. These fixtures drive discovery and schema tests.
- [x] **Agent: Terra.** **0B.7** Add `tests/conftest.py` helpers that construct `NASR` against a
      supplied fixture path or temporary cache without touching package data,
      the user's cache, or the network.
- [x] **Agent: Terra.** **0B.8** Add a manifest-consistency test proving that every table in
      `FILESTYPES.md` exists in at least one supported manifest and every
      operational table in either supported manifest has an approved naming
      entry or an explicit schema-version compatibility entry.

Acceptance criteria:

- Both supported schema manifests and their provenance are checked in.
- The schema-difference report accounts for every change between generations.
- Core fixture tests run without network access or local FAA archives.
- Schema-only fixtures contain every supported CSV filename and exact headers.
- No operational FAA dataset is added to Git.

## Milestone 1: Fix critical correctness defects

Goal: make existing local-data functionality reliable before adding new
features.

This milestone touches `openNASR/basictypes.py`, `openNASR/nav.py`,
`openNASR/airport.py`, `openNASR/arb.py`, `openNASR/nasr.py`,
`openNASR/rwy.py`, and `openNASR/flightplan.py`. `exceptions.py` (the typed
      exception hierarchy defined in "Architectural decisions" above) must exist
before most of these tasks, since several of them replace a string `raise`
or a silent failure with a specific typed exception — create it first if it
does not yet exist.

Tasks are grouped by file/symbol so each is independently reviewable and
testable.

**`openNASR/exceptions.py` (prerequisite for the tasks below)**

- [x] **Agent: Terra.** **1.1** Create `openNASR/exceptions.py` implementing the full
      exception hierarchy from "Architectural decisions" > "Exception
      hierarchy" (`OpenNASRError`, `ConfigurationError`,
      `CycleNotFoundError`, `DownloadError`, `ArchiveError`,
      `TableNotFoundError`, `SchemaMismatchError`, `RecordNotFoundError`,
      `AmbiguousRecordError`, `FieldConversionError`,
      `InvalidGeometryError`). Implement the members
      needed by Milestone 1 now (`OpenNASRError`, `CycleNotFoundError`,
      `RecordNotFoundError`, `AmbiguousRecordError`, `TableNotFoundError`). Add
      `SchemaMismatchError` no later than Milestone 1B and
      `FieldConversionError` no later than Milestone 5; the remaining exceptions
      are added when Milestones 3-6 first need them.
- [x] **Agent: Terra.** **1.2** Give `RecordNotFoundError` and `AmbiguousRecordError`
      constructors that accept and store structured context (e.g.
      `entity_type`, `identifier`, `filters`, and for the ambiguous case a
      `candidates` sequence) so callers can build a useful message without
      string-formatting logic duplicated at each call site.

**`openNASR/basictypes.py`**

- [x] **Agent: Terra.** **1.3** In `RawDict.__init__` (`basictypes.py:104`), replace the call
      to the undefined `getRecords(airport, nasrDF, airportIDCol)` with the
      existing `getAirportRecords(airport, nasrDF, airportIDCol)`
      (`basictypes.py:13`), which already returns the list of
      `SimpleNamespace` rows this loop expects.
- [x] **Agent: Terra.** **1.4** In `RawDict.getRawByID` (`basictypes.py:113`), either
      initialize `self._map` and `self._raw` in `__init__` (a dict of
      `id -> record` alongside the existing `id -> classType(cRec)` storage
      already built by the loop) so the lookup works, or delete
      `getRawByID` and `getRaw` if nothing in the codebase calls them. Grep
      the codebase for `getRawByID` and `RawDict(...).getRaw(` before
      deciding; do not leave a method that always fails with
      `AttributeError` on first use.
- [x] **Agent: Terra.** **1.5** In `Raw.__getattr__` (`basictypes.py:95`), replace the
      reference to the undefined `self._attributes` with a safe delegation
      to `self._raw`: return `getattr(self._raw, name)` inside a
      `try`/`except AttributeError` that re-raises a plain
      `AttributeError(f"'{type(self).__name__}' object has no attribute
      '{name}'")` (not a recursive call back into `__getattr__`). Add a
      regression test that accessing a valid raw column name (e.g. an
      airport's `SITE_ELEVATION`) works through this path and that an
      invalid name raises `AttributeError`, not `RecursionError`.

**`openNASR/nav.py`**

- [x] **Agent: Terra.** **1.6** In `NAVAID.__init__` (`nav.py:5`), replace the bare `raise
      'Navaid does not exist...'` string raise (`nav.py:12`) with `raise
      RecordNotFoundError(entity_type="Navaid", identifier=navaid)`. Remove
      the `print("Unable to find %s" % navaid)` on the preceding line —
      the exception message carries this information now.
- [x] **Agent: Terra.** **1.7** In `NAVAID._addBASE` (`nav.py:14`), change every criterion
      from OR to AND: build `navBool` starting as `navBool = navBool &
      navCenterBool` (etc.) only for the criteria the caller actually
      supplied, instead of the current `navBool = navBool | navCenterBool`
      pattern at `nav.py:21-27`. The identifier match (`navBool` from
      `nav.py:15`) must always be a required term, not optional.
- [x] **Agent: Terra.** **1.8** In the same method, replace the ambiguous-match branch
      (`nav.py:29-34`) so it raises `AmbiguousRecordError` with the
      candidate rows attached as structured context (per Task 1.2) instead
      of `print`-ing each candidate field and then `raise 'More than
      one...'`.
- [x] **Agent: Terra.** **1.9** In the same method, fix the single-match branch
      (`nav.py:35-36`) to construct the record from `navRecs` (the already
      filtered result), not from a second unfiltered query
      `NAV_BASE[NAV_BASE['NAV_ID']==navaid]` — the current code discards
      the state/country/type filtering it just did. Replace the
      zero-match branch (`nav.py:37-38`) with `raise
      RecordNotFoundError(entity_type="Navaid", identifier=navaid,
      filters={...})`.
- [x] **Agent: Terra.** **1.10** Add a `navType` -> `nav_type` parameter alias per the
      "Navaid requirements" compatibility note in Milestone 5, or defer this
      specific rename to Milestone 5 if it is not needed to pass Milestone 1
      regression tests — do not block this milestone on it.

**`openNASR/airport.py`**

- [x] **Agent: Terra.** **1.11** In `Airport.__init__` (`airport.py:27`), replace `raise
      'Airport does not exist...'` (`airport.py:43`) with `raise
      RecordNotFoundError(entity_type="Airport", identifier=airport)`.
      Remove the preceding `print("Unable to find %s" % airport)`
      (`airport.py:42`).
- [x] **Agent: Terra.** **1.12** Confirm `nasr.isAirport(airport, forceFAA=True)`
      (`airport.py:28`) resolves an ICAO identifier to the matching row's
      `ARPT_ID` before that identifier is used against `APT_RWY`,
      `ILS_BASE`, `ILS_DME`, `ILS_GS`, `ILS_MKR`, and `APT_RWY_END`
      (`airport.py:32-38`). Trace `NASR.isAirport` (`nasr.py:108`): when
      `useCol == 'ICAO_ID'` and `forceFAA=True`, the method currently
      returns `airportIDCol='ARPT_ID'` (`nasr.py:119`) but still passes the
      *original* `ARPT_ID` value found in that branch
      (`nasr.py:116`) — verify with a regression test using an airport
      whose FAA and ICAO IDs differ (e.g. `BWI` vs `KBWI`) that every
      related-table lookup uses the FAA `ARPT_ID` value, not the ICAO
      string, as the filter value.
- [x] **Agent: Terra.** **1.13** Give `NASR.isAirport()` (`nasr.py:108`) a default value for
      `forceFAA` (e.g. `forceFAA: bool = True`) so existing callers that
      invoke it positionally with one argument keep working, and document
      the three-tuple return value (`isAirportBool, airportIDCol,
      ARPT_ID`) with a docstring or a small `NamedTuple` if that does not
      break the existing unpacking call sites.

**`openNASR/arb.py`**

- [x] **Agent: Terra.** **1.14** In `NASR.loadARTCC` (`nasr.py:137`), confirm the call
      `ARB(self['ARB_BASE'], self['ARB_SEG'], arbType='ARTCC')` matches
      `ARB`'s actual current constructor signature in `arb.py`; update
      whichever side (the call or the constructor) is stale so
      `loadARTCC()` succeeds against the fixture dataset added in
      Milestone 2.

**`openNASR/nasr.py`**

- [x] **Agent: Terra.** **1.15** In `NASR.__init__` (`nasr.py:33`), remove the `preloadAll`
      code path that calls the commented-out `self.loadAirports()`
      (`nasr.py:41`, method definition commented out at `nasr.py:140-141`).
      Either: (a) delete the `preloadAll` parameter entirely if nothing
      depends on it, or (b) keep the parameter for signature compatibility
      but raise `NotImplementedError("preloadAll is not yet supported")`
      immediately if `preloadAll=True` is passed, rather than silently
      proceeding into code that references a nonexistent method. Do not
      leave the current behavior, which crashes with `AttributeError` deep
      inside construction.
- [x] **Agent: Terra.** **1.16** In `NASR.setupFiles` (`nasr.py:45`), fix the exact-date
      cycle comparison at `nasr.py:59`: change `cDate < useDate` to `cDate
      <= useDate` so that requesting a cycle's own effective date selects
      that cycle rather than the previous one. Add a regression test that
      constructs `NASR(useDate=<cycle date>)` for a cycle that exists
      locally and asserts the *same* cycle (not the prior one) is selected.
- [x] **Agent: Terra.** **1.17** In the same method, handle the case where `availibleDates`
      (or, for an exact-date request, `earlierDates` at `nasr.py:59-60`) is
      empty. Currently an empty list causes an unhelpful `IndexError` at
      `nasr.py:56-57` or `nasr.py:60`. Raise `CycleNotFoundError` with a
      message that names the requested date (if any) and the searched
      `data/zip` directory, and that tells the caller how to add a cycle
      (place a `28DaySubscription_Effective_YYYY-MM-DD.zip` file there).
- [x] **Agent: Terra.** **1.18** In `NASR.loadCSVData` (`nasr.py:93`), replace the `print`
      calls at `nasr.py:100-105` used to report and retry CSV parsing
      errors with the `warnings` module (`warn(...)`) or `logging`, so
      ordinary construction does not print to stdout on the happy path.
      Keep the retry-with-`backslashreplace` behavior; only change how the
      retry is reported.
- [x] **Agent: Luna.** **1.19** Remove any remaining bare debug prints in `nasr.py` and
      other Milestone-1 files (e.g. search for `print(` calls that are not
      part of documented CLI/reporting behavior) once Tasks 1.6, 1.11, and
      1.18 have removed the ones already identified above. Grep the whole
      `openNASR/` tree for `print(` as a final check for this task.

**`openNASR/flightplan.py`**

- [x] **Agent: Terra.** **1.20** Inspect `openNASR/flightplan.py` for imports/names left over
      from the old `nasr` package (e.g. relative imports that no longer
      resolve under `openNASR/`). Either repair the imports so the module
      loads cleanly, or — if the module's functionality is not part of the
      Milestone 1 scope to finish — exclude it from `openNASR/__init__.py`'s
      public exports and make importing it directly raise a clear
      `NotImplementedError` at module load time with a one-line explanation,
      rather than an unrelated `ImportError`/`NameError`.

**Cross-cutting cleanup**

- [x] **Agent: Luna.** **1.21** Grep the `openNASR/` tree for `raise '` and `raise "` (bare
      string raises, invalid in Python 3 and already a `TypeError` at
      runtime) outside the files above and convert each to the appropriate
      typed exception from `exceptions.py`.
- [x] **Agent: Luna.** **1.22** Normalize source files touched by this milestone to UTF-8
      encoding, LF line endings, and no trailing whitespace. Do not
      reformat files this milestone does not otherwise touch — save
      whole-tree formatting for when Ruff formatting is enforced in
      Milestone 7.
- [x] **Agent: Luna.** **1.23** Correct spelling in public diagnostics and internal names
      touched by the tasks above (e.g. `availibleZips`/`availibleDates` in
      `nasr.py:51-53` → `availableZips`/`availableDates`) where the rename
      is purely internal and does not change any public signature. Do not
      rename public parameters or exported symbols as part of this
      spelling pass — that is a compatibility-sensitive change out of scope
      here.

Required regression tests use the deterministic core fixture introduced in
Milestone 0B. They must never depend on a developer's local FAA cycle:

- [ ] **Agent: Terra.** Construct an airport by FAA ID.
- [ ] **Agent: Terra.** Construct the same airport by ICAO ID, and assert every related
      collection (`rwy`, `rwyend`, `ils`, `dme`, `gs`, `mkr`) is non-empty
      and identical to the FAA-ID construction (covers Task 1.12).
- [ ] **Agent: Terra.** Access airport runway, runway-end, and ILS collections.
- [ ] **Agent: Terra.** Look up a unique fix.
- [ ] **Agent: Terra.** Look up a unique navaid.
- [ ] **Agent: Terra.** Resolve a duplicated navaid using state and type filters (covers Task
      1.7).
- [ ] **Agent: Terra.** Raise `AmbiguousRecordError` for an unresolved duplicate navaid,
      confirm the exception exposes the candidate rows (covers Task 1.8).
- [ ] **Agent: Terra.** Raise `RecordNotFoundError` for each missing entity type (airport,
      fix, navaid).
- [ ] **Agent: Terra.** Select an exact local cycle date and confirm the *matching* cycle,
      not the prior one, is used (covers Task 1.16).
- [ ] **Agent: Terra.** Raise `CycleNotFoundError` when no cycles exist in the searched
      directory (covers Task 1.17).
- [ ] **Agent: Terra.** Load an ARTCC and access a boundary (covers Task 1.14).
- [ ] **Agent: Terra.** Access a valid raw attribute and an invalid raw attribute through
      `Raw.__getattr__`, asserting `AttributeError` (not `RecursionError`)
      for the invalid case (covers Task 1.5).

Acceptance criteria:

- All documented basic lookup examples execute against the fixture dataset.
- No public code path raises a string or relies on printed errors.
- The old constructor forms remain functional.
- All Milestone 1 regression tests pass.

## Milestone 1B: Inventory and schema layer

Goal: give every table in a cycle raw discoverability, including tables with
no dedicated record class, and parse the FAA schema-description files so
column-level validation is possible. This is slice 1 of the "Complete FAA
CSV coverage plan" above, and — unlike slices 2-6 of that plan — it is
required for the `1.0.0` release; see "Relationship to the initial 1.0.0
release" for why the other slices are deferred.

This milestone follows Milestone 1 and uses the supported manifests and
schema-only fixtures from Milestone 0B. It produces the
`schemas.py` and `registry.py` modules referenced by "Files required for
complete coverage" above, in their minimal required-for-1.0.0 form (full
`TableSpec`/relationship population for every table is still deferred to
slices 2-6).

Tasks:

- [x] **Agent: Sol.** **1B.1** Create `openNASR/schemas.py` with the `ColumnSchema` and
      `TableSchema` frozen dataclasses defined in "Core metadata classes"
      above.
- [x] **Agent: Sol.** **1B.2** Implement a parser in `schemas.py` for one
      `*_CSV_DATA_STRUCTURE.csv` file that returns a list of `ColumnSchema`
      rows for a single table. Use both supported manifests and their
      schema-only fixtures to confirm the actual FAA column names for field
      name, type, max length, and nullability before writing the parser.
- [x] **Agent: Sol.** **1B.3** Implement `SchemaCatalog` in `schemas.py` with a
      `table(name, schema_id)`
      method. Since a single schema-description file can describe multiple
      operational tables (per "Schema-description table coverage" above),
      group parsed rows by the file's `CSV File` column (verify the exact
      column name against a real file in Task 1B.2) before building each
      table's `TableSchema`. Add `identify_schema(cycle_path)` that fingerprints
      table names, columns, and FAA-declared types and returns `pre_2026_09` or
      `nasr_2026_09`. Do not choose a schema solely from a filename or date; an
      unrecognized fingerprint raises detailed `SchemaMismatchError`.
- [x] **Agent: Sol.** **1B.4** Implement `SchemaCatalog.validate(name, frame)` returning a
      `ValidationReport` listing missing required columns and unexpected
      columns by comparing a loaded DataFrame's columns against the selected
      versioned `TableSchema`. Separately compare the FAA-declared schema type
      metadata with the supported manifest; never treat the intentionally
      string-valued pandas dtype as an FAA type mismatch. Normal table
      loading must call the report's strict check and raise
      `SchemaMismatchError` for any incompatible drift. The exception must
      include the cycle, table, schema-description filename, missing columns,
      unexpected columns, type differences, affected `TableSpec` and record
      class, and concrete instructions to update `schemas.py`, `registry.py`,
      the relevant domain module, fixtures, the coverage manifest, and this
      plan. Only an explicitly requested diagnostic inspection mode may return
      unfamiliar raw data without raising.
- [x] **Agent: Sol.** **1B.5** Write unit tests parsing every schema-description file in both
      schema-only fixtures and asserting `SchemaCatalog.table(name)` returns a
      non-empty `TableSchema` for every operational table in the corresponding
      versioned manifest.
- [x] **Agent: Sol.** **1B.6** Create `openNASR/registry.py` with the `TableSpec` frozen
      dataclass and `TableRegistry` class defined in "Core metadata
      classes" above. For Milestone 1B, populate `TableRegistry` with a
      `TableSpec` entry for every supported operational table and a
      `TableVariantSpec` for each schema generation in which it appears. Each
      variant defines optional `identity_key`, `indexes`, `order_by`, and
      `required_columns`. Leave `identity_key=None` unless its stability is
      documented or verified across representative data. Initially point
      `record_type` at a shared minimal `FaaRecord` base; Milestones 5 and 8-12
      assign approved record classes. Leave `relationships` empty until the
      owning rich-object milestone verifies the joins.
- [x] **Agent: Sol.** **1B.7** Implement `TableRegistry.supported_tables()` and
      `TableRegistry.unmodeled_tables(available)` as specified in "Core
      metadata classes" and the "Generic loading contract for every CSV"
      bullet list above.
- [x] **Agent: Sol.** **1B.8** Write coverage tests against both schema-only fixtures asserting
      every discovered CSV is either in `TableRegistry.supported_tables()` or
      reported by `unmodeled_tables()` and rejected during normal loading.
      Keep real-cycle integration behind `OPENNASR_REAL_CYCLE_DIR`.
- [x] **Agent: Luna.** **1B.9** Produce a machine-readable coverage report (e.g. a small
      script or test-generated JSON under a scratch/report path, not
      committed generated output) listing, for each supported manifest: total
      CSV files found, how many matched a `TableSpec`, and which did not.
      This satisfies the "produce a machine-readable coverage report" bullet
      from the "Inventory and schema layer" slice description above.

Acceptance criteria:

- Every filename in both supported manifests is discoverable in its schema-only
  fixture and handled according to strict or diagnostic mode.
- Every schema-description file in both generations parses and yields a
  `TableSchema` for every table it describes.
- Every operational table in either supported manifest has exactly one
  schema-version-aware `TableSpec`.
- `unmodeled_tables()` correctly reports a CSV file that exists in the
  fixture/real cycle but has no registered `TableSpec` (test this by
  temporarily registering fewer than 65 tables in a test-local registry
  instance, not by deleting real entries).
- Normal loading raises `SchemaMismatchError` for that unmodeled table, and the
  error contains enough structured detail for a coding agent to locate and
  update the registry, schema policy, record class, fixture, and manifest.

## Milestone 2: Create deterministic test infrastructure

Goal: replace manual scripts with fast automated tests that do not depend on a
multi-gigabyte local dataset or network access.

The current `tests/` directory has five `main_test_*.py` scripts. Four
(`main_test_NASR_airport.py`, `main_test_NASR_airspace.py`,
`main_test_NASR_fix.py`, `main_test_NASR_navaid.py`) are small runnable
examples against the current public API. The fifth,
`tests/main_test_NASR.py`, is **not** a usable starting point: it imports
the already-deleted top-level `nasr` package (`from nasr.nasr import
NASR`), depends on an external `trino` connection to
`trino.opensky-network.org` with a hardcoded username, and writes flight
track CSVs to a `ZTL/` directory. Task 2.10 below calls this out explicitly
so no agent tries to "convert" it as-is.

Tasks:

- [x] **Agent: Terra.** **2.1** Promote the Milestone 0B core fixture to
      `tests/fixtures/cycle/CSV_Data/<stem>/` (matching the
      nested layout `NASR.checkForDecompressed` expects at `nasr.py:82-91`,
      i.e. a `CSV_Data/` directory containing one subdirectory of `.csv`
      files) containing minimal representative CSV tables. Name the cycle
      stem consistently with the `28DaySubscription_Effective_YYYY-MM-DD`
      pattern the loader parses (e.g. use a clearly fake near-future or
      fixture-only date so it can never collide with a real downloaded
      cycle).
- [x] **Agent: Luna.** **2.2** Verify or extend `APT_BASE.csv` to contain exactly two airport rows.
      Include only the columns `AirportBase` and its properties actually
      read (`ARPT_ID`, `ICAO_ID`, `LAT_DECIMAL`, `LONG_DECIMAL`, `ELEV`,
      `SITE_ELEVATION` per `basictypes.py:61` and `airport.py:14-23`) plus
      any column a Milestone 1 regression test also needs. Give the two
      airports different FAA and ICAO identifiers so Task 1.12's
      ICAO-resolution regression test is meaningful.
- [x] **Agent: Luna.** **2.3** Verify or extend `APT_RWY.csv` and `APT_RWY_END.csv` with at least
      one reciprocal runway pair (e.g. `01/19`) for one of the two Task 2.2
      airports, including both runway ends so `Airport.makeRWYbnds`
      (`airport.py:75-81`) has real geometry to build.
- [x] **Agent: Luna.** **2.4** Verify or extend `ILS_BASE.csv`, `ILS_DME.csv`, `ILS_GS.csv`, and
      `ILS_MKR.csv` with one ILS record tied to one of the Task 2.3 runway
      ends.
- [x] **Agent: Luna.** **2.5** Verify or extend `FIX_BASE.csv` with one uniquely identified fix
      (e.g. `AABEE`, matching the identifier already used in the README's
      quick-start example and the existing `main_test_NASR_fix.py`, so the
      README example itself becomes testable per Task 7.1).
- [x] **Agent: Luna.** **2.6** Verify or extend `NAV_BASE.csv` with one navaid with a globally
      unique `NAV_ID`, and two navaid rows sharing one `NAV_ID` but
      differing in `STATE_CODE` and `NAV_TYPE` (so Milestone 1's
      AND-filter and `AmbiguousRecordError` regression tests, Tasks 1.7-1.9,
      have real duplicate data to resolve against).
- [x] **Agent: Luna.** **2.7** Verify or extend `ARB_BASE.csv` and `ARB_SEG.csv` with one ARTCC
      (reuse a real three-letter ARTCC identifier such as `ZOB` for
      familiarity) that has both a high-altitude and a low-altitude
      boundary. Construct the boundary segment coordinates so each closes
      into a valid simple polygon (no self-intersection) — validate this
      with `shapely.geometry.Polygon(...).is_valid` in the fixture-building
      test itself, not just by eyeballing the coordinates.
- [x] **Agent: Terra.** **2.8** Add at least one malformed fixture (e.g. a CSV with a missing
      required column, or a row with an unparseable coordinate value) under
      `tests/fixtures/malformed/` for the error-path tests in Task 2.13.
- [x] **Agent: Terra.** **2.9** Add at least one fixture cycle variant under
      `tests/fixtures/missing_table_cycle/` that omits one optional table
      entirely, to exercise the "missing optional table affects only its
      related optional property" requirement from the coverage-tests list
      above.
- [x] **Agent: Luna.** **2.10** Delete `tests/main_test_NASR.py`. Its `trino`/OpenSky data
      pull is unrelated to `openNASR`'s scope (it consumes `openNASR` output
      to query a third-party flight-tracking service) and it no longer even
      imports successfully. If any part of its logic is worth keeping as a
      documented usage example, move only that part into a new
      README-adjacent example, not into the automated test suite, and do
      not carry over the hardcoded `trino` connection or credentials-shaped
      username.
- [x] **Agent: Terra.** **2.11** Convert `tests/main_test_NASR_airport.py` into
      `tests/test_airport.py`: split into discrete `test_*` functions (e.g.
      construct-by-FAA-id, construct-by-ICAO-id, access `rwy`/`rwyend`/`ils`
      collections), replace the direct `NASR()` call with the Task 2.15
      fixture, and remove the interactive `BWI.plot()` call. Milestone 6 owns
      plotting tests after the plotting return contract is implemented.
      Delete the large commented-out block (`main_test_NASR_airport.py:16-72`)
      rather than carrying it into the new file.
- [x] **Agent: Terra.** **2.12** Convert `tests/main_test_NASR_airspace.py` into
      `tests/test_airspace.py`, `tests/main_test_NASR_fix.py` into
      `tests/test_fix.py`, and `tests/main_test_NASR_navaid.py` into
      `tests/test_navaid.py`, each using the Task 2.15 fixture instead of a
      bare `NASR()` call against real local data.
- [x] **Agent: Luna.** **2.13** Confirm no default Milestone 2 test invokes interactive plotting.
      Add a comment or marker pointing to Milestone 6 rather than asserting a
      future `Figure`/`Axes` return contract prematurely.
- [x] **Agent: Terra.** **2.14** Add error-path tests using the Task 2.8 and 2.9 fixtures:
      constructing `NASR` against the malformed fixture raises a typed
      exception (not an unrelated pandas parser traceback), and constructing
      it against the missing-optional-table fixture succeeds but the
      dependent property/collection is empty or raises a specific typed
      error only when that specific feature is used.
- [x] **Agent: Terra.** **2.15** Extend the Milestone 0B fixtures in `tests/conftest.py` with a temporary
      cache directory (`tmp_path`-based), the Task 2.1 extracted fixture
      cycle, a fixture producing the *archive* form (a real `.zip` built
      from the Task 2.1 tree, for Milestone 3's import/extraction tests),
      and a ready-to-use `NASR` instance constructed against the fixture
      cycle.
- [x] **Agent: Terra.** **2.16** Add unit tests for `timestampToYearDecimal` (`nasr.py:10`)
      covering a leap year and a non-leap year.
- [x] **Agent: Terra.** **2.17** Add only the identifier-normalization tests needed by existing
      Milestone 1 behavior. Milestone 5 owns the final repository-wide
      normalization contract; do not add skipped future tests.
- [x] **Agent: Luna.** **2.18** Move projection round-trip coverage to Milestone 6, where the
      corrected coordinate contract is implemented. Milestone 2 only verifies
      that importing core lookup functionality does not require plotting.
- [x] **Agent: Luna.** **2.19** Mark any test that requires a real, multi-gigabyte local FAA
      cycle (as opposed to the Task 2.1 fixture) with
      `@pytest.mark.skipif` gated on an explicit environment variable (e.g.
      `OPENNASR_REAL_CYCLE_DIR`), and confirm the default `pytest` run skips
      them with no environment configured.
- [x] **Agent: Terra.** **2.20** Audit the full new `tests/` tree for anything that opens a
      socket, resolves a hostname, or otherwise reaches the network by
      default, and fix or explicitly mark it per Task 2.19.

Fixture requirements:

- Values should be deterministic and small enough for code review.
- Boundary coordinates must form valid polygons.
- Duplicate navaid records must differ in state and type.
- ICAO and FAA identifiers must map to the same airport.
- At least one optional table should be absent to verify graceful handling.
- Fixture field values are synthetic/fabricated, not copied from a live FAA
  cycle, except for identifiers that are public and stable by design (e.g.
  reusing the real ARTCC code `ZOB` or fix code `AABEE` as a label is fine).
  Do not copy real runway lengths, coordinates, elevations, or other
  operational values verbatim from a downloaded FAA cycle into a committed
  fixture — invented-but-plausible values keep the fixture obviously
  non-operational and avoid the fixture silently going stale against the
  FAA source it was copied from.

Acceptance criteria:

- `python -m pytest` passes without network access or local FAA data.
- The default test suite completes quickly enough for every commit.
- Test failures identify behavior rather than depending on incidental FAA data.
- `tests/main_test_NASR.py` no longer exists and no automated test depends on
  `trino` or any other external network service.

## Milestone 3: Implement cycle and cache management

Goal: remove runtime data storage from the installed package and provide safe,
explicit cycle management.

### Cycle model

Introduce an immutable `Cycle` value object containing:

- `effective_date: date`
- `archive_path: Path | None`
- `data_path: Path | None`
- `source_url: str | None`
- parsed metadata

Dates must be parsed and formatted in one shared utility.

Introduce an immutable `UpdateStatus` containing the newest remote cycle,
newest cached cycle, whether an update is available, check time, source URL,
and whether the result came from the 24-hour cache.

### CycleManager API

Implement at minimum:

```python
manager = CycleManager(cache_dir=None)
manager.available_cycles() -> tuple[date, ...]
manager.get(cycle) -> Cycle
manager.latest() -> Cycle
manager.import_archive(path, *, expected_cycle=None) -> Cycle
manager.check_for_updates(*, force=False) -> UpdateStatus
manager.download(cycle, *, force=False) -> Cycle
manager.download_latest(*, force=False) -> Cycle
manager.remove(cycle, *, archive=True, extracted=True) -> None
```

Tasks:

- [x] **Agent: Terra.** Resolve the cache path according to the documented precedence.
- [ ] **Agent: Terra.** Discover valid extracted cycles and archives independently.
- [ ] **Agent: Terra.** Validate archive names without relying solely on lexical sorting.
- [ ] **Agent: Terra.** Read the cycle date from trusted metadata or a validated filename.
- [ ] **Agent: Terra.** Import an existing archive without modifying the original file.
- [ ] **Agent: Terra.** Download to a temporary `.part` file in the cache.
- [ ] **Agent: Terra.** Stream downloads instead of reading the entire archive into memory.
- [ ] **Agent: Terra.** Atomically rename successful downloads.
- [ ] **Agent: Luna.** Compute and store SHA-256 metadata.
- [ ] **Agent: Terra.** Reject HTML error pages and obviously invalid archives.
- [ ] **Agent: Sol.** Extract into a temporary directory, validate it, then atomically publish
      the completed cycle.
- [ ] **Agent: Sol.** Protect extraction against absolute paths and `..` path traversal.
- [ ] **Agent: Terra.** Locate the nested FAA CSV archive or CSV directory without assuming one
      exact intermediate folder name.
- [ ] **Agent: Sol.** Make interrupted download and extraction cleanup safe and idempotent.
- [ ] **Agent: Luna.** Make `force=False` reuse a valid cached cycle.
- [ ] **Agent: Sol.** Never delete caller-owned archives during import.
- [ ] **Agent: Terra.** Implement an injectable FAA cycle provider that discovers only metadata
      and archive URLs. Give live requests a hard two-second timeout and mock
      the provider in all default tests.
- [ ] **Agent: Terra.** Implement `CycleManager.check_for_updates(force=False)` returning
      `UpdateStatus`. Reuse a successful result for 24 hours; `force=True`
      bypasses it. Write cache metadata atomically outside the package.
- [ ] **Agent: Terra.** Do not overwrite the last successful update metadata with a failed check.
      The explicit method raises a typed `DownloadError` with its cause, while
      the import wrapper suppresses the failure after diagnostic logging.
- [ ] **Agent: Terra.** Add `notify_if_update_available()` and call it from `openNASR/__init__.py`.
      It performs only the metadata check, never downloads, and prints exactly
      one concise message to `stderr` only when the remote cycle is newer than
      the newest cached cycle. It must catch every update-check/cache failure so
      package import always succeeds.
- [ ] **Agent: Luna.** Support `OPENNASR_DISABLE_UPDATE_CHECK=1` for deterministic deployments
      and environments whose policy prohibits import-time network access.
- [ ] **Agent: Terra.** Test import with: a fresh successful response, a valid cached response,
      cache older than 24 hours, `force=True`, no update, update available,
      timeout, DNS/TLS/HTTP failure, malformed response, unwritable cache, and
      the disable environment variable. Assert failures emit no user-facing
      connection warning and never prevent import.
- [ ] **Agent: Terra.** After the Python API is complete, add `openNASR/cli.py` using the standard
      library `argparse` module and register an `opennasr` console-script entry
      point in `pyproject.toml`.
- [ ] **Agent: Terra.** Implement `opennasr check [--force]`, showing the newest FAA cycle, newest
      cached cycle, cache age, and whether a download is available.
- [ ] **Agent: Terra.** Implement `opennasr download latest` and
      `opennasr download YYYY-MM-DD`, delegating to `CycleManager` rather than
      duplicating network or extraction logic.
- [ ] **Agent: Terra.** Implement `opennasr list`, showing cached and archived cycles with their
      paths, sizes, validation state, and effective dates.
- [ ] **Agent: Terra.** Implement `opennasr remove YYYY-MM-DD`; require interactive confirmation
      unless `--yes` is supplied, resolve the exact cycle before deletion, and
      report which cached archive and extracted data were removed.
- [ ] **Agent: Terra.** Give CLI commands documented stable exit codes for success, usage error,
      unavailable network/data, validation failure, and internal failure.
- [ ] **Agent: Terra.** Test every CLI command using temporary caches and mocked transports. No
      CLI test may access the live FAA service or the user's real cache.

Network-test requirements:

- Mock all HTTP responses.
- Cover success, 404, timeout, truncated response, invalid ZIP, wrong cycle,
  interrupted write, and retry behavior.
- Do not scrape live FAA HTML in the ordinary test suite.
- Isolate FAA URL discovery behind a provider interface so site changes do not
  affect archive, cache, and table logic.

Acceptance criteria:

- A fixture ZIP can be imported and loaded from an empty temporary cache.
- Re-import and re-extraction are idempotent.
- Failed operations leave no cycle that appears valid.
- ZIP traversal attempts cannot write outside the temporary extraction root.
- `NASR()` does not write into `site-packages` or the source checkout.
- A successful update result is reused for 24 hours and `force=True` refreshes
  it.
- `import openNASR` announces an available newer cycle without downloading it.
- Every simulated update-check failure leaves import successful and silent.
- The `opennasr` entry point and all four command families pass mocked tests.

## Milestone 4: Add lazy, indexed table access

Goal: reduce startup time and memory use while preserving direct DataFrame
access.

### TableRepository API

Implement a mapping-like repository:

```python
tables = TableRepository(cycle_path)
tables.available_tables
tables.load("APT_BASE")
tables["APT_BASE"]
tables.is_loaded("APT_BASE")
tables.clear("APT_BASE")
tables.clear()
```

Tasks:

- [ ] **Agent: Luna.** Discover table names without loading CSV contents.
- [ ] **Agent: Luna.** Normalize requested table names to uppercase.
- [ ] **Agent: Terra.** Cache each loaded DataFrame per `NASR` instance.
- [ ] **Agent: Terra.** Preserve `nasr["APT_BASE"]` compatibility by delegating to the repository.
- [ ] **Agent: Terra.** Implement `collections.abc.Mapping` instead of subclassing `dict` if
      behavior can remain compatible.
- [ ] **Agent: Terra.** Provide `nasr.table(name, *, copy=False)`.
- [ ] **Agent: Terra.** Make the default return the cached DataFrame and document mutation risk.
- [ ] **Agent: Luna.** Return a defensive copy when `copy=True`.
- [ ] **Agent: Terra.** Add clear errors for missing or unreadable tables.
- [ ] **Agent: Terra.** Handle encoding fallback narrowly; never catch every exception and retry
      indiscriminately.
- [ ] **Agent: Terra.** Preserve meaningful pandas parser errors as exception causes.
- [ ] **Agent: Terra.** Create indexes lazily for frequently queried identifier columns.
- [ ] **Agent: Terra.** Cache normalized identifier mappings rather than scanning entire columns
      for every lookup.
- [ ] **Agent: Terra.** Avoid global caches that can leak data between cycles.

Performance targets, measured with a representative real cycle when available:

- Constructing `NASR` must not parse all CSV files.
- Accessing one entity should load only the required tables.
- Repeated lookups in an already indexed table should not perform full-column
  scans.
- Record baseline and improved timing and peak memory in development notes; do
  not create brittle performance assertions in unit tests.

Acceptance criteria:

- `NASR()` loads zero DataFrames until a table or entity is requested.
- Repeated access returns the same cached DataFrame unless `copy=True`.
- Clearing a table causes the next access to reload it.
- Mapping compatibility tests pass.

## Milestone 5: Normalize the domain API

Goal: provide consistent, typed objects while preserving raw FAA records and
legacy entry points.

### Common record model

Replace ad hoc `SimpleNamespace` behavior with one consistent representation.
An immutable dataclass or read-only mapping wrapper is preferred. It must:

- preserve source column names;
- permit safe attribute access for valid column names;
- provide mapping access for all columns;
- distinguish a missing column from a present null value;
- expose `raw` or `as_dict()` without leaking undocumented mutable state.

- [ ] **Agent: Terra.** Implement shared converters for nullable text, ISO dates, integers,
      decimals/floats, boolean/code values, coordinates, and enums without
      mutating raw strings.
- [ ] **Agent: Terra.** Raise `FieldConversionError` for invalid non-empty values with cycle,
      table, column, raw value, record identity when available, and expected
      type.
- [ ] **Agent: Terra.** Test that leading zeros and empty strings survive raw access while typed
      properties return the approved Python values or `None`.

### NASR facade methods

Repositories are the canonical plural API:

```python
nasr.airports: AirportRepository
nasr.fixes: FixRepository
nasr.navaids: NavaidRepository
nasr.artccs: ArtccRepository

nasr.airports.get(identifier) -> Airport
nasr.airports.find(*, state=None, country=None) -> tuple[Airport, ...]
nasr.navaids.get(identifier, *, state=None, country=None, artcc=None,
                  nav_type=None) -> Navaid
nasr.navaids.find(*, state=None, country=None, artcc=None,
                   nav_type=None) -> tuple[Navaid, ...]
```

Singular convenience methods delegate directly to the corresponding
repository's `get()` method:

```python
nasr.airport(identifier) -> Airport
nasr.fix(identifier) -> Fix
nasr.navaid(identifier, *, state=None, country=None, artcc=None,
            nav_type=None) -> Navaid
nasr.artcc(identifier) -> Artcc
```

Plural repository attributes are not callable methods. Search always uses
`.find(...)`; exact lookup uses `.get(...)` or a singular convenience method.
Later `1.x` milestones add repositories using the same contract.

- [ ] **Agent: Terra.** Add tests proving repository `.get()` and the singular convenience method
      return equivalent rich objects.
- [ ] **Agent: Terra.** Add repository-wide identifier normalization tests for stripping and
      uppercasing, including composite identifiers and optional filters.

### Airport requirements

- [ ] **Agent: Terra.** Resolve FAA and ICAO identifiers case-insensitively.
- [ ] **Agent: Terra.** Expose `faa_id`, `icao_id`, `name`, `latitude`, `longitude`, and
      `elevation_ft` with documented nullability.
- [ ] **Agent: Terra.** Expose runways and runway ends as typed immutable collections.
- [ ] **Agent: Terra.** Associate ILS, DME, glide-slope, and marker records without assuming every
      optional table or field exists.
- [ ] **Agent: Terra.** Validate reciprocal runway identifiers before building polygons.
- [ ] **Agent: Terra.** Keep raw records available for fields without typed properties.

### Fix requirements

- [ ] **Agent: Terra.** Expose identifier, name when available, latitude, longitude, state,
      country, and ARTCC metadata.
- [ ] **Agent: Terra.** Treat duplicated fix identifiers explicitly if current FAA cycles contain
      them.

### Navaid requirements

- [ ] **Agent: Terra.** Make every filter optional but conjunctive.
- [ ] **Agent: Terra.** Normalize aliases such as `navType` to the new `nav_type` parameter during
      the compatibility period.
- [ ] **Agent: Terra.** Raise `AmbiguousRecordError` with candidate summaries when multiple rows
      remain.
- [ ] **Agent: Luna.** Do not print all candidates to stdout.
- [ ] **Agent: Terra.** Expose navigation type, name, state, country, high/low ARTCC, frequency,
      and coordinates when available.

### ARTCC and boundary requirements

- [ ] **Agent: Terra.** Replace dynamic attributes as the sole boundary interface with an
      explicit mapping keyed by altitude or boundary type.
- [ ] **Agent: Terra.** Retain `.high` and `.low` compatibility properties where meaningful.
- [ ] **Agent: Terra.** Preserve disjoint polygon parts; do not accidentally join independent
      rings into one invalid polygon.
- [ ] **Agent: Terra.** Use `Polygon` or `MultiPolygon` according to the data.
- [ ] **Agent: Terra.** Expose bounds in standard Shapely order:
      `(min_x, min_y, max_x, max_y)` or `(min_lon, min_lat, max_lon, max_lat)`.
- [ ] **Agent: Terra.** Validate and document coordinate order for `latlon` and `lonlat`.

Acceptance criteria:

- Every single-record lookup has deterministic not-found and ambiguous errors.
- Domain objects are type annotated and have useful representations.
- Raw field access remains possible.
- Compatibility tests cover legacy imports, class aliases, and constructors.

## Milestone 6: Correct geometry and plotting

Goal: make coordinate calculations explicit, numerically safe, and independent
from interactive plotting.

Tasks:

- [ ] **Agent: Terra.** Rename `cfcn.py` to `coordinates.py` with a compatibility forwarding
      module.
- [ ] **Agent: Sol.** Define whether every coordinate argument is `(latitude, longitude)` or
      `(longitude, latitude)` and enforce that convention.
- [ ] **Agent: Terra.** Document that projection distances are nautical miles.
- [ ] **Agent: Sol.** Make `ll2xy` and `xy2ll` round-trip within an agreed tolerance.
- [ ] **Agent: Sol.** Handle projection-center points where `rho == 0` without division by zero.
- [ ] **Agent: Sol.** Reject invalid latitude and longitude values.
- [ ] **Agent: Terra.** Add scalar and NumPy-array tests.
- [ ] **Agent: Sol.** Verify runway width conversion from feet to nautical miles.
- [ ] **Agent: Sol.** Verify ILS magnetic variation sign handling against documented FAA field
      semantics.
- [ ] **Agent: Terra.** Return Matplotlib `Figure` and `Axes` objects from plotting methods.
- [ ] **Agent: Luna.** Never call `plt.close("all")` by default.
- [ ] **Agent: Luna.** Do not rely on `plt.gca()` when an axes object is already available.
- [ ] **Agent: Luna.** Keep Matplotlib imports behind the optional plotting boundary so core
      table access works without the `plot` extra.
- [ ] **Agent: Terra.** Use noninteractive plotting tests that inspect artists and geometry.

Acceptance criteria:

- Projection round-trip tests cover scalar, vector, and center-point inputs.
- Importing and using core `openNASR` works without Matplotlib installed.
- Airport plotting returns objects callers can customize and save.
- Plot tests pass with the `Agg` backend.

## Milestone 7: Documentation, CI, and release readiness

Goal: produce a package that can be installed, tested, and released
reproducibly.

By this milestone, Milestones 1-6 have replaced most of the code Ruff and
mypy would otherwise be flagging mid-rewrite (see the Milestone 0 note on
deferred enforcement). Task 7.10 below turns on the gate.

Tasks:

- [ ] **Agent: Luna.** **7.1** Update README examples to execute as doctests (via
      `doctest`) or as tested documentation snippets (e.g. extracted and run
      in a test) where practical. Prioritize the "Quick start", "Airports",
      "Fixes", and "Navigation aids" examples, since those are the ones most
      likely to silently drift from the real API.
- [ ] **Agent: Luna.** **7.2** Document the cache location and override precedence (explicit
      `cache_dir` argument > `OPENNASR_CACHE_DIR` env var > platform default)
      from Milestone 3's "Data location" design, in the README's data-setup
      section.
- [ ] **Agent: Luna.** **7.3** Document manual archive import (`CycleManager.import_archive`)
      and automatic download (`CycleManager.download` /
      `download_latest`) as two clearly separate workflows in the README,
      matching Milestone 3's API.
- [ ] **Agent: Luna.** **7.4** Document duplicate-record behavior (`AmbiguousRecordError`)
      and the full exception hierarchy from `exceptions.py`, with one
      example of catching a typed exception.
- [ ] **Agent: Terra.** **7.5** Add an API reference for public classes and methods. This can
      be a generated reference (e.g. via `pdoc` or `mkdocs` + `mkdocstrings`)
      or a hand-written Markdown reference page — pick whichever this
      project's docs tooling (introduced in this same task, if none exists)
      supports; do not hand-maintain a reference that duplicates docstrings
      if a generator is available.
- [ ] **Agent: Luna.** **7.6** Add a migration guide (e.g. `MIGRATION.md`) from the old
      `nasr` namespace and legacy uppercase classes (`FIX`, `NAVAID`, `ARB`)
      to the new facade (`nasr.fix(...)`, `Fix`, `Navaid`, `Artcc`),
      referencing the compatibility aliases documented in "Compatibility
      policy" above.
- [ ] **Agent: Luna.** **7.7** Add `CHANGELOG.md` using Keep a Changelog format, backfilling
      entries for the Milestone 0-7 work already completed at the time this
      task runs.
- [ ] **Agent: Luna.** **7.8** Add contributor instructions (e.g. `CONTRIBUTING.md`) covering:
      environment setup (`pip install -e ".[dev,plot]"`), how to run the
      full verification command list from "Testing matrix" below, and where
      test fixtures live.
- [ ] **Agent: Terra.** **7.9** Add CI configuration (e.g. GitHub Actions) running the test
      suite on the minimum supported Python version (Task 0.1) and the
      newest released Python version.
- [ ] **Agent: Terra.** **7.10** In the same CI configuration, add required (non-`continue-on-error`)
      steps for `ruff format --check`, `ruff check`, and `mypy`. This is the
      enforcement step deferred from Milestone 0 — remove any `--exit-zero`
      or equivalent soft-fail flag added there. Fix whatever findings this
      surfaces in the by-now-largely-rewritten codebase before merging this
      task; do not merge the gate red.
- [ ] **Agent: Terra.** **7.11** Add a CI step that builds the wheel and asserts (e.g. via a
      small script inspecting the archive listing) that it contains no path
      under `openNASR/data/`, extending the manual check from Task 0.13 into
      an automated, permanent CI check.
- [ ] **Agent: Terra.** **7.12** Validate README rendering (e.g. render it through the same
      Markdown renderer PyPI uses, or at minimum lint it with a Markdown
      linter) and validate package metadata with
      `python -m twine check dist/*`.
- [ ] **Agent: Sol.** **7.13** Decide the initial supported release version number based on
      compatibility (see "Compatibility policy" below for the pre-`1.0.0`
      rules); do not publish while any Milestone 0-6 acceptance criterion is
      unmet or any P1/P2 defect from "Current repository state" remains
      open.
- [ ] **Agent: Luna.** **7.14** (Non-blocking for release readiness — track separately, do
      not let it hold up `1.0.0`) Update the Git remote/documentation from
      the moved ADCLab repository to
      `https://github.com/xDecisionSystems/openNASR` once ownership is
      confirmed by the user. This depends on an external, organizational
      decision outside this codebase's control.

Release acceptance criteria:

- A clean environment can install the wheel and import the package.
- A new user can import a local fixture/archive by following only the README.
- All CI jobs pass, including the Task 7.10 lint/type-check gate.
- No critical known defect is documented as a feature or left behind a public
  flag.
- No FAA dataset, secret, local path, or generated artifact exists in the
  release.
- Record and domain coverage matches the `1.0.0` scope defined in "Complete
  FAA CSV coverage plan" > "Relationship to the initial 1.0.0 release" —
  full rich coverage of every supported operational table is explicitly not required to
  ship `1.0.0`; raw coverage of all discovered tables is required.
- Both supported schema generations pass strict manifest and schema validation.
- Cycle download/cache management, import-time update notification, and every
  required `opennasr` CLI command pass their fixture-based tests.

## Milestone 8: Release 1.1.0 — airport-linked airspace and military operations

Goal: add rich objects for the two airport-linked tables deferred from the
`1.0.0` airport model: `CLS_ARSP` and `MIL_OPS`.

Tasks:

- [ ] **Agent: Sol.** **8.1** Verify identity, index, and airport/site relationship keys for both
      tables against both supported schema generations and representative rows.
- [ ] **Agent: Terra.** **8.2** Implement `ClassAirspaceRecord` and a rich `ClassAirspace` object
      in `airspace.py`, exposed through `nasr.class_airspaces` and
      `Airport.class_airspace` where the join is unambiguous.
- [ ] **Agent: Terra.** **8.3** Implement `MilitaryOperationRecord` and a rich
      `MilitaryOperation` object in `military.py`, exposed through
      `nasr.military_operations` and `Airport.military_operations`.
- [ ] **Agent: Terra.** **8.4** Add raw/typed converter tests, repository `.get()`/`.find()` tests,
      ambiguous/missing relationship tests, and synthetic rows for both schemas.
- [ ] **Agent: Terra.** **8.5** Export and document both rich APIs, then update the coverage report
      and changelog for `1.1.0`.

Acceptance criteria:

- `CLS_ARSP` and `MIL_OPS` have approved records, rich objects, repositories,
  and tested airport relationships.
- No join uses an undocumented short identifier.
- Both supported schema generations pass strict and rich-object tests.

## Milestone 9: Release 1.2.0 — navigation network

Goal: complete rich navigation-network coverage for `AWY_*`, `HPF_*`, `COM`,
and `FRQ`, and connect them to the existing fix/navaid objects where supported.

Tasks:

- [ ] **Agent: Sol.** **9.1** Verify and register identity, ordering, and relationship keys for
      `AWY_BASE` and `AWY_SEG_ALT` across both schemas.
- [ ] **Agent: Terra.** **9.2** Implement `AirwayRecord` and
      `AirwaySegmentRecord`; expose the rich
      `Airway` through `nasr.airways`, `nasr.airway()`, ordered segments, and
      segment altitude constraints.
- [ ] **Agent: Terra.** **9.3** Verify and register keys for `HPF_BASE`, `HPF_CHRT`, `HPF_RMK`, and
      `HPF_SPD_ALT`; implement their approved record classes and rich
      `HoldingPattern` repository, charts, remarks, and speed/altitude limits.
- [ ] **Agent: Terra.** **9.4** Implement `CommunicationOutletRecord`/`CommunicationOutlet` and
      `FrequencyRecord`/`Frequency` with `nasr.communication_outlets` and
      `nasr.frequencies` repositories.
- [ ] **Agent: Sol.** **9.5** Add relationships from fixes, navaids, airways, holding patterns,
      and serviced facilities only where full FAA composite keys are verified.
- [ ] **Agent: Terra.** **9.6** Add synthetic relationship fixtures for both schemas, ordering and
      ambiguity tests, raw/typed converter tests, public exports, documentation,
      coverage reporting, and the `1.2.0` changelog entry.

Acceptance criteria:

- All eight navigation-network tables have rich objects or rich child
  collections matching `FILESTYPES.md`.
- Airway segments and limits preserve FAA sequence order.
- Communication/frequency links never rely on display names alone.

## Milestone 10: Release 1.3.0 — procedures and preferred routes

Goal: implement rich coverage for `CDR`, `DP_*`, `PFR_*`, and `STAR_*`.

Tasks:

- [ ] **Agent: Sol.** **10.1** Verify procedure codes, airport associations, route identifiers,
      and ordering columns for both supported schemas.
- [ ] **Agent: Terra.** **10.2** Implement `CodedDepartureRouteRecord` and rich
      `CodedDepartureRoute` objects through `nasr.coded_departure_routes`.
- [ ] **Agent: Terra.** **10.3** Implement `DepartureProcedureRecord`, `DepartureAirportRecord`,
      and `DepartureRouteRecord`; expose rich `DepartureProcedure` objects via
      `nasr.departures`, `nasr.departure()`, airports, and ordered routes.
- [ ] **Agent: Terra.** **10.4** Implement `PreferredRouteRecord`,
      `PreferredRouteFormatRecord`, and `PreferredRouteSegmentRecord`; expose
      `nasr.preferred_routes` with ordered segments and formats.
- [ ] **Agent: Terra.** **10.5** Implement `StarProcedureRecord`, `StarAirportRecord`, and
      `StarRouteRecord`; expose rich `StarProcedure` objects through
      `nasr.stars`, `nasr.star()`, airports, and ordered routes.
- [ ] **Agent: Terra.** **10.6** Add both-schema fixtures, exact/ambiguous lookup tests, sequence
      tests, airport relationship tests, converter tests, exports,
      documentation, coverage reporting, and the `1.3.0` changelog entry.

Acceptance criteria:

- All ten procedure/route tables have approved records and rich APIs.
- Route and procedure ordering is deterministic and schema-version aware.
- Duplicate procedure names or codes raise structured ambiguity errors.

## Milestone 11: Release 1.4.0 — facilities, weather, and identifiers

Goal: implement rich coverage for `ATC_*`, `RDR`, `AWOS`, `WXL_*`, `FSS_*`,
and `LID`.

Tasks:

- [ ] **Agent: Sol.** **11.1** Verify facility, site, service, remark, and location join keys for
      all eleven tables against both supported schemas.
- [ ] **Agent: Terra.** **11.2** Implement `AtcFacilityRecord`, `AtisRecord`, `AtcRemarkRecord`,
      and `AtcServiceRecord`; expose rich `AtcFacility` objects through
      `nasr.atc_facilities` and `nasr.atc_facility()`.
- [ ] **Agent: Terra.** **11.3** Implement `RadarRecord` and a standalone rich `Radar` repository,
      adding facility relationships only when the full key is reliable.
- [ ] **Agent: Terra.** **11.4** Implement `AutomatedWeatherStationRecord` and rich
      `AutomatedWeatherStation` objects through `nasr.weather_stations`.
- [ ] **Agent: Terra.** **11.5** Implement `WeatherLocationRecord`, `WeatherServiceRecord`, and
      rich `WeatherLocation` objects through `nasr.weather_locations` and their
      service collections.
- [ ] **Agent: Terra.** **11.6** Implement `FlightServiceStationRecord`,
      `FlightServiceStationRemarkRecord`, and rich `FlightServiceStation`
      objects through `nasr.flight_service_stations`.
- [ ] **Agent: Terra.** **11.7** Implement `LocationIdentifierRecord` and rich standalone
      `LocationIdentifier` objects through `nasr.location_identifiers`.
- [ ] **Agent: Terra.** **11.8** Add both-schema fixtures, repository and relationship tests,
      converter tests, exports, documentation, coverage reporting, and the
      `1.4.0` changelog entry.

Acceptance criteria:

- All eleven facility/weather/location tables have rich APIs matching
  `FILESTYPES.md`.
- Standalone objects remain useful without speculative joins.
- Optional service and remark tables load lazily.

## Milestone 12: Release 1.5.0 — special-use and military airspace

Goal: complete rich coverage for `MAA_*`, `PJA_*`, and `MTR_*`.

Tasks:

- [ ] **Agent: Sol.** **12.1** Verify the FAA meaning of `MAA` from official documentation. Keep
      the approved conservative `Maa*` names unless a later user-approved naming
      decision updates `FILESTYPES.md`.
- [ ] **Agent: Sol.** **12.2** Verify identity, contact, sequence, multipart geometry, route, and
      ordering keys for all twelve tables across both schema generations.
- [ ] **Agent: Terra.** **12.3** Implement `MaaRecord`, `MaaContactRecord`, `MaaRemarkRecord`, and
      `MaaShapePointRecord`; expose rich `Maa` objects through `nasr.maas`,
      `nasr.maa()`, contacts, remarks, and validated geometry.
- [ ] **Agent: Terra.** **12.4** Implement `ParachuteJumpAreaRecord` and
      `ParachuteJumpAreaContactRecord`; expose rich `ParachuteJumpArea` objects
      through `nasr.parachute_jump_areas` and contact collections.
- [ ] **Agent: Terra.** **12.5** Implement `MilitaryTrainingRouteRecord`,
      `MilitaryTrainingRouteAgencyRecord`, `MilitaryTrainingRoutePointRecord`,
      `MilitaryTrainingRouteProcedureRecord`,
      `MilitaryTrainingRouteTerrainRecord`, and
      `MilitaryTrainingRouteWidthRecord`; expose rich
      `MilitaryTrainingRoute` objects through `nasr.military_training_routes`.
- [ ] **Agent: Sol.** **12.6** Preserve ordered points, widths, terrain, procedures, and
      multipart geometry without joining disconnected shapes or route parts.
- [ ] **Agent: Terra.** **12.7** Add both-schema fixtures, geometry validity tests, ordering and
      relationship tests, converter tests, exports, documentation, coverage
      reporting, and the `1.5.0` changelog entry.

Acceptance criteria:

- All twelve tables have approved records and rich APIs.
- Polygon/MultiPolygon and route-part behavior is supported by schema evidence
  and synthetic multipart tests.
- The complete coverage report has no operational table lacking a rich object
  or rich child collection.

## Compatibility policy

Throughout the `1.x` release series:

- Prefer compatibility aliases and deprecation warnings over abrupt removals.
- Deprecations must identify the replacement and planned removal version.
- Keep `nasr["TABLE_NAME"]` working when the internal table repository changes.
- Keep direct constructors such as `Airport("BWI", nasr)` working while adding
  facade methods.
- Preserve uppercase FAA column names in raw records and DataFrames.
- Do not guarantee undocumented internal attributes.

Provide a lightweight top-level `nasr` namespace compatibility shim if existing
users are known to depend on it. Do not restore a second full implementation
tree. Remove the shim no earlier than `2.0.0` and only after deprecation and
migration documentation.

## Testing matrix

Each feature should be covered at the lowest appropriate level:

| Area | Unit tests | Fixture integration | Optional real-cycle test |
| --- | --- | --- | --- |
| Date and cycle parsing | Required | Required | Optional |
| Archive validation/extraction | Required | Required | Not needed |
| HTTP download handling | Mocked | Mocked | Manual/optional |
| CSV table loading | Required | Required | Recommended |
| Airport lookup | Required | Required | Recommended |
| Fix/navaid lookup | Required | Required | Recommended |
| ARTCC geometry | Required | Required | Recommended |
| Coordinate conversion | Required | Not needed | Not needed |
| Plotting | Required with Agg | Required | Optional |
| Packaging | Not applicable | Wheel inspection | Not needed |

Required verification commands after the tooling milestone:

```bash
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy openNASR
python -m build
python -m twine check dist/*
```

Agents may run focused subsets during development, but the entire set is the
release gate.

## Security and reliability requirements

- Treat ZIP archives and downloaded content as untrusted input.
- Prevent path traversal during extraction.
- Use bounded streaming reads and timeouts for network operations.
- Do not disable TLS verification.
- Do not execute files from an FAA archive.
- Avoid unsafe deserialization formats for metadata and caches.
- Use atomic writes for archives, metadata, and extracted-cycle publication.
- Ensure concurrent readers never observe a partially extracted cycle.
- Use a lock around download/extraction publication if concurrent processes are
  supported.
- Include the original exception as the cause when wrapping low-level errors.
- Do not catch `Exception` unless cleanup is followed by a deliberate re-raise
  or a well-scoped typed exception.

## Performance and resource requirements

- Do not load all FAA CSV tables merely to construct `NASR`.
- Do not copy complete DataFrames unless requested.
- Do not repeatedly build the same identifier index.
- Stream large downloads and extraction operations.
- Avoid checking large archives into source control or package artifacts.
- Make cache removal explicit; never automatically delete a user's only local
  cycle.
- Provide enough logging for long downloads and extractions without printing
  from ordinary lookup methods.

## Documentation standards

- Examples must use public APIs and be covered by tests when practical.
- Public methods require docstrings describing parameters, returns, exceptions,
  coordinate order, and units.
- Use FAA terminology but explain abbreviations on first use.
- Clearly distinguish FAA identifiers from ICAO identifiers.
- Avoid promises about FAA schema stability.
- Keep the non-operational-use disclaimer visible.
- Do not instruct users to write data inside `site-packages` once cycle
  management is implemented.

## Explicit non-goals for the initial stable release

- Certifying data for operational navigation or flight dispatch.
- Replacing official FAA publications or NOTAM services.
- Editing or submitting FAA source data.
- Providing a graphical desktop application.
- Supporting arbitrary AIXM, shapefile, and legacy text formats in the first
  stable release. CSV is the priority.
- Building a remote database service.
- Automatically combining NASR with live traffic or weather feeds.
- Guaranteeing every historical NASR schema without representative test data.

## Suggested commit sequence

Keep commits reviewable and independently testable. A recommended sequence is:

1. `build: migrate packaging and add development tooling`
2. `test: add supported schema manifests and bootstrap fixtures`
3. `fix: add typed exception hierarchy`
4. `fix: repair record collections and typed lookup errors`
5. `fix: make cycle selection exact and failures explicit`
6. `feat: add schema parsing and table registry inventory layer`
7. `test: replace manual scripts with deterministic pytest coverage`
8. `feat: add external cycle cache manager`
9. `feat: import and safely extract NASR archives`
10. `feat: add explicit FAA cycle downloads and update checks`
11. `feat: add opennasr data management CLI`
12. `perf: load and index NASR tables lazily`
13. `refactor: normalize core domain repositories and rich objects`
14. `fix: harden coordinate and boundary geometry`
15. `refactor: isolate optional plotting support`
16. `docs: publish API and migration guidance`
17. `ci: enforce lint, type-check, and package checks`
18. `feat: add airport-linked airspace and military operations`
19. `feat: add airway holding and communications objects`
20. `feat: add procedure and preferred-route objects`
21. `feat: add facility weather and identifier objects`
22. `feat: add special-use and military airspace objects`

Do not combine all milestones into one large commit.

## Definition of done

A task is done only when:

- implementation and regression tests are present;
- relevant tests pass;
- public behavior is documented;
- backward compatibility is preserved or intentionally deprecated;
- errors are actionable and typed;
- no generated data or unrelated changes are included;
- this plan accurately reflects the remaining work.

The project is ready for its initial stable release only when Milestones 0,
0B, 1, 1B, and 2 through 7 meet their acceptance criteria and no P1 or P2
correctness issue is known to remain. The complete rich-object objective is done
only when Milestones 8-12 also meet their acceptance criteria and the coverage
report has no operational table without a rich API.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-08-15 | Store NASR cycles in a user cache, not the Python package. | FAA datasets are large, mutable runtime data and must not be shipped in wheels. |
| 2026-08-15 | Check FAA cycle metadata during package import, while keeping archive downloads explicit through `download()` or `download_latest()`. | The user wants immediate notice of newer data without automatic large downloads. |
| 2026-08-15 | Keep import-time update-check failures silent and non-fatal. | Offline use and temporary FAA-service failures must never make the Python package unavailable. |
| 2026-08-15 | Cache successful FAA cycle update checks for 24 hours, support `force=True`, and do not treat failed checks as successful cache results. | Repeated imports should avoid unnecessary FAA requests while callers can request an immediate refresh and transient failures remain retryable. |
| 2026-08-15 | Provide an `opennasr` CLI for `check`, `download`, `list`, and `remove`; keep aviation queries in Python. | Users need a simple way to manage large cycle files without duplicating domain-query APIs in the terminal. |
| 2026-08-15 | Gate `1.0.0` on strict raw support for both schemas, core rich objects, cycle management, update notification, CLI, tests, documentation, packaging, and CI; deliver remaining rich families in numbered `1.x` milestones. | This provides a dependable first stable release without abandoning complete rich-object coverage. |
| 2026-08-15 | Use exact semantics for an explicitly requested cycle. | Silent fallback can produce incorrect time-dependent aviation results. |
| 2026-08-15 | Load tables lazily and cache them per `NASR` instance. | Eagerly parsing every CSV wastes startup time and memory for narrow queries. |
| 2026-08-15 | Preserve raw FAA tables and fields alongside typed objects. | Advanced consumers need fields not yet represented by domain properties. |
| 2026-08-15 | Keep legacy constructors and uppercase class aliases temporarily. | Existing users need a migration path while the API becomes consistent. |
| 2026-08-15 | Use small local fixtures for default tests. | Tests must be deterministic, fast, and independent of network and multi-gigabyte datasets. |
| 2026-08-15 | Defer Ruff/mypy enforcement (Milestone 0) to a required CI gate only in Milestone 7 (Task 7.10). | Milestones 1-6 rewrite most of the source tree; gating on strict lint/type checks before that churn wastes agent effort on code about to be replaced. |
| 2026-08-15 | Split full 63-table/87-file CSV coverage out of the `1.0.0` scope; only raw coverage of all tables plus record/domain coverage of the already-public families (airport, fix, navaid, ARTCC) is required for `1.0.0`. | The complete coverage matrix is a multi-month follow-on effort; conflating it with `1.0.0` blocked a clear release definition and left Milestone 7's acceptance criteria silent on how much of the matrix was actually required. |
| 2026-08-15 | Add Milestone 0B before correctness work and retain Milestone 1B for the inventory/schema implementation. | Regression and schema tests require deterministic supported-schema manifests and fixtures before implementation begins. |
| 2026-08-15 | Delete `tests/main_test_NASR.py` outright rather than converting it (Milestone 2, Task 2.10). | It imports the already-removed top-level `nasr` package and depends on a third-party `trino`/OpenSky connection with a hardcoded username; it cannot run and is out of `openNASR`'s scope. |
| 2026-08-15 | Provide rich domain objects for all 63 operational tables, using standalone rich objects where no reliable parent relationship exists. | The user wants a consistently object-oriented API while avoiding invented cross-table joins. |
| 2026-08-15 | Treat schema drift as an error during normal loading and expose unfamiliar raw data only through explicit diagnostic inspection mode. | FAA format changes require code, registry, fixture, and documentation review rather than silent best-effort parsing. |
| 2026-08-15 | Preserve exact FAA CSV text in the raw layer and perform validated conversions only in rich-object properties. | Users need both source fidelity and convenient Python values without pandas inference corrupting identifiers or empty fields. |
| 2026-08-15 | Assign all post-`1.0.0` rich-object families to Milestones 8-12 (`1.1.0` through `1.5.0`). | Complete rich coverage must have an executable owner and cannot depend on another user request. |
| 2026-08-15 | Treat `FILESTYPES.md` as authoritative for approved module and API names. | A single naming source prevents the plan and implementation from drifting. |
| 2026-08-16 | Support Python 3.10 and newer. | Python 3.10 is the plan's default baseline, and the current source uses no feature requiring a newer minimum. |
| 2026-08-16 | Define the supported inventory as 63 operational tables plus 24 schema-description files in both 2026 manifests; remove plan-only `AWY_ALT` and `AWY_SEG` entries and model `AWY_SEG_ALT` as `AirwaySegmentRecord`. | Both official packages contain the same 87 CSV files, and neither contains `AWY_ALT` or `AWY_SEG`; `AWY_SEG_ALT` contains the ordered segment and altitude fields. |
