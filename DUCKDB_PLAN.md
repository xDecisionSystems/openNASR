# DuckDB Storage and Query Acceleration Plan

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

## Agent operating rules

- Every agent reads this file, `PLAN.md`, `README.md`, `pyproject.toml`, and
  all files touched by its task before editing.
- Each task ends with focused tests. The integration owner runs the complete
  suite, Ruff, mypy, build, and Twine checks before a milestone is marked
  complete.
- Every implementation task adds a decision-log row to this file if it changes
  the storage format, public API, or compatibility policy.
- Commit one task at a time with a narrow conventional commit. Do not mix
  benchmark output or cache contents into commits.

## Delivery sequence

### Phase 13.0 — Discovery and contract (blocking)

- [ ] **13.0.1 — Agent: Sol.** Audit every current `TableRepository` caller,
  including repositories, schema validation, direct mapping access, and tests.
  Produce a concise compatibility matrix identifying which methods must be
  preserved by the table-store protocol.

  Acceptance: matrix is checked into this document or a linked design note;
  it covers `__getitem__`, `table(copy=)`, iteration, available tables,
  indexes, schema validation, and DataFrame mutation semantics.

- [ ] **13.0.2 — Agent: Sol.** Create a representative benchmark specification
  using the real current cycle plus committed small fixtures. Measure CSV
  construction, first table access, repeated table access, airport/fix/navaid
  identity lookup, airway relationship lookup, and cold/warm DuckDB access.

  Acceptance: benchmark commands, machine metadata, data-size reporting, and
  a pass/fail performance target are documented. Benchmarks do not run in CI
  and do not commit FAA data.

- [ ] **13.0.3 — Agent: Terra.** Add the optional dependency group
  `duckdb = ["duckdb>=<approved minimum>"]` only after Sol confirms a tested
  compatible version range. Update installation documentation; do not make it
  a base dependency.

  Acceptance: a fresh `pip install -e '.[duckdb]'` succeeds and the base
  `pip install -e .` still imports with no DuckDB installed.

**Gate 13.0:** Sol approves the protocol and raw-fidelity strategy. No runtime
backend code begins until this gate is recorded in the decision log.

### Phase 13.1 — Storage format and safe ingestion

- [ ] **13.1.1 — Agent: Terra.** Define `DuckDbCycleMetadata` and a
  storage-format version. Add strict metadata validation with typed errors for
  date mismatch, unsupported storage version, missing table, schema
  fingerprint mismatch, and incomplete build.

  Acceptance: unit tests cover valid metadata, each invalid condition, and
  sidecar atomicity. No raw exception leaks from metadata parsing.

- [ ] **13.1.2 — Agent: Luna.** Add small synthetic multi-table fixtures that
  exercise leading zeroes, empty strings, commas/newlines, non-ASCII text,
  duplicate identifiers, and a 2026.09-style schema fixture.

  Acceptance: fixtures are tiny, committed text only, and shared by CSV/DuckDB
  parity tests. No FAA archive is added.

- [ ] **13.1.3 — Agent: Terra.** Implement a per-cycle DuckDB builder that
  imports every discovered operational CSV table with explicit source-text
  preservation, records row counts/fingerprints, and validates all tables
  before publish.

  Dependencies: 13.0.1, 13.1.1, 13.1.2.

  Acceptance: a database built from each supported schema fixture has the same
  table names, columns, row counts, and source cell values as CSV loading.

- [ ] **13.1.4 — Agent: Terra.** Make builder publication concurrency-safe:
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

- [ ] **13.2.1 — Agent: Terra.** Extract a minimal internal table-store
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

- [ ] **13.4.1 — Agent: Sol.** Select a small, stable public query surface for
  server use. Prefer typed, parameterized filters over a public raw-SQL
  endpoint. Define pagination, maximum result size, field selection, and error
  semantics.

  Acceptance: proposal names exact endpoints/functions and explicitly defers
  arbitrary SQL execution.

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
| 2026-08-17 | Plan DuckDB as an explicit optional, per-cycle local storage backend; retain CSV as the default first-release backend. | It accelerates repeated local/API-style queries while preserving the current public DataFrame and repository contract, avoids a forced dependency, and makes source/provenance boundaries clear. |
| 2026-08-17 | Store the database beside the exact extracted cycle and treat it as a rebuildable derivative. | This makes historical-date selection deterministic and permits removal/rebuild without losing the FAA archive or CSV source data. |
| 2026-08-17 | Preserve raw FAA values as strings before adding any typed/analytic views. | NASR fields include identifiers and source text where leading zeroes and blanks are meaningful; automatic database type inference risks silent data changes. |
