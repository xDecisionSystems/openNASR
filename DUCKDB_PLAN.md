# DuckDB Storage and Query Acceleration Plan

## Goal

Make repeated openNASR use substantially faster—locally and as the data layer
for a future web service—by converting each validated FAA NASR cycle into an
immutable, queryable DuckDB representation. The implementation must preserve
the library's current CSV/Pandas API, exact historical-date behavior, and raw
FAA source fidelity while making DuckDB an optional acceleration path.

## Objective

Add an optional, local DuckDB backend that makes repeated use of an imported
FAA NASR cycle faster without changing the library's existing CSV/Pandas
contract. The backend must support exact historical-cycle selection and provide
a sound base for a later FastAPI service.

This is a performance feature, not a replacement for FAA source data. A NASR
archive and its extracted CSV files remain the source of record.

## Non-negotiable product rules

- Preserve `NASR`, `CycleManager`, repositories, legacy constructors, and
  `nasr["TABLE"]` behavior. Existing callers must continue to receive pandas
  `DataFrame` objects.
- DuckDB is optional. Installing `openNASR` without the DuckDB extra must keep
  working exactly as it does today.
- Keep one immutable database per exact FAA effective date. Never answer a
  requested date with a different cycle.
- Preserve FAA source values losslessly, including leading zeroes, blank
  values, and schema-specific text fields. Do not rely on automatic type
  inference during ingestion.
- Do not commit archives, extracted cycles, databases, generated benchmarks,
  or credentials.
- Database creation must be atomic, validated, repeatable, and safe if it is
  interrupted. A bad/incomplete database must never be selected for reads.
- No runtime download, extension installation, or network access is introduced
  by this feature.

## Target user experience

The initial release should be explicit and opt-in:

```python
from openNASR import CycleManager, NASR

cycles = CycleManager()
cycles.build_duckdb("2026-08-06")

# Same public repositories and DataFrame table API as CSV mode.
nasr = NASR(cycle="2026-08-06", storage="duckdb")
airport = nasr.airports.get("ATL")
table = nasr.table("APT_BASE")
```

`storage="csv"` remains the default for the first release. A later release may
add `storage="auto"`, but only after benchmarks demonstrate a material benefit
and its fallback behavior is documented.

Databases live beside their immutable extracted cycle:

```text
<cache>/cycles/2026-08-06/
├── CSV_Data/...                 # existing extracted FAA data
├── nasr.duckdb                  # completed DuckDB representation
└── nasr.duckdb.json             # provenance and compatibility metadata
```

The metadata must include at least: effective date, archive SHA-256 when
available, source CSV schema fingerprint, openNASR storage-format version,
DuckDB version, creation time, and table row counts.

## Architecture decisions to validate early

1. **Raw fidelity first.** Import raw NASR tables using explicitly declared
   string columns. Any typed/analytic columns are additive views or generated
   columns; they never replace the raw source representation.
2. **Backend boundary.** Introduce a small table-store protocol below `NASR`:
   discover table names, load one table as a DataFrame, tell whether it is
   loaded, and build a normalized lookup index. `TableRepository` becomes the
   CSV implementation; `DuckDbTableRepository` implements the same behavior.
3. **Atomic publishing.** Build into a uniquely named temporary database in
   the target directory, validate it, write metadata, then atomically replace
   the final database and sidecar. Preserve a previous valid database until a
   replacement is fully validated.
4. **Read-only normal operation.** `NASR(storage="duckdb")` opens the completed
   per-cycle database read-only. Ingestion is the only writer and is protected
   by a per-cycle lock.
5. **No blind indexing.** Begin with primary lookup and relationship columns
   defined by `TableRegistry`; benchmark every proposed DuckDB index against a
   scan before retaining it. Do not create indexes for all columns.
6. **Spatial scope is deferred.** DuckDB spatial support is not required for
   the first backend release. Existing Shapely plotting/geometry remains
   unchanged. A later task may evaluate a separately installed spatial
   extension or PostGIS for web-service spatial workloads.

## Agent roster and roles

Agent names below are roles, not fixed individuals — any capable agent may be
assigned a role for a given task, but each in-flight task has exactly one
owning agent at a time.

| Role | Responsibility |
| --- | --- |
| **Sol** | Architecture, protocol/contract design, security and compatibility review, gate approval, performance/benchmark design. Sol does not write backend implementation code; Sol reviews it. |
| **Terra** | Production implementation: storage format, builder, table-store backend, public `NASR`/`CycleManager` API, packaging, query acceleration. |
| **Luna** | Fixtures, parity/regression tests, CLI surface, documentation, benchmark tooling. Luna does not change production behavior; Luna's tests must fail against a broken implementation and pass against a correct one. |

If a phase's suggested-schedule table names a role with no available agent,
reassign the task to another role rather than leaving it unowned — the goal
is one clear owner per task, not adherence to a specific name.

## Coordination rules for parallel agents

- **Branch per task.** Each task in the Delivery sequence is done on its own
  branch, named `duckdb/<task-id>-<short-slug>` (e.g. `duckdb/13.1.3-builder`).
  Do not share a branch across two open tasks, even within the same phase —
  two agents editing the same file on one branch is exactly the collision
  this plan needs to avoid.
- **File-ownership map.** Before starting a task that touches a file listed
  in "New and shared files" below, confirm no other *currently open* task
  claims the same file. Where the table's "Later editors" column names a
  task, that task must not open its branch until the file's prior editor has
  merged — rebase onto that merge rather than editing the file in parallel
  from an older base.
- **Merge order follows task order, not wall-clock completion.** Within a
  phase, merge branches in ascending task-ID order (13.1.1 before 13.1.2,
  etc.) even if a later task finishes first. A task that depends on another
  (see each task's `Dependencies:` line) must not open its branch until its
  dependency has merged to the integration branch.
- **Integration branch.** All phase branches merge into a long-lived
  `duckdb/integration` branch, not directly into `main`. Nothing from this
  plan reaches `main` before Gate 13.5 passes on `duckdb/integration`.
- **Every agent reads** this file, `PLAN.md`, `README.md`, `pyproject.toml`,
  and every file its task will touch, before editing.
- **Each task ends with focused tests** scoped to that task. The agent
  merging last in a phase (by the task-ID order above) runs the complete
  suite, Ruff, mypy, build, and Twine checks on the merged phase branch
  before requesting the phase gate.
- **Gate authority.** Only the role named in a phase's `**Gate 13.x:**` line
  may record that gate as passed (Sol for every gate in this plan). A gate
  is recorded by adding a dated row to the Decision log naming the gate,
  not by checking off a task box. No task in the next phase may open its
  branch until its phase's gate row exists in the Decision log.
- Every implementation task adds a decision-log row to this file if it
  changes the storage format, public API, or compatibility policy.
- Commit one task at a time with a narrow conventional commit referencing
  the task ID (e.g. `feat(duckdb): 13.1.3 per-cycle builder`). Do not mix
  benchmark output or cache contents into commits.

## New and shared files

Naming new files up front lets two agents on different tasks avoid guessing
at each other's module boundaries. Task IDs mark who creates or first
populates a file; other tasks that later touch the same file are listed
under "later editors" so the collision is visible before either starts.

| File | Created by | Purpose | Later editors |
| --- | --- | --- | --- |
| `openNASR/duckdb_metadata.py` | 13.1.1 | `DuckDbCycleMetadata`, storage-format version constant, metadata validation/typed errors | — |
| `tests/fixtures/duckdb_parity/` | 13.1.2 | Tiny synthetic multi-table fixtures shared by CSV/DuckDB parity tests | 13.2.3 (adds cases, does not restructure) |
| `openNASR/duckdb_builder.py` | 13.1.3 | Per-cycle DuckDB builder: import, validate, publish | 13.1.4 (concurrency/atomicity additions to the same module) |
| `openNASR/storage.py` | 13.2.1 | The minimal table-store protocol extracted from `TableRepository`; `TableRepository` itself stays in `openNASR/tables.py` and is updated in place to satisfy the protocol | — |
| `openNASR/duckdb_tables.py` | 13.2.2 | `DuckDbTableRepository` | — |
| `openNASR/cycles.py` (existing, shared) | — | `CycleManager.build_duckdb`/`duckdb_path`/`remove(duckdb=True)` land here | 13.3.1 opens this file first; no other task in this plan edits it — if a future task needs to, it must rebase onto 13.3.1's merge |
| `openNASR/nasr.py` (existing, shared) | — | `storage=` kwarg on `NASR.__init__` | 13.3.2 only; sequenced after 13.3.1 and 13.2.4 so it never overlaps another open edit to this file |
| `openNASR/cli.py` (existing, shared) | — | `build-duckdb`, `list --storage` subcommands | 13.3.3 only |
| `openNASR/registry.py` (existing, shared) | — | Read-only: 13.4.2 reads `TableRegistry` identity/relationship keys to choose indexes; it does not edit this file | — |

Any task that needs a new file not listed here adds a row to this table in
the same commit that creates the file.

## Delivery sequence

### Phase 13.0 — Discovery and contract (blocking)

- [x] **13.0.1 — Agent: Sol.** Audit every current `TableRepository` caller,
  including repositories, schema validation, direct mapping access, and tests.
  Produce a concise compatibility matrix identifying which methods must be
  preserved by the table-store protocol.

  Acceptance: matrix is checked into this document or a linked design note;
  it covers `__getitem__`, `table(copy=)`, iteration, available tables,
  indexes, schema validation, and DataFrame mutation semantics.

- [x] **13.0.2 — Agent: Sol.** Create a representative benchmark specification
  using the real current cycle plus committed small fixtures. Measure CSV
  construction, first table access, repeated table access, airport/fix/navaid
  identity lookup, airway relationship lookup, and cold/warm DuckDB access.

  Acceptance: benchmark commands, machine metadata, data-size reporting, and
  a pass/fail performance target are documented. Benchmarks do not run in CI
  and do not commit FAA data.

#### 13.0 table-store compatibility audit

The only production object that constructs `TableRepository` is `NASR`.
`NASR` wraps it and passes its own `Mapping[str, DataFrame]` surface to every
domain repository. The current airport/fix/navaid, airspace, airway, holding,
communications, procedure, ATC/radar, weather, FSS, location, and military
repositories therefore consume `__getitem__` and optional-table `get`, not a
concrete `TableRepository`. The same is true of `relationships.py`,
`flightplan.py`, plotting helpers, and the legacy Airport/ARB/FIX/NAVAID
paths. This is the backend seam: none of those callers may need a storage-mode
branch.

Direct `TableRepository` callers are `NASR.setupFiles`/`NASR.table`, the
repository unit tests, and the schema-catalog tests that load a synthetic row.
The facade and fixture/error-path tests additionally exercise the observable
mapping, lazy-loading, validation, and mutation behavior. The resulting
compatibility matrix is:

| Surface or caller | Current observable behavior | Table-store obligation |
| --- | --- | --- |
| `available_tables` | Sorted, canonical uppercase tuple discovered without reading table contents; includes operational and schema-description CSVs. | Required protocol property. DuckDB obtains it from validated metadata/catalog state, with the same names and stable ordering. |
| `load(name)` | Strips and uppercases `name`, lazily creates one DataFrame, caches it per repository instance, returns the identical object thereafter, and raises `TableNotFoundError` for an absent table. CSV retries Latin-1 only after `UnicodeDecodeError`; unrelated parser errors propagate. | Required protocol method. Encoding retry is CSV-specific, but names, exception type, laziness, identity, columns, row order, and cell values are backend-independent. |
| `table(name, copy=False)` | Aliases the cached frame. `copy=True` returns a deep DataFrame copy. | Required protocol method and public compatibility behavior. |
| `is_loaded(name)` | Normalized, per-instance cache-membership check; it does not trigger a load. | Required protocol method. |
| `index(name, column)` | Lazily caches exact string-value to row-position tuples; duplicate values retain source row order. | Required protocol method. It may be implemented from the cached frame; no physical DuckDB index is implied. |
| `normalized_index(name, column)` | Lazily caches `str(value).strip().upper()` to row-position tuples; duplicates retain source row order. | Required protocol method. It must have identical normalization, positions, duplicate handling, and cache reuse. |
| `__getitem__` | Equivalent to `load`; this is direct legacy access on `TableRepository` and the basis of `nasr["TABLE"]`. | Required mapping adapter over `load`. |
| `__iter__`, `__len__`, `keys` | Iterate/count the stable available-table set without loading frames. | `__iter__` and `__len__` are required mapping adapters; `Mapping` derives `keys`. |
| Membership and `get` | Inherited `TableRepository` mapping operations route through `__getitem__` and can therefore load a valid table. Domain code sees `NASR`, whose explicit `__contains__` normalizes strings without loading and whose `get` returns its default only for absence while preserving `SchemaMismatchError`. | Preserve the `NASR` facade behavior. Direct store-level inherited behavior remains compatible but is not a separate protocol primitive. |
| `NASR.get(name, default)` and domain optional tables | A genuinely absent table returns the default; `SchemaMismatchError` is never hidden as absence. | Remains a facade/mapping responsibility. A backend must raise the same missing-table and validation exceptions so this distinction survives. |
| Whole-cycle schema checks | During construction, `NASR` identifies the schema and rejects unmodeled operational tables without loading operational DataFrames. | Remains above the table-store boundary. The DuckDB metadata/catalog must expose enough trusted table/schema information for the same check. |
| Per-table schema validation | On first access, `NASR._load_table` passes the loaded frame to `SchemaCatalog.validate(...).require_compatible`; later cached access is not revalidated. `APT_BASE.ARPT_ID` has an additional facade check. Direct `TableRepository.load` does not validate. | Remains above the table-store boundary and must run exactly once before a newly loaded frame is exposed through `NASR`. The store must not make invalid data look absent. |
| Domain repositories and relationship helpers | Receive `Mapping[str, DataFrame]`; use `[]` for required tables, `get` for optional tables, pandas filtering/grouping, source row order, and their own cached normalized/grouped indexes. | No new protocol calls. CSV and DuckDB must present equivalent frames, mapping exceptions, and ordering. Repository-local indexes are distinct from table-store/physical indexes. |
| Direct mutation | `load`, `table(copy=False)`, and `__getitem__` expose shared per-instance state, so mutation is visible on subsequent accesses in that instance. A deep copy is isolated. Existing row-position indexes can become stale if callers mutate after building them. | Preserve shared-versus-copy behavior through Gate 13.2. Mutation affects only the in-memory frame and must never write through to CSV or immutable DuckDB. Task 13.2.4 decides whether stale-index behavior needs an explicit guard. |

The minimal structural protocol for 13.2.1 is therefore
`available_tables`, `load`, `table`, `is_loaded`, `index`, and
`normalized_index`, plus the `Mapping` adapters `__getitem__`, `__iter__`, and
`__len__`. `table_path`, `cycle_path`, pandas `read_options`, encoding retry,
DuckDB connections, SQL, and physical database indexes are implementation
details and are not protocol members. Public imports of
`openNASR.tables.TableRepository` and its CSV behavior remain unchanged.

#### 13.0 benchmark specification

The benchmark runner added by 13.4.4 must implement the command contract
below. It is a manual tool, excluded from pytest collection and CI. Output
must be written outside the repository (or to an ignored caller-selected
scratch directory), and the runner must refuse to download data or select a
different cycle.

```bash
export OPENNASR_BENCHMARK_CACHE=/absolute/path/to/an/existing/cache
export OPENNASR_BENCHMARK_OUTPUT=/absolute/path/outside/the/repository

# Build/read benchmark on the exact real current cycle. The runner builds any
# timed database in an isolated temporary copy; it does not replace the user's
# canonical artifact.
python -m tools.duckdb_benchmark run \
  --cache-dir "$OPENNASR_BENCHMARK_CACHE" \
  --cycle 2026-08-06 \
  --include-build \
  --cold-repetitions 9 \
  --warm-repetitions 5 \
  --warm-iterations 200 \
  --output "$OPENNASR_BENCHMARK_OUTPUT/real-2026-08-06.json"

# Reproducible small-data coverage for both supported schema generations.
python -m tools.duckdb_benchmark run-fixtures \
  --fixtures tests/fixtures/duckdb_parity \
  --cold-repetitions 9 \
  --warm-repetitions 5 \
  --warm-iterations 200 \
  --output "$OPENNASR_BENCHMARK_OUTPUT/fixtures.json"

# Compare a no-index baseline with an index candidate built from the same DB.
python -m tools.duckdb_benchmark compare-index \
  --baseline "$OPENNASR_BENCHMARK_OUTPUT/real-2026-08-06-no-index.json" \
  --candidate "$OPENNASR_BENCHMARK_OUTPUT/real-2026-08-06-index.json"
```

The real dataset is the locally supplied FAA cycle effective `2026-08-06`,
selected exactly. If it is unavailable, the report is incomplete and cannot
pass the performance gate; the runner must not substitute `latest`. The small
datasets are the committed `tests/fixtures/duckdb_parity/` fixtures created by
13.1.2 for both `pre_2026_09` and `nasr_2026_09`. Until those land, the current
`core/pre_2026_09` fixture may be used only for runner development, not for a
final Gate 13.4 report. Fixture results establish correctness and catch gross
regressions but have no latency threshold because timer overhead dominates
their tiny tables. FAA archives, extracted cycles, databases, and generated
JSON/Markdown reports are never committed.

Each backend must run the same preselected keys and workload order. Key
selection happens outside timed regions and is recorded in the report: choose
up to nine unique, nonblank keys spread deterministically across the sorted
source rows. Airport, fix, and navaid use their registry identity columns;
airway uses a complete `AWY_BASE` composite key known to have at least one
`AWY_SEG_ALT` child. Include a not-found key for each identity lookup, but
report hits and misses separately. Assert equal public values, ordering,
DataFrame dtypes/cells, and exception classes before accepting timings.

| Workload | Timed operation and cache state | Reported measures |
| --- | --- | --- |
| Build | Build and validate a new database from the same extracted cycle in a fresh temporary target. | Wall time, CPU time, peak RSS, CSV bytes, DB/sidecar bytes, table/row counts. |
| Construction | `NASR(cycle=exact_date, storage=...)` in a fresh subprocess; no operational table has been accessed. | CSV and process-cold DuckDB median/p95 wall time and peak RSS. |
| First table access | `nasr.table("APT_BASE")` once on a newly constructed instance; construction time excluded. | Median/p95 latency, RSS increment, rows/columns/bytes materialized. |
| Repeated table access | After one untimed prime, call `nasr.table("APT_BASE")` on the same instance and verify object identity; measure batches of 200 calls. Repeat with `copy=True` separately. | Per-call median/p95 and copy cost. |
| Identity lookup | `airports.get`, `fixes.get`, and `navaids.get` for the preselected hit/miss keys. First lookup uses a new instance; warm lookup repeats on one primed repository. | Per-family hit/miss median/p95, tables materialized, peak RSS. |
| Relationship lookup | `airways.get(complete_key)` including ordered segment assembly. First lookup uses a new instance; warm lookup repeats on one primed repository. | Hit/miss median/p95, returned child count/order, tables materialized, peak RSS. |
| DuckDB cold/warm access | “Cold” means a fresh Python process, read-only connection, and empty application DataFrame/index caches. “Warm” means the same process/`NASR` instance after one untimed access. | Connection/construction, first materialization/query, and repeated cached access separately. |

Do not drop operating-system caches or claim filesystem-cold results. Run on
an otherwise idle machine, alternate CSV/DuckDB sample order, disable GC only
inside identical timed regions, use `perf_counter_ns`, and retain all samples
alongside median, p95, minimum, and median absolute deviation. A subprocess is
the unit of every cold repetition; warm repetitions use a new subprocess but
multiple iterations within one instance. The report must capture:

- UTC timestamp; OS, kernel, architecture; CPU model/logical count/governor;
  total RAM; filesystem/mount type and whether storage is rotational;
- Python, openNASR, pandas, and DuckDB versions; Git commit and dirty state;
  benchmark arguments and relevant environment variables;
- exact effective date, source archive name/SHA-256 when available, schema ID
  and fingerprint, table/file count, per-table and total row count, total CSV
  bytes, archive bytes, DuckDB bytes, sidecar bytes, and storage-format version;
- the selected lookup keys, index definitions, index build time/size delta,
  failure/skip reasons, and raw timing/RSS samples.

Performance is evaluated only after full CSV/DuckDB parity passes. The real
cycle passes the first-release performance target when all of these hold:

1. Process-cold DuckDB construction median is at most 50% of CSV construction.
2. Across first `APT_BASE` access plus first airport, fix, navaid, and airway
   lookups, the geometric-mean speedup is at least 2.0x and at least four of
   the five workloads improve by at least 1.5x.
3. No warm/repeated workload regresses beyond the noise allowance:
   `duckdb_median <= max(1.20 * csv_median, csv_median + 0.25 ms)`, and DuckDB
   p95 is no more than 1.25x CSV p95 plus 0.25 ms.
4. Build time, peak RSS, and disk size are reported and reviewed; they are not
   hidden by the latency pass. A result that swaps a latency win for more than
   2x CSV peak RSS during the corresponding repository lookup requires a
   decision-log exception before Gate 13.4 can pass.

An individual physical DuckDB index is retained only if an A/B run on the
same database and keys improves candidate-query median latency by at least 25%
and p95 by at least 10%, with no correctness change, while its build time and
database-size delta are reported. Otherwise the scan remains the approved
implementation. Results from different machines, cycles, schema fingerprints,
or dirty commits are not combined into one pass/fail comparison.

- [x] **13.0.3 — Agent: Terra.** Add the optional dependency group
  `duckdb = ["duckdb>=<approved minimum>"]` only after Sol confirms a tested
  compatible version range. Update installation documentation; do not make it
  a base dependency.

  Acceptance: a fresh `pip install -e '.[duckdb]'` succeeds and the base
  `pip install -e .` still imports with no DuckDB installed.

**Gate 13.0:** Sol approves the protocol and raw-fidelity strategy. No runtime
backend code begins until this gate is recorded in the decision log.

### Phase 13.1 — Storage format and safe ingestion

- [x] **13.1.1 — Agent: Terra.** Define `DuckDbCycleMetadata` and a
  storage-format version. Add strict metadata validation with typed errors for
  date mismatch, unsupported storage version, missing table, schema
  fingerprint mismatch, and incomplete build.

  Acceptance: unit tests cover valid metadata, each invalid condition, and
  sidecar atomicity. No raw exception leaks from metadata parsing.

- [x] **13.1.2 — Agent: Luna.** Add small synthetic multi-table fixtures that
  exercise leading zeroes, empty strings, commas/newlines, non-ASCII text,
  duplicate identifiers, and a 2026.09-style schema fixture.

  Acceptance: fixtures are tiny, committed text only, and shared by CSV/DuckDB
  parity tests. No FAA archive is added.

- [x] **13.1.3 — Agent: Terra.** Implement a per-cycle DuckDB builder that
  imports every discovered operational CSV table with explicit source-text
  preservation, records row counts/fingerprints, and validates all tables
  before publish.

  Dependencies: 13.0.1, 13.1.1, 13.1.2.

  Acceptance: a database built from each supported schema fixture has the same
  table names, columns, row counts, and source cell values as CSV loading.

- [x] **13.1.4 — Agent: Terra.** Make builder publication concurrency-safe:
  per-cycle lock, temporary database/sidecar, cleanup on error, atomic publish,
  and read-only completed database opening.

  Dependencies: 13.1.3.

  Acceptance: concurrent-build, interrupted-build, stale-temp, and
  pre-existing-valid-database tests pass. A reader never observes a partial
  database.

- [ ] **13.1.5 — Agent: Sol.** Security review ingestion paths, SQL object
  quoting, temporary file handling, lock behavior, and metadata provenance.

  Acceptance: review findings are resolved or recorded with explicit approval
  and follow-up tasks; `git diff --check` and security-focused tests pass.

**Gate 13.1:** A database can be built twice from the same fixture with stable
observable contents; corrupted/partial artifacts are rejected.

### Phase 13.2 — Table-store abstraction and parity

- [x] **13.2.1 — Agent: Terra.** Extract a minimal internal table-store
  protocol from `TableRepository` without changing CSV behavior. Keep
  `TableRepository` as the reference implementation.

  Acceptance: all current tests pass unchanged except intentional new protocol
  tests; no public import path moves.

- [ ] **13.2.2 — Agent: Terra.** Implement `DuckDbTableRepository` against the
  completed database. `table()`/`__getitem__` return cached pandas DataFrames,
  honor `copy=True`, and expose the same normalized-index semantics as CSV.

  Dependencies: 13.1.4, 13.2.1.

  Acceptance: parameterized CSV-vs-DuckDB tests pass across both supported
  schema fixtures for table access, copies, iteration, missing tables, and
  normalized indexes.

- [ ] **13.2.3 — Agent: Luna.** Add parity tests for all public repositories:
  airports, fixes, navaids, airways, procedures, airspace, ILS, and special-use
  records. Compare observable values and public exception types, not internal
  implementation objects.

  Dependencies: 13.2.2.

  Acceptance: every repository fixture test runs in both storage modes; any
  deliberate difference requires an approved decision-log entry.

- [ ] **13.2.4 — Agent: Sol.** Review mutation and cache semantics. Decide and
  document whether a DuckDB-backed DataFrame is cached per `NASR` instance
  exactly like CSV mode, and confirm that user mutation never writes through
  to the immutable database.

  Acceptance: regression tests prove mutation/copy behavior and source
  database immutability.

**Gate 13.2:** CSV and DuckDB modes are behaviorally interchangeable for all
currently public lookup/repository workflows.

### Phase 13.3 — Public lifecycle and exact-date selection

- [ ] **13.3.1 — Agent: Terra.** Add `CycleManager.build_duckdb(cycle)` and
  `CycleManager.duckdb_path(cycle)` using exact ISO date semantics. Add a
  `CycleManager.remove(..., duckdb=True)` option that reports whether the
  database artifact was removed; retain existing default removal behavior.

  Acceptance: exact-cycle, absent-cycle, idempotent build, stale database, and
  selective remove tests pass using temporary cache roots.

- [ ] **13.3.2 — Agent: Terra.** Add `NASR(storage="csv" | "duckdb")` with
  clear typed errors when DuckDB is not installed, no database exists, or a
  database is incompatible with the extracted cycle. Default remains `"csv"`.

  Dependencies: 13.2.4, 13.3.1.

  Acceptance: `NASR(cycle="YYYY-MM-DD", storage="duckdb")` never falls back to
  another cycle or silently rebuilds/downloads. CSV mode remains unchanged.

- [ ] **13.3.3 — Agent: Luna.** Add CLI commands:

  ```text
  opennasr build-duckdb YYYY-MM-DD
  opennasr build-duckdb latest
  opennasr list --storage
  ```

  Dependencies: 13.3.1.

  Acceptance: all CLI tests use mocked providers and temporary caches; output
  identifies effective date, artifact state, and typed failure messages.

- [ ] **13.3.4 — Agent: Luna.** Update README, API docs, cache layout docs,
  migration notes, and examples. Explain `storage="duckdb"`, optional install,
  per-cycle disk use, rebuild/removal behavior, and date reproducibility.

**Gate 13.3:** A user can download/import a cycle, explicitly build its
database, select it by exact date, and remove it without affecting archive or
CSV source data unless explicitly requested.

### Phase 13.4 — Query acceleration and service readiness

- [x] **13.4.1 — Agent: Sol.** Select a small, stable public query surface for
  server use. Prefer typed, parameterized filters over a public raw-SQL
  endpoint. Define pagination, maximum result size, field selection, and error
  semantics.

  Acceptance: proposal names exact endpoints/functions and explicitly defers
  arbitrary SQL execution.

#### 13.4.1 public read-only query contract

The first query surface is one library method and one direct HTTP mapping; it
is intentionally table-oriented so it does not create a second set of domain
record models:

```python
page = nasr.query_table(
    "APT_BASE",
    filters=(QueryFilter.eq("ARPT_ID", "ATL"),),
    fields=("ARPT_ID", "ARPT_NAME", "LAT_DECIMAL", "LONG_DECIMAL"),
    page_size=100,
    cursor=None,
)
```

The exact public Python entry point is
`NASR.query_table(table, *, filters=(), fields=None, page_size=100,
cursor=None) -> QueryPage`. `QueryFilter`, `QueryOperator`, `QueryPage`, and
the query error types live in `openNASR.query` and are re-exported from
`openNASR`. The corresponding future service operation is
`POST /v1/cycles/{cycle}/query`; its JSON body contains `table`, `filters`,
`fields`, `page_size`, and `cursor`, and its response is the JSON form of
`QueryPage`. This plan defines that transport mapping but does not add FastAPI
or an HTTP server.

`QueryFilter` is immutable and has `field`, `operator`, and `value` members.
The first release supports only `QueryOperator.EQ` with one string value and
`QueryOperator.IN` with a non-empty tuple of string values. Filters are joined
with `AND`; `OR`, comparisons, pattern/regular-expression matching, joins,
aggregation, ordering supplied by callers, expressions, and NULL-specific
operators are deferred. Values compare against preserved raw source strings,
so blank string is a valid value and comparisons are case-sensitive. Table
and field identifiers must resolve against the selected cycle's validated
catalog before any statement is prepared. Values are always bound parameters;
identifiers are never accepted as SQL fragments.

`fields` is either `None`, meaning every source field in source order, or a
non-empty tuple of at most 64 field names. Matching table and field names is
case-insensitive after surrounding whitespace is stripped; response keys use
the catalog's canonical names and retain requested field order. Duplicate or
unknown fields are errors, and internal ingestion/order columns are never
selectable. At most eight filters and 100 values across all `IN` filters are
accepted. A query with no matches succeeds with an empty `rows` tuple.

`QueryPage` is immutable and contains `table`, `fields`, `rows`,
`effective_date`, `schema_fingerprint`, `next_cursor`, and
`storage` (`"csv"` or `"duckdb"`). `rows` is an ordered tuple of mappings from
canonical field name to preserved source string. It deliberately omits a
total-count query. Results use source row order with a private source-row
ordinal as the final deterministic tie-breaker; this ordinal is not exposed
as a field. CSV and DuckDB produce byte-for-byte equivalent values and page
boundaries.

Pagination is cursor-based. `page_size` must be from 1 through 1,000. The
default is 100 and the server may configure a lower cap, never a higher one.
The opaque, versioned cursor binds the effective date, schema fingerprint,
canonical table, normalized filters, selected fields, page size, and next
source-row position. Reusing it with any different request or cycle raises
`InvalidQueryCursorError`; expiry is unnecessary because completed cycle
artifacts are immutable. Implementations must additionally stop before an
8 MiB UTF-8 JSON-equivalent page payload and return a smaller non-empty page
with `next_cursor` when possible. If one row alone exceeds 8 MiB,
`QueryResultTooLargeError` is raised. These are library limits; an HTTP
deployment may impose stricter request/body limits.

All query failures are typed beneath `QueryError`:

| Error | Meaning | Suggested HTTP mapping |
| --- | --- | --- |
| `QueryValidationError` | Invalid page size, empty/oversized selection, too many filters/values, or malformed typed value. | 422 |
| `QueryTableNotFoundError` | The requested table is not in the selected cycle's validated catalog. | 404 |
| `QueryFieldNotFoundError` | A selected or filtered field is absent. | 422 |
| `UnsupportedQueryOperatorError` | The operator is not `EQ` or `IN`. | 422 |
| `InvalidQueryCursorError` | Cursor is malformed, unsupported, or does not match the exact query/cycle. | 422 |
| `QueryResultTooLargeError` | One source row cannot fit under the payload cap. | 413 |

Cycle/database absence and incompatibility continue to use the lifecycle
errors defined by 13.1/13.3; the query layer does not relabel them as an empty
result. Storage/driver failures also propagate as typed storage errors rather
than leaking DuckDB exceptions. HTTP error bodies should contain a stable
machine code and message but no SQL, filesystem path, cursor internals, or
bound values.

Arbitrary SQL execution is explicitly outside the public contract. There is
no `NASR.sql`, SQL request field, `/sql` endpoint, or escape hatch accepting a
predicate/order expression. The implementation in 13.4.3 may generate private
read-only SQL for the operations above and must retain the DataFrame fallback
when an operation is unsupported by a backend.

Tests required when 13.4.3 implements this contract:

- parameterize CSV and DuckDB over `EQ`, `IN`, multiple `AND` filters, blank
  values, duplicates, no matches, and both schema-generation fixtures;
- prove projection order, canonical response names, `fields=None`, and
  rejection of empty, duplicate, unknown, internal, and over-64 field lists;
- prove page sizes 1 and 1,000, reject 0 and 1,001, traverse all pages without
  gaps/duplicates, and assert identical backend page boundaries;
- reject malformed/version-mismatched cursors and cursors replayed with a
  different cycle, schema, table, filter, projection, or page size;
- exercise the 8 MiB boundary, early page truncation, one-oversized-row error,
  maximum filter count, maximum aggregate `IN` values, and empty `IN`;
- assert every public error class and proposed HTTP status, and verify messages
  do not expose SQL, bound values, cursor payloads, or local paths;
- use adversarial table/field/value strings to prove identifier allowlisting,
  bound parameters, read-only operation, and the absence of any public raw-SQL
  method or `/sql` route;
- verify result provenance, deterministic source ordering, no total-count
  query, DataFrame fallback behavior, and no mutation of the per-cycle DB.

- [ ] **13.4.2 — Agent: Terra.** Add only benchmark-justified indexes for
  registry identity keys and high-value relationship keys. Record each index,
  its build cost, and measured improvement.

  Dependencies: 13.0.2, 13.2.2.

  Acceptance: no index is retained without a reproducible benchmark; raw-data
  fidelity and parity remain unchanged.

- [ ] **13.4.3 — Agent: Terra.** Add an internal read-only query service that
  permits repositories to avoid materializing whole tables for supported exact
  identity/filter queries, while retaining DataFrame fallback for unsupported
  paths.

  Dependencies: 13.4.1, 13.4.2.

  Acceptance: repository-level benchmark targets are met and all public return
  types/errors match CSV mode.

- [ ] **13.4.4 — Agent: Luna.** Add benchmark tooling and a non-CI benchmark
  report template. Include cold build, warm construction, lookup latency,
  memory, database size, and CSV/DuckDB comparison by exact cycle.

- [ ] **13.4.5 — Agent: Sol.** Produce a FastAPI integration note, not a
  runtime dependency. Specify a lifespan-managed read-only database pool,
  cycle selection via `cycle` or `as_of` (mutually exclusive), response
  provenance, pagination, and deployment limits. Evaluate DuckDB versus
  PostGIS only for spatial multi-user workloads.

**Gate 13.4:** benchmarks prove whether DuckDB is a worthwhile local option;
the FastAPI design can serve immutable exact-date cycle data without exposing
raw SQL or mutable database state.

### Phase 13.5 — Release hardening

- [ ] **13.5.1 — Agent: Terra.** Run the full matrix on every supported Python
  version: base install, `.[duckdb]`, CSV mode, DuckDB mode, absent optional
  dependency, invalid database, both schema fixtures, and exact historical
  cycles.

- [ ] **13.5.2 — Agent: Sol.** Review backward compatibility, atomicity,
  cache removal, disk-growth documentation, source-value fidelity, and date
  semantics. Approve or block release.

- [ ] **13.5.3 — Agent: Terra.** Run the release gate:

  ```bash
  python -m pytest
  python -m ruff format --check .
  python -m ruff check .
  python -m mypy openNASR
  python -m build
  python -m twine check dist/*
  ```

  Acceptance: all commands pass from a clean checkout. Verify both built
  artifacts exclude test fixtures, FAA data, local caches, and `.duckdb` files.

## Suggested parallel schedule

Each wave corresponds to one phase from the Delivery sequence (Wave 1 =
Phase 13.0, Wave 2 = Phase 13.1, and so on); "Dependency" names the prior
wave's gate, which must have its Decision-log row before this wave's
branches open.

| Wave | Agents | Work | Dependency |
| --- | --- | --- | --- |
| 1 | Sol + Terra | 13.0.1/13.0.2 architecture and benchmark contract; 13.0.3 packaging after version decision | none |
| 2 | Terra + Luna | 13.1.1 metadata, 13.1.2 fixtures | 13.0 gate |
| 3 | Terra + Sol | 13.1.3/13.1.4 builder; 13.1.5 security review | 13.1.1/13.1.2 |
| 4 | Terra + Luna + Sol | 13.2.1/13.2.2 protocol/backend, 13.2.3 parity tests, 13.2.4 semantics review | 13.1 gate |
| 5 | Terra + Luna | 13.3.1/13.3.2 lifecycle/API, 13.3.3/13.3.4 CLI/docs | 13.2 gate |
| 6 | Sol + Terra + Luna | 13.4 query design/indexing/backend path, benchmarks, FastAPI note | 13.3 gate |
| 7 | Terra + Sol | 13.5 release matrix and approval | 13.4 gate |

## Explicit non-goals for the first DuckDB release

- Replacing pandas as the public table return type.
- Automatically converting every cached cycle during package import.
- Adding a FastAPI runtime dependency or deploying a web service.
- Downloading DuckDB extensions at runtime.
- Public arbitrary SQL execution.
- Treating a database built from one FAA effective date as valid for another.
- Replacing Shapely plotting geometry or committing generated plots.

## Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-17 | Approve the 13.4.1 read-only query contract: `NASR.query_table(...) -> QueryPage` and the future `POST /v1/cycles/{cycle}/query` mapping support only allowlisted fields, typed `EQ`/`IN` filters, cursor pagination, and bounded projection/results; no public arbitrary-SQL surface is provided. | A narrow parameterized API serves common identity/filter workloads, preserves exact-cycle provenance and CSV/DuckDB parity, and keeps SQL injection, unbounded scans/results, and backend-specific expressions out of the compatibility contract. |
| 2026-08-17 | Plan DuckDB as an explicit optional, per-cycle local storage backend; retain CSV as the default first-release backend. | It accelerates repeated local/API-style queries while preserving the current public DataFrame and repository contract, avoids a forced dependency, and makes source/provenance boundaries clear. |
| 2026-08-17 | Store the database beside the exact extracted cycle and treat it as a rebuildable derivative. | This makes historical-date selection deterministic and permits removal/rebuild without losing the FAA archive or CSV source data. |
| 2026-08-17 | Preserve raw FAA values as strings before adding any typed/analytic views. | NASR fields include identifiers and source text where leading zeroes and blanks are meaningful; automatic database type inference risks silent data changes. |
| 2026-08-17 | Add an agent roster table, a per-task branch/merge/gate-authority protocol, and a "New and shared files" ownership map; require gates to be recorded as dated Decision-log rows rather than task checkboxes. | The task-level `Agent: X` labels and phase gates already implied parallel execution but never said how two agents avoid editing the same file at once, who may declare a gate passed, or where new modules (`duckdb_metadata.py`, `duckdb_builder.py`, `storage.py`, `duckdb_tables.py`) actually live — leaving that implicit risks two agents guessing differently and colliding on `nasr.py`/`cycles.py` mid-phase. |
| 2026-08-17 | Require `duckdb>=1.2.2` only through the explicit `duckdb` optional-dependency extra. | DuckDB 1.2.2 declares Python >=3.7 and has CPython 3.10/3.12 wheels; a clean Python 3.12 install passed both the base-without-DuckDB import and the `.[duckdb]` install/import checks, including an exact-1.2.2 smoke import. |
| 2026-08-17 | Define the table-store contract as cached DataFrame loading, mapping adapters, available/loaded state, and exact/normalized row-position indexes; keep schema validation in `NASR` above the backend boundary. | All domain repositories consume the `NASR` mapping rather than `TableRepository` directly. Preserving that seam avoids storage branches throughout domain code while retaining lazy validation, exceptions, row order, and shared-versus-copy mutation behavior. |
| 2026-08-17 | Gate DuckDB performance on an exact real cycle using process-cold and warm measurements; use committed fixtures for parity rather than latency, require a 2x geometric-mean first-access speedup, and retain physical indexes only after an A/B win. | Tiny fixture timings are dominated by overhead, operating-system cache eviction is not portable, and unmeasured indexes can increase build time and disk use without helping representative repository workloads. |
| 2026-08-17 | Store only text-preserving pandas CSV frames in a versioned DuckDB artifact, with a metadata sidecar carrying source schema and database digests. | A typed import could change zero-padded or blank FAA values; a digest-bound sidecar lets readers reject an incomplete or mismatched database/metadata transition rather than treating it as a completed artifact. |
