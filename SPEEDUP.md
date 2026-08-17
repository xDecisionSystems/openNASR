# Table-Lookup Speedup Plan

## Goal

Remove confirmed unindexed, per-call, full-table lookup cost from openNASR
paths that resolve rows repeatedly. A use of `.to_dict()` is **not** by
itself a defect: optimize only profiler-confirmed lookup hot paths, using the
same technique already proven correct
in `ROUTE_PATH_PLAN.md`'s Phase 4 (`_WaypointResolver`, `_AirwayIndex`):
build a vectorized index once per immutable table set, reuse it across calls,
and never regress raw-value fidelity, public return types, or source
ordering to get there.

This plan now covers three confirmed problem areas, in severity order:

1. **`openNASR/repository.py`'s cached index itself is broken for
   high-cardinality columns** (Phase 2). This is the most severe finding in
   this plan: `AirportRepository`/`FixRepository`/`NavaidRepository` already
   build a cached index — but the index-building technique
   (`dict(tuple(frame.groupby(normalized)))`) is catastrophically slow when
   the grouping column is close to fully unique, which every identifier
   column these repositories index (`FIX_ID`, `ARPT_ID`, `NAV_ID`) is by
   definition. Confirmed 2026-08-17: the very first `nasr.fixes.get(...)`
   call costs **~14.9 seconds**; the first `nasr.airport(...)` call costs
   **~41 seconds**. This affects what looked like the already-fast, modern
   facade, not legacy code.
2. **Every legacy `Raw`/`SimpleNamespace`-based constructor and every
   domain-module repository outside `repository.py`** (Phase 3) —
   `openNASR/basictypes.py`, `fix.py`, `nav.py`, `nasr.py`'s
   `isFix`/`isAirport`/`isNavaid`, and every repository in `atc.py`,
   `communications.py`, `holding.py`, `fss.py`, `locations.py`,
   `military.py`, `weather.py`, `arrivals.py`, `departure.py`, `airway.py`,
   and `airspace.py` — repeat an uncached, full-table `.map()`/`==` scan on
   every call, the same anti-pattern `ROUTE_PATH_PLAN.md` already found and
   fixed in `flightplan.py`'s pre-`_WaypointResolver` code.
3. **`openNASR/flightplan.py`'s procedure-lookup tables and all of
   `openNASR/plotting.py`** (Phase 4, this plan's original scope) — the
   `_WaypointResolver`/`_AirwayIndex` vectorization from
   `ROUTE_PATH_PLAN.md`'s Phase 4 did not cover `_procedure_path`, and
   `plotting.py` was never touched by any prior performance work.

Phase 0/1 audit and measure every call site before any fix, so scope and
priority are set by evidence, not assumption — this already reversed one
earlier conclusion in this plan (see the corrected Decision log entry dated
2026-08-17 "Correction:").

## Non-negotiable product rules

- Preserve every public function/method signature, return type, and
  exception type in every module this plan touches
  (`openNASR.repository`, `openNASR.flightplan`, `openNASR.plotting`, and
  every domain module listed in the Goal above). Speed is an implementation
  change, not an API or behavior change.
- Preserve raw FAA value fidelity and source row/segment ordering exactly.
  An index is a faster way to find the same rows, never a way to
  reorder, deduplicate beyond what the current code already does, or lose a
  row.
- Preserve `RouteResolver`'s existing snapshot/mutation semantics (see
  `ROUTE_PATH_PLAN.md` T4.4): an index reflects the table set at
  construction; callers that mutate a table or switch cycles must construct
  a new resolver/session, not expect live invalidation.
- No new caching layer may introduce cross-cycle or cross-instance state
  leakage. Two `RouteResolver`/plotting-session instances built from
  different NASR table sets must never share cached rows (mirrors the
  existing `test_route_resolver_isolated_between_duckdb_instances` contract).
- No behavior change to CSV/DuckDB parity: a vectorized index must produce
  identical matches whether the underlying tables came from
  `TableRepository` or `DuckDbTableRepository`.
- Benchmarks are diagnostic evidence, not CI gates (matches
  `DUCKDB_PLAN.md`/`ROUTE_PATH_PLAN.md`'s existing convention). Absolute
  timings depend on the benchmark machine; report before/after ratios
  alongside the recorded environment.

## Agent roster and roles

Reuses the Sol/Terra/Luna convention from `DUCKDB_PLAN.md`/
`ROUTE_PATH_PLAN.md`.

| Agent model | Role | Responsibility |
| --- | --- | --- |
| **Sol** | Research/review | Audit which call sites are genuinely slow, design each index's shape, set benchmark methodology, approve gates. Sol does not implement production fixes. |
| **Terra** | Implementation | Production implementation in `repository.py`, scoped domain repositories, `flightplan.py`, and `plotting.py`. Terra owns one production-file set at a time. |
| **Luna** | Tests/tooling | Fixtures, regression tests, benchmark tooling (routes and `plotExamples/`-equivalent plotting calls), documentation. |

## Coordination rules

- **Sequential ownership per file.** Many modules are edited by different
  tasks below (`openNASR/repository.py` in Phase 2, roughly a dozen domain
  modules in Phase 3, `openNASR/flightplan.py` in Phase 4,
  `openNASR/plotting.py` in Phase 5); treat each file the way
  `ROUTE_PATH_PLAN.md` treats `flightplan.py` alone — merge task *N* on a
  file before starting task *N+1* on the same file, even across phases. A
  task touching only one file may run in parallel with an open task on a
  different file. Phase 3's tasks each touch several distinct modules
  (T3.2/T3.3 split by table size, not by file) — confirm no other open
  Phase 3 task is mid-edit on the same module before starting.
- **Every task cites the exact function and line(s) it changes.** Line
  numbers drift fast, especially in `openNASR/flightplan.py`
  (grew from 504 to 931 lines during `ROUTE_PATH_PLAN.md`'s Phase 1-4 work)
  — re-check before citing a new line number in a task, and re-check before
  starting a task that cites one written earlier.
- **Every task ends with a benchmark or regression test that fails (is slow,
  or asserts wrong output) before the fix and passes/speeds up after.**
- **This plan builds on, and must stay consistent with, `ROUTE_PATH_PLAN.md`.**
  Do not duplicate `RouteResolver`, `_WaypointResolver`, or `_AirwayIndex`;
  extend them. If a task here would conflict with an open
  `ROUTE_PATH_PLAN.md` task on the same lines, land the `ROUTE_PATH_PLAN.md`
  task first.
- **Gate authority:** Sol signs off each phase gate (`**Gate N:**`) with a
  dated Decision-log row. The next phase should not start until the prior
  gate is recorded.
- **Every task heading names its assigned model.** Use only `Agent model:
  Sol`, `Agent model: Terra`, or `Agent model: Luna`; do not infer a model
  from the phase title. Sol may review in parallel with Terra; Luna may
  prepare tests or benchmarks in parallel only when it does not modify a
  production file Terra owns.
- **Require a profiler gate before expanding Phase 3.** A module advances
  from the audit list to a Terra implementation task only after the benchmark
  harness records a material repeated-lookup cost on a representative cycle.
  This avoids behavior-risky rewrites of low-frequency compatibility code
  merely because it contains pandas filtering.

## Phase 0 — Audit: which lookups are actually slow

- [x] **S0.1 — Agent model: Sol. Done (2026-08-17), superseding an earlier
  conclusion.** Enumerated every `.to_dict(orient="records")`/`.map()`/
  `groupby` call site across all 40 `openNASR/*.py` modules (not just the 17
  using `.to_dict(orient="records")` — the audit widened after the Phase 2
  finding below, since the worst bug does not use that method at all) and
  classified each as:
  (a) **genuinely vectorized and cached, no fix needed** — confirmed for
  `openNASR/repository.py`'s `_class_airspace`/`_military_operations`
  (small tables, `CLS_ARSP`/`MIL_OPS`, boolean-mask filtered, no caching
  needed at that size) and `ROUTE_PATH_PLAN.md`'s already-fixed
  `_WaypointResolver`/`_AirwayIndex`;
  (b) **cached, but the caching technique itself is broken for
  high-cardinality columns** — `openNASR/repository.py`'s
  `RecordRepository._normalized_index` and `AirportRepository._related_index`
  (Phase 2 below). **Correction to this document's earlier claim:** an
  earlier pass of this audit (see the 2026-08-17 Decision log entry
  "Scope this plan to...") concluded these two methods were "already
  vectorize-then-materialize and already cache" and therefore fine. That
  conclusion checked that a cache existed, not that building it was fast.
  Direct measurement found the opposite: it is the single slowest code path
  in the package;
  (c) **full-table scan per call, no cache at all** — every legacy
  `Raw`/`SimpleNamespace` constructor (`openNASR/basictypes.py`,
  `fix.py`, `nav.py`, `nasr.py`'s `isFix`/`isAirport`/`isNavaid`) and every
  repository outside `repository.py`: `atc.py` (`AtcFacilityRepository`,
  `RadarRepository`), `communications.py`
  (`CommunicationOutletRepository`, `FrequencyRepository`), `holding.py`
  (`HoldingPatternRepository`), `fss.py`
  (`FlightServiceStationRepository`), `locations.py`
  (`LocationIdentifierRepository`), `military.py`
  (`MilitaryOperationRepository`, `MilitaryTrainingRouteRepository`),
  `weather.py` (`AutomatedWeatherStationRepository`,
  `WeatherLocationRepository`), `arrivals.py` (`StarProcedureRepository`),
  `departure.py` (`CodedDepartureRouteRepository`,
  `DepartureProcedureRepository`, `PreferredRouteRepository`), `airway.py`
  (`AirwayRepository`), and `airspace.py`'s `ClassAirspaceRepository`/
  `ArtccRepository`/`MaaRepository`/`ParachuteJumpAreaRepository` (Phase 3
  below), plus `openNASR/flightplan.py`'s `_procedure_path`/
  `_is_published_dotted_procedure` and all of `openNASR/plotting.py`
  (Phase 4 below, this plan's original scope);
  (d) **full-table scan, but called at most once per process/instance
  lifetime with no realistic repeated-call scenario** — none confirmed;
  every full-table scan found is inside a `find()`/`get()`/constructor
  called once per lookup, and lookups are the whole point of these classes.
  Acceptance: this bullet's classification is the audit result; superseded
  only by direct measurement, not by re-reading the code a second time (see
  the (b)/(c) correction above for why).
- [x] **S0.2 — Agent model: Sol. Done (2026-08-17).** Measured real-cycle
  cost directly (not estimated) for every (b)/(c) site above, using the
  canonical `2026-05-14` cycle already established as this repository's
  benchmark baseline in `ROUTE_PATH_PLAN.md`.
  **(b) — the caching-technique bug, most severe:**
  - `nasr.fixes.get(...)` (`RecordRepository._normalized_index`, backing
    `FixRepository`): first call in a process costs **~14.9s**. Root cause,
    isolated directly: `dict(tuple(frame.groupby(normalized)))` over
    `FIX_BASE` (70,003 rows, 70,003 distinct `FIX_ID` values — i.e. no
    actual grouping occurs, every row is its own group) costs ~15.3s on its
    own; the equivalent `frame.groupby(normalized).indices` (index arrays,
    not materialized per-group DataFrames) costs **~0.09s** for the same
    input — about 170× faster for identical correctness, materializing an
    individual group's rows afterward via `.iloc[indices[key]]` costs
    <1ms.
  - `nasr.airport(...)` (`AirportRepository._related_index`, joining
    `APT_RWY`/`APT_RWY_END`/`ILS_BASE`/`ILS_DME`/`ILS_GS`/`ILS_MKR` by
    `ARPT_ID`): first call in a process costs **~41.3s** (building six
    separate broken indexes, the worst being `APT_BASE`'s own 19,410-row,
    19,410-distinct-value `ARPT_ID` index at ~12.5s). Once every index is
    cached, a second, different airport's lookup costs ~17ms — reasonably
    fast, but the one-time cold cost makes the *first* call to what is
    documented as the primary modern API look completely hung.
  **(c) — uncached full-table scans, high severity but not catastrophic:**
  - Legacy `FIX("AABEE", nasr)`: ~32.3ms per construction (two independent
    uncached `.map()` scans of `FIX_BASE`: one in `NASR.isFix`, one in
    `FIX._addBASE`).
  - Legacy `nasr.isAirport("BWI")`: ~5.6ms per call (two uncached `.map()`
    scans of `APT_BASE`, one per identifier column).
  - Legacy `NAVAID("ABR", nasr)`: ~4.4ms per construction (same two-scan
    pattern against `NAV_BASE`).
  - Legacy `Airport("ATL", nasr)` (excluding an unrelated, pre-existing
    `makeRWYbnds`/`ll2xy` geometry bug hit for several real airports on this
    cycle, out of this plan's scope): ~27-28ms per construction (seven
    uncached `==`-mask scans, one per joined table).
  - `nasr.coded_departure_routes.find(...)` (`departure.py`, largest
    table not yet covered): ~10.4ms per call against `CDR` (41,212 rows),
    every call, warm or cold — matches the `_procedure_path` pattern
    `ROUTE_PATH_PLAN.md` already fixed in `flightplan.py`.
  - `_procedure_path`/`_is_published_dotted_procedure`
    (`openNASR/flightplan.py`): a warm `RouteResolver.path(...)` call for a
    route containing no procedure averages ~422µs; a route containing a DP
    or STAR averages ~183ms — roughly 430× more expensive, and procedure
    routes were the majority (51 of 78 resolved) of the canonical 100-route
    sample. Profiled root cause: `_procedure_path` calls `.map(_text)` over
    the full `DP_RTE` (12,221 rows)/`STAR_RTE` (17,527 rows) tables on every
    invocation, with no index — ~11 million calls to the module's `_text()`
    helper across 10 warm iterations of one procedure-heavy route.
  - `_airway_segments` (`openNASR/plotting.py`): one call (as `plot_airspace`
    makes) took ~2.0s against `AWY_SEG_ALT` (19,318 rows) + `AWY_BASE`
    (1,519 rows) + `FIX_BASE` (70,003 rows) + `NAV_BASE` (1,634 rows).
  - `_procedure_segments` (`openNASR/plotting.py`): one call (as
    `plot_airport_procedures` makes, once for `DP_RTE` and once for
    `STAR_RTE`) took ~1.5s each against `DP_RTE` (12,221 rows)/`STAR_RTE`
    (17,527 rows). Ten repeated calls (simulating batch-plotting ten
    airports) took ~14.8s with no reuse — the cost repeats in full every
    call since nothing is cached.
  Real-cycle row counts for every operational table not already listed
  above (used to prioritize Phase 3's remaining, not-yet-individually-
  measured repositories): `PFR_SEG` 74,182; `CDR` 41,212; `FRQ` 40,767;
  `LID` 31,046; `MTR_SOP` 20,787; `AWY_SEG_ALT` 19,318; `HPF_SPD_ALT`
  17,914; `STAR_RTE` 17,527; `HPF_CHRT` 16,208; `HPF_BASE` 15,565;
  `PFR_BASE`/`PFR_RMT_FMT` 13,309; `DP_RTE` 12,221; `WXL_SVC` 10,725;
  `DP_APT` 6,413; `MTR_PT` 5,884; `ATC_BASE` 3,617; `WXL_BASE` 3,363;
  `STAR_APT` 3,356; `ATC_RMK` 3,176; `ARB_SEG` 2,687; `AWOS` 2,647; `COM`
  1,822; the remainder are under 1,700 rows and lower priority.
  Acceptance: the measurements above are the recorded baseline; Phase 2/3/4's
  before/after comparisons must reproduce or supersede them with recorded
  numbers, not assume they still hold.

**Gate 0:** Sol confirms the (b)/(c) classification and baseline measurements
are reproducible, and that Phases 2-4 below cover every confirmed (b)/(c)
site (or explicitly defers a site with a stated reason). Gate 0 specifically
confirms the corrected (b) finding (Phase 2) is understood as higher
priority than Phase 3/4's already-planned work, since it affects a
documented "already fast" public API.

## Phase 1 — Benchmark harness (routes and `plotExamples/`)

**Directory move (2026-08-17):** all benchmarking code and data now live
under `benchmarks/`, not `tools/`. `benchmarks/duckdb_benchmark.py`,
`benchmarks/flightplan_benchmark.py`, and `benchmarks/route_benchmark.py`
are straight moves of the former `tools/*_benchmark.py` scripts (paths and
docstrings updated, behavior unchanged). `tools/route_path_validation.py`
stayed in `tools/` — it is a correctness validator, not a benchmark. Every
task below that references `tools/route_benchmark.py` or a new
`tools/plotting_benchmark.py` should read `benchmarks/` instead.

- [x] **L1.1 — Agent model: Luna. Done (2026-08-17), as a new
  script rather than an extension of `route_benchmark.py`.** Rather than add
  a mode to `benchmarks/route_benchmark.py` (which reports raw JSON for a
  fixed synthetic 6-route matrix, a different and still-useful purpose —
  keep it as is), added `benchmarks/run_benchmarks.py` as the primary,
  human-readable entry point: it samples the canonical 100-route,
  `random.Random(20260514)`-seeded selection from
  `benchmarks/data/example_routes.csv` (moved from the untracked
  `tests/exampleRoutes.csv`; now committed so the benchmark is
  self-contained) against a locally cached cycle, and prints separate
  mean/median/p95/min/max for procedure-containing vs. direct/airway-only
  routes, plus the cost ratio between them. Verified against the real
  `2026-05-14` cycle: reproduces the ~100-160x order-of-magnitude gap this
  plan's Phase 0 measured (exact ratio varies by sample size/iteration
  count, as expected for a timing measurement).
  The command now also accepts `--storage duckdb` and `--output PATH`; the
  latter writes machine-readable JSON containing load/index timings and the
  same direct/procedure summaries printed to the terminal.
  Dependencies: none.
- [x] **L1.2 — Agent model: Luna. Done (2026-08-17).** Add a `plotExamples/`-equivalent
  benchmark to `benchmarks/plotting_benchmark.py` (a new tool, not an
  extension of the route tool — plotting has a different call shape: one-shot
  figure construction, not per-route resolution). It must exercise, without
  writing PNGs or importing `matplotlib.pyplot` in a display-requiring way
  (use `Agg`, matching every `plotExamples/*.py` script's own convention):
  - `plot_airspace` for one ARTCC boundary (mirror
    `plotExamples/main_test_NASR_zob_airways.py`'s ZOB high+low case).
  - `plot_airport_procedures` for one airport (mirror
    `plotExamples/main_test_NASR_atlanta_procedures.py`'s ATL case).
  - `plot_airport_procedures` repeated across a small fixed list of airport
    identifiers (e.g. 10), to measure the no-caching repeated-call cost
    directly, not just a single call — this is the scenario S0.2 found
    costs ~14.8s uncached for just the departure layer.
  - `plot_flight_plan` for one representative route, both a
    direct/airway-only route and a procedure-containing route (reuses
    `flightplan.py`'s cost, included here so the plotting benchmark's report
    is a complete picture of what a plotting workflow actually pays).
  Report each case's cold (first call) and repeated-call timings separately,
  using the same already-loaded-tables/reported-environment policy as
  `benchmarks/route_benchmark.py`. Support `--cycle`/`--cache-dir` matching every
  `plotExamples/*.py` script's existing CLI convention, and default to CSV
  storage with an option for DuckDB (`plotExamples/duckdb_example_setup.py`
  currently hardcodes DuckDB; the benchmark should support both so a
  regression in either backend is visible).
  Acceptance: running the tool against the canonical cycle reproduces this
  session's measured order of magnitude for `_airway_segments`/
  `_procedure_segments` before any Phase 5 fix lands.
- [x] **L1.3 — Agent model: Luna. Done (2026-08-17).** Add `benchmarks/repository_benchmark.py`
  to cover Phase 0's (b)/(c) findings that `run_benchmarks.py` (routes) and
  the new `plotting_benchmark.py` (plotting) do not: the legacy
  `Airport`/`FIX`/`NAVAID` constructors, `nasr.isAirport`/`isFix`/`isNavaid`,
  and the modern `nasr.airport`/`nasr.fixes.get`/`nasr.navaids.get`
  repository facade, plus a representative sample of the other
  domain-module repositories found slow in Phase 0(c) (at minimum
  `nasr.coded_departure_routes`, the largest table not covered by an
  existing benchmark). For each, report **first-call (cold index/scan) and
  warm repeated-call timing separately** — Phase 0's worst finding
  (`nasr.airport`'s 41s first call) is specifically a first-call problem
  invisible in a warm-only benchmark, the same lesson `run_benchmarks.py`
  already applies to procedure-vs-direct routes. Sample identifiers the
  same diverse way `run_benchmarks.py` samples routes: pull a random,
  seeded set of real `FIX_ID`/`ARPT_ID`/`NAV_ID`/`RCode` values from the
  already-loaded tables (no second external dataset needed — the NASR
  tables themselves are the diverse input here), not one hardcoded
  identifier per table. Print the same style of human-readable
  mean/median/p95 summary as `run_benchmarks.py`, not raw JSON.
  Acceptance: running the tool against the canonical cycle reproduces
  Phase 0's order-of-magnitude findings (the `nasr.airport`/`nasr.fixes.get`
  first-call cost in particular) before any Phase 2/3 fix lands.
  Dependencies: none.
- [x] **L1.4 — Agent model: Luna. Done (2026-08-17).** Add a non-CI benchmark report template
  for this plan's numbers, following `docs/DUCKDB_BENCHMARK_REPORT_TEMPLATE.md`'s
  existing convention (environment, versions, canonical cycle, cold/warm
  policy, before/after table). Do not duplicate
  `docs/route_path_baseline_2026-05-14.md`; link to it for the route-only
  numbers and add sections here for the repository and plotting findings.
  Dependencies: L1.1, L1.2, L1.3. Template: `docs/SPEEDUP_BENCHMARK_REPORT_TEMPLATE.md`.

**Gate 1:** Sol confirms all three benchmark tools (`run_benchmarks.py`,
`plotting_benchmark.py`, `repository_benchmark.py`) run against the
canonical cycle, report numbers consistent with Phase 0's baseline, and are
wired to `--cycle`/`--cache-dir` so they work against any locally cached
cycle, not only `2026-05-14`.

## Phase 2 — Fix `openNASR/repository.py`'s broken cached index (highest priority)

This phase fixes Phase 0's most severe finding and should land before
Phase 3/4/5's other work, even though those were written first
chronologically: it is a correctness-of-performance bug in code that is
*already* the documented, recommended modern facade
(`nasr.airport(...)`/`nasr.fixes.get(...)`/`nasr.navaids.get(...)`), not a
missing optimization in a known-slow legacy path. A user hitting the
~41-second first `nasr.airport(...)` call has no reason to suspect the
"fast" API is the problem.

- [ ] **T2.1 — Agent model: Terra.** Replace
  `RecordRepository._normalized_index`'s and
  `AirportRepository._related_index`'s `dict(tuple(frame.groupby(normalized)))`
  (`openNASR/repository.py:252-265`, `151-169`) with
  `frame.groupby(normalized).indices` (a `dict[str, numpy.ndarray]` of
  integer row positions per group, built in one vectorized pass — confirmed
  2026-08-17 at ~0.09s for `FIX_BASE`'s 70,003-row/70,003-group case, ~170×
  faster than the current `dict(tuple(...))` construction for the same
  input and same correctness). Update every call site that currently
  expects the index's values to be `DataFrame` objects
  (`_rows_for_identifier_column`, `_related_records`, and any other
  `self._normalized_indexes[...]`/`self._related_indexes[...]` reader) to
  materialize a group's rows on demand via `frame.iloc[positions]` instead
  of using the stored value directly — confirmed this materialization step
  itself costs under 1ms per group, so deferring it to lookup time (rather
  than eagerly building one `DataFrame` per group up front) is both correct
  and still fast.
  Acceptance: a unit test builds an index over a synthetic table with a
  fully-unique identifier column (reproducing the `FIX_BASE` shape), confirms
  the same rows are returned for a known identifier, and structurally blocks
  the old `dict(tuple(frame.groupby(...)))` materialization pattern. Record
  real-cycle speedup in `benchmarks/repository_benchmark.py`; do not use an
  absolute wall-clock assertion in pytest because it is hardware-sensitive.
  Dependencies: none.
- [x] **T2.2 — Agent model: Terra. Done (2026-08-17).** Audited every
  remaining package `groupby` call after T2.1: the two in
  `openNASR/repository.py` now use `.indices`, and the sole materializing
  site is `ArtccRepository._boundaries` in `openNASR/airspace.py` (grouping
  `ARB_SEG` by `(ALTITUDE, TYPE)`). Measured against the real 2026-05-14
  cycle: `ARB_SEG` has 2,687 rows across 26 ARTCCs; the largest location
  (`ZAN`) has 351 rows and only three groups. Over 100 warmed iterations,
  the existing ordered group materialization had a 0.85 ms median versus
  1.28 ms for `.indices` followed by the required per-group `.iloc`
  materialization. It is therefore low-cardinality, does not exhibit T2.1's
  eager-high-cardinality blowup, and a rewrite would be slower while adding
  ordering risk: `Boundary` depends on source order to identify closed
  rings. No production change was made. Acceptance: every `groupby` call
  site is now either `.indices`-backed or directly measured as safe.
  Dependencies: T2.1 (reuse whatever pattern T2.1 settles on).
- [x] **L2.3 — Agent model: Luna. Done (2026-08-17).** Add a regression test reproducing the
  ~41s `nasr.airport(...)` first-call cost and the ~14.9s
  `nasr.fixes.get(...)` first-call cost found in Phase 0, asserting the
  post-fix cost is materially smaller (an absolute wall-clock ceiling well
  under the original measurement, e.g. under 2s, is appropriate here — this
  bug's severity is itself hardware-independent, since it scales with row
  count, not CPU speed, so a generous absolute ceiling is a meaningful
  regression guard, unlike Phase 4/5's relative-improvement convention).
  The regression uses structural position-index assertions rather than a
  fragile wall-clock pytest ceiling. Run
  `python -m benchmarks.repository_benchmark --cycle 2026-05-14` to record
  cold and warm numbers on the benchmark host.
  Dependencies: T2.1, L1.3.
- [x] **S2.4 — Agent model: Sol. Done (2026-08-17, reviewed `2f85f4d`).** Confirm no other repository or test in
  the package silently depended on `_normalized_index`/`_related_index`
  values being full `DataFrame` objects rather than row-position arrays
  (e.g. via `isinstance` checks, `.columns` access on a cached value, or
  similar) — review, not new code.
  Dependencies: T2.1, T2.2.

L2.3 evidence: `tests/test_nasr_facade.py` verifies fully unique identifiers
use cached NumPy row positions and that repeated lookups reuse the same index;
`tests/test_repository.py` blocks the former per-group DataFrame materializer.
`benchmarks/repository_benchmark.py` samples seeded real-cycle identifiers and
reports first-call (cold) and repeated (warm) medians/p95 for modern and
legacy APIs. Gate 2's canonical-cycle results below supersede the earlier
environment note that no fresh timing report was available.

  Compatibility result: the only production consumers of these two private
  caches are `AirportRepository.get`, `AirportRepository._related_records`,
  and `RecordRepository._rows_for_identifier_column`. Commit `2f85f4d`
  updates all three to materialize on demand with `frame.iloc[positions]`.
  The composite-key path still intersects the materialized rows' original
  labels, and the airport FAA/ICAO path still deduplicates by original row
  label, so non-Range indexes and overlapping identifiers retain their prior
  behavior. A package/test-wide search found no `.columns`, DataFrame type
  check, or other reader of a cached value. Tests inspect only cache reuse;
  the new structural test additionally requires `numpy.ndarray` positions.
  The focused repository/airspace/domain suite passed 46 tests; Ruff and mypy
  passed for the reviewed files.

**Gate 2:** Sol confirms T2.1's fix drops `nasr.airport(...)`'s and
`nasr.fixes.get(...)`'s first-call cost from ~41s/~14.9s to a small recorded
number (target: comfortably under 1s each on the benchmark host),
that T2.2's audit found and fixed every other instance of the same
anti-pattern, and that the full test suite passes with no behavior change.

**Gate 2 — APPROVED (2026-08-17).** On the canonical `2026-05-14` CSV cycle,
with all tables loaded before lookup timing, a fresh one-identifier benchmark
process measured the following valid public lookups (`FIBEE` and `VT47` both
returned their expected record types):

| Public lookup | Phase 0 first-call baseline | Current first call | Speedup | Current repeated call |
| --- | ---: | ---: | ---: | ---: |
| `nasr.fixes.get(...)` | ~14.9s | 103.860ms | ~143x | 1.764ms |
| `nasr.airport(...)` | ~41.3s | 138.936ms | ~297x | 15.793ms |

Both first calls are comfortably below the 1s target. A separate seeded
10-identifier run reported first-build-inclusive p95 values of 103.542ms for
fixes and 140.079ms for airports, with warm medians of 1.566ms and 15.019ms,
respectively. T2.2 accounts for every package `groupby`: the two repository
indexes use row-position `.indices`, while the sole remaining DataFrame-group
materialization is the measured low-cardinality, source-order-sensitive ARTCC
boundary case. The full suite passed with **376 passed, 1 skipped** using
`.venv/bin/python -m pytest -q`; no behavior regression was observed.

Gate approval does not broaden Batch C. Its manifest remains exactly the five
ranked, measured entries below. Unranked modules and the sub-millisecond ARTCC
grouping remain audit findings until a cold/warm measurement and named
regression test justify adding them.

## Execution order and bounded parallelism

The phase numbering is dependency order, not permission for a broad rewrite.
Execute these bounded batches and stop at every gate:

| Batch | Agent model | Work | Parallelism rule |
| --- | --- | --- | --- |
| A | Luna + Terra + Sol | Finish L1.1; add L1.2/L1.3 harnesses; design/review T2.1 | Luna may change benchmark files while Terra owns only `repository.py`; Sol reviews evidence. |
| B | Terra, then Luna, then Sol | T2.1/T2.2, L2.3, S2.4/Gate 2 | Sequential on `repository.py`; do not start domain migrations before Gate 2. |
| C | Terra + Luna + Sol | T3.1 helper, then only profiled domain batches, L3.5/Gate 3 | Split Terra work only by disjoint module sets and commit one module batch at a time. |
| D | Terra + Luna + Sol | T4.1-T4.3, L4.4/Gate 4 | `flightplan.py` has one Terra owner; Luna may prepare benchmark cases only. |
| E | Terra + Luna + Sol | T5.1-T5.2, L5.3-L5.4/Gate 5 | `plotting.py` has one Terra owner; preserve plotted coordinate data. |
| F | Luna + Sol | L6.1-L6.2 and S6.3/Gate 6 | Documentation/reporting starts only after performance gates are measured. |

Before Batch C, Sol must turn Phase 0's long domain list into a short ranked
manifest: module, public lookup, real-cycle cold/warm measurement, key
columns, and exact regression tests. Entries without a material measured cost
remain documented audit findings, not Terra implementation tasks.

### Ranked Phase 3 manifest (2026-08-17)

This is the bounded Batch C implementation manifest. Measurements use the
`2026-05-14` CSV cycle with relevant tables already loaded: “cold” is the
first public lookup after load and “warm” is the median of repeated lookups
(20 repetitions, except 10 for the legacy `FIX` constructor). They measure
lookup/index work, not archive or table loading. Ranking is by warm cost; the
cutoff is a measured median of at least 10ms. Modules below the cutoff or not
yet measured remain audit findings and must be profiled before being added.

| Rank | Module / public lookup | Cold / warm evidence | Key columns to index | Exact regression test |
| ---: | --- | ---: | --- | --- |
| 1 | `airway.py`: `nasr.airways.get(("N", "C", "A216"))` | 147.533ms / 147.626ms | `(REGULATORY, AWY_LOCATION, AWY_ID)` across `AWY_BASE`/`AWY_SEG_ALT`; preserve segment and related fix/navaid order | `tests/test_airways.py::test_airway_repository_orders_segments_and_exposes_altitudes` |
| 2 | `holding.py`: `nasr.holding_patterns.get(("AABEE INT*GA*K7", "1", "GA", "US"))` | 39.512ms / 40.916ms | `(HP_NAME, HP_NO, STATE_CODE, COUNTRY_CODE)` across `HPF_BASE`/`HPF_CHRT`/`HPF_RMK`/`HPF_SPD_ALT` | `tests/test_holding_patterns.py::test_holding_pattern_uses_full_key_and_orders_remarks` |
| 3 | `fix.py`/`nasr.py`: `FIX("AABEE", nasr)` (representative for the legacy `FIX`/`Airport`/`NAVAID` and `is*` batch in T3.4) | 35.403ms / 32.780ms | `FIX_BASE.FIX_ID`; shared legacy helper must also cover `APT_BASE.(ARPT_ID, ICAO_ID)` and `NAV_BASE.NAV_ID` | `tests/test_milestone_1_terra.py::test_legacy_fix_constructor_resolves_identifier_case_insensitively` (plus the adjacent airport/navaid compatibility tests) |
| 4 | `departure.py`: `nasr.preferred_routes.get(("ABE", "ACY", "TEC", "1"))` | 28.573ms / 29.794ms | `PFR_BASE`/`PFR_SEG`: `(ORIGIN_ID, DSTN_ID, PFR_TYPE_CODE, ROUTE_NO)`; `PFR_RMT_FMT`: `(Orig, Dest, Type, Seq)` | `tests/test_preferred_routes.py::test_preferred_route_orders_segments_and_attaches_format` |
| 5 | `locations.py`: `nasr.location_identifiers.get(("US", "00A", "AEA", "PA", "BENSALEM", "LANDING FACILITY", "H"))` | 21.672ms / 21.970ms | `(COUNTRY_CODE, LOC_ID, REGION_CODE, STATE, CITY, LID_GROUP, FAC_TYPE)` | `tests/test_locations.py::test_location_identifier_uses_full_composite_key` |
| 6 | `military.py`: `nasr.military_training_routes.get(("IR", "002"))` | 19.591ms / 20.905ms | `(ROUTE_TYPE_CODE, ROUTE_ID)` across `MTR_BASE` and its agency/point/SOP/terrain/width children | `tests/test_military.py::test_military_training_route_repository_and_singular_facade_are_equivalent` |
| 7 | `atc.py`: `nasr.atc_facilities.get(("24226.1", "A", "NON-ATCT", "TX", "00R", "LIVINGSTON", "US"))` | 14.070ms / 14.206ms | `(SITE_NO, SITE_TYPE_CODE, FACILITY_TYPE, STATE_CODE, FACILITY_ID, CITY, COUNTRY_CODE)` across `ATC_BASE` and child tables | `tests/test_atc.py::test_atc_facility_collects_matching_child_records_in_remark_order` |
| 8 | `communications.py`: `nasr.frequencies.get(("00A", "00A", "HELIPORT", "PA", "US", "122.9", "", "CTAF"))` | 12.872ms / 12.565ms | `(FACILITY, SERVICED_FACILITY, SERVICED_SITE_TYPE, SERVICED_STATE, SERVICED_COUNTRY, FREQ, SECTORIZATION, FREQ_USE)` | `tests/test_communications.py::test_communication_outlet_and_frequency_repositories_expose_rich_records` |
| 9 | `departure.py`: `nasr.coded_departure_routes.find("ABECLTGV")` | 13.818ms / 10.606ms | `CDR.RCode` | `tests/test_coded_departure_routes.py::test_coded_departure_route_repository_returns_typed_record` |

The manifest intentionally does not authorize a blanket T3.3 rewrite. A
second real-cycle screen admitted only the four newly ranked paths above.
Representative warm medians below the 10ms cutoff remain audit-only: FSS
5.895ms, weather location 7.247ms, STAR 8.631ms, class airspace 1.605ms, and
MAA 4.397ms. The measured `ArtccRepository` `groupby` is also excluded:
on the largest real `ARB_SEG` location (`ZAN`, 351 of 2,687 rows), it creates
three source-ordered groups in 0.822ms median (100 repetitions). Its
DataFrame groups are the required input to `Boundary`, not a persistent
high-cardinality index. Other unranked domain repositories require the same
cold/warm measurement and a named regression test before Terra work begins.

## Phase 3 — Index the domain-module repositories (`atc.py`, `communications.py`, `holding.py`, `fss.py`, `locations.py`, `military.py`, `weather.py`, `arrivals.py`, `departure.py`, `airway.py`, `airspace.py`, and legacy `airport.py`/`fix.py`/`nav.py`)

This phase fixes Phase 0(c)'s uncached-full-table-scan finding, the same
class of bug `ROUTE_PATH_PLAN.md` already fixed in `flightplan.py` and this
plan's Phase 4/5 fix in `flightplan.py`'s procedure tables and
`plotting.py`. Unlike Phase 2, none of these are individually catastrophic
(milliseconds, not tens of seconds) — but there are roughly a dozen
independent repositories with the identical bug, and several back tables
in the tens of thousands of rows (`CDR` 41,212, `LID` 31,046, `FRQ` 40,767,
`PFR_SEG`/`PFR_BASE` 74,182/13,309, `HPF_*` 14,000-18,000). Prioritize by
Phase 0's row-count table, largest first, rather than fixing every module
in file-alphabetical order.

- [x] **T3.1 — Agent model: Terra. Done (2026-08-17).** Added the small,
  snapshot-scoped `openNASR.indexing` helper: callers own a cache keyed by
  frame identity and column, and receive normalized-value -> source-row
  position indexes built with `.groupby(...).indices`; a second helper
  materializes only the requested group with `.iloc`. It deliberately has
  no cross-instance cache and no repository migration in this task. Synthetic
  10,001-row parity and structural regressions verify duplicate/source order,
  cache reuse, missing rows, and rejection of eager `dict(tuple(groupby()))`
  materialization. A non-CI 10,000-row/100-lookup synthetic measurement was
  16.21x faster for one index build than repeated normalized scans. It is the
  shared primitive only for the five measured manifest paths below;
  T3.2/T3.4 remain responsible for applying it.
  Dependencies: T2.1 (reuse the same underlying technique).
- [x] **T3.2 — Agent model: Terra. Implementation done; Gate 3 performance
  verification incomplete (2026-08-17).** Applied T3.1's
  position-index helper to the manifest-approved high-value paths only:
  `CodedDepartureRouteRepository` (`CDR`),
  `LocationIdentifierRepository` (`LID`), `FrequencyRepository` (`FRQ`),
  and `PreferredRouteRepository`'s base/format/segment tables (`PFR_*`).
  Composite keys intersect source positions before one ordered `.iloc`
  materialization. Focused regression and CSV/DuckDB parity tests pass. A
  non-CI 2026-05-14 CSV measurement (first call, then 20 warmed repetitions)
  recorded warm medians of 0.70 ms (CDR), 1.14 ms (LID), 1.68 ms (FRQ), and
  3.22 ms (PFR), all more than an order of magnitude below the 10.606–29.794
  ms manifest baseline; cold measurements include one index build per
  queried column (133.848–228.763 ms) and are not compared cross-host.
  Sol's same-host verification measured CDR 0.908ms (11.69x) and LID 1.264ms
  (17.38x), but FRQ 1.665ms (7.55x) and PFR 3.313ms (8.99x). Results are all
  materially faster. FRQ/PFR miss the original ratio-only target but pass the
  bounded absolute-floor policy recorded under Gate 3; their profiles no
  longer contain the full-table scan this phase was intended to remove.
  Dependencies: T3.1.
- [x] **T3.3 — Agent model: Terra. Implementation landed; relationship
  follow-up required.** Applied T3.1's helper only to the four additional
  manifest-qualified repositories: `airway.py`, `holding.py`, `military.py`'s
  military-training-route path, and `atc.py`'s facility path. FSS, weather,
  arrivals, and the measured airspace paths remain audit findings because
  their representative warm calls are below the 10ms profiler threshold.
  Same-host post-change warm medians were 139.584ms airway (1.06x), 21.391ms
  holding (1.91x), 4.065ms military (5.14x), and 3.520ms ATC (4.04x).
  Military and ATC are below Gate 3's amended 5ms absolute floor; airway and
  holding remain open under T3.3a.
  Dependencies: T3.1, T3.2 (land the highest-value tables first so the
  shared helper is proven at scale before the long tail).
- [ ] **T3.3a — Agent model: Terra.** Add one bounded, snapshot-scoped
  composite-key row-position index for `relationships.related_record`, and
  wire it only through `AirwayRepository` and `HoldingPatternRepository` in
  this phase. Profiling shows this is the remaining hot lookup: ten warm
  `A216` calls perform 140 relationship resolutions and spend 4.740s
  cumulative in `related_record`; ten holding calls spend 0.676s there.
  The current helper repeatedly normalizes all 70,003 `FIX_BASE` rows (and,
  for every airway segment, `NAV_BASE`) once per relationship.

  The index must key on the complete declared target-column tuple, store
  source row positions rather than `FaaRecord` instances, and be owned by the
  repository snapshot. Do not cache returned record objects: `FaaRecord.raw`
  exposes its backing mapping, so reusing objects would introduce mutation
  and identity behavior not present today. Preserve `None` for incomplete or
  absent relationships and the exact `AmbiguousRecordError` for duplicate
  complete keys. A prototype full-composite position index built the real
  FIX/NAV indexes in 103.851ms once; resolving all 14 relationships for the
  seven-segment airway then took 0.598ms median instead of 128.900ms, while
  the holding relationship took 1.937ms instead of 17.988ms.

  Acceptance: the existing airway-order and holding-fix regressions pass,
  plus tests for an absent and ambiguous complete relationship. Record cold
  index build separately; the warm public calls must satisfy Gate 3's policy
  below without broadening the manifest to the lower-cost
  communications/airspace callers of `related_record`.
- [ ] **T3.4 — Agent model: Terra.** Fix the legacy uncached scans: `NASR.isFix`/
  `isAirport`/`isNavaid` (`openNASR/nasr.py`) and `basictypes.py`'s
  `getAirportRecord`/`getAirportRecords` (backing `Airport`, `RWY`,
  `RWYEnd`, `ILSBase`, `ILSDME`, `ILSGS`, `ILSMKR`), plus `fix.py`'s
  `FIX._addBASE` and `nav.py`'s `NAVAID._addBASE`. These are legacy
  compatibility constructors (per `MIGRATION.md`), so prefer building a
  lazily-cached index attached to the `NASR` instance itself (built once,
  the first time any legacy constructor needs it, reused by every
  subsequent legacy call in that instance's lifetime) over changing any
  constructor's signature or the `Raw`/`SimpleNamespace` result shape.
  Acceptance: `FIX(...)`/`Airport(...)`/`NAVAID(...)` and
  `isFix`/`isAirport`/`isNavaid` produce identical results before and after;
  a benchmark run confirms at least an order-of-magnitude reduction in
  repeated-construction cost.
  Dependencies: T2.1 (reuse the same technique).
- [ ] **L3.5 — Agent model: Luna.** Add regression tests reproducing at
  least the `CDR`/`LID`/`FRQ` and legacy-constructor costs found in Phase 0,
  asserting a materially smaller post-fix cost using the same
  relative-improvement convention as Phase 4/5. Re-run L1.3's benchmark
  against the canonical cycle and record the new numbers for every
  repository/constructor T3.2-T3.4 touched.
  Dependencies: T3.2, T3.3, T3.4, L1.3.

**Gate 3:** Sol re-runs L1.3's benchmark and confirms every covered
repository/constructor meets the performance policy below, with no test
regression across the full suite (not just `tests/test_flightplan.py` — this
phase touches roughly a dozen modules with their own test files).

**Gate 3 — OPEN (2026-08-17).** Do not sign off until the four bounded T3.3
additions, T3.3a, and T3.4 land, L3.5 covers every touched path, and a
canonical rerun confirms the policy below. No unranked module outside the
nine-entry manifest is authorized for Phase 3 implementation.

**Gate 3 performance policy amendment (2026-08-17):** a manifest path passes
when its warm median is either at least 10x faster than baseline **or at most
5ms after eliminating the repeated full-table normalized scan**. The absolute
floor is half the 10ms admission threshold and prevents chasing a ratio by
caching mutable public record objects or replacing small, source-faithful
DataFrame materialization. It is not available to airway/holding while their
profiles still contain repeated full-table relationship scans.

Under this policy, T3.2's FRQ (1.665ms, 7.55x) and PFR (3.313ms, 8.99x)
results pass, as do T3.3's military and ATC results above. Profiles of 100
warm calls show FRQ/PFR time is now dominated by bounded `.iloc`/`to_dict`
record materialization, not normalization of their full source tables.
CDR (0.908ms, 11.69x) and LID (1.264ms, 17.38x) retain their ratio-based
passes. Airway and holding remain the only indexed-domain performance misses;
Gate 3 also remains blocked on the rest of T3.4 and release evidence.

## Phase 4 — Index the procedure tables (`openNASR/flightplan.py`)

- [ ] **T4.1 — Agent model: Terra.** Add a `_ProcedureIndex` class,
  structurally parallel to the existing `_AirwayIndex`
  (`openNASR/flightplan.py:272-293`): snapshot `DP_BASE`, `DP_RTE`,
  `STAR_BASE`, `STAR_RTE` once at construction and build vectorized
  lookup structures keyed by normalized `DP_COMPUTER_CODE`,
  `TRANSITION_COMPUTER_CODE` (both `DP_RTE` and `STAR_RTE`), and
  `STAR_COMPUTER_CODE` — the exact three lookups `_procedure_path`
  currently repeats as full-column `.map(_text).eq(token)` scans on every
  call (`flightplan.py:499-528`). Use the same "vectorized mask once, cache
  the result, no per-call `.to_dict()` over the full table" technique
  `_WaypointResolver`/`_AirwayIndex` already use — and reuse Phase 2's
  `.indices`-based fix if any of these columns turn out to be as
  high-cardinality as `FIX_ID`/`ARPT_ID` (measure before assuming
  `dict(tuple(frame.groupby(...)))` is safe here; do not reintroduce Phase
  2's bug in a new index).
  Acceptance: a unit test constructs a `_ProcedureIndex` against a small
  synthetic table set and confirms each of the three lookups returns the
  same rows a direct `.map(_text).eq(...)` filter would.
  Dependencies: Phase 2 (T2.1's fixed indexing technique).
- [ ] **T4.2 — Agent model: Terra.** Thread `_ProcedureIndex` through
  `_procedure_path` (`flightplan.py:476-658`) and
  `_is_published_dotted_procedure` (`flightplan.py:661-688`), replacing
  their full-column `.map(_text)` filters with index lookups, the same way
  T3.1/T3.2 in `ROUTE_PATH_PLAN.md` threaded `_AirwayIndex` through
  `_airway_vertices`/`_is_published_airway`. Preserve every existing
  ambiguity/not-found exception exactly — this is a lookup-mechanism change,
  not a matching-policy change (`ROUTE_PATH_PLAN.md`'s T2.4/T2.4a correction
  is the cautionary example: don't conflate a performance fix with a
  matching-logic fix in the same task).
  Acceptance: the full `tests/test_flightplan.py` suite (41 tests as of
  this plan's writing) passes unchanged; no test's expected output,
  exception type, or exception message changes.
  Dependencies: T4.1.
- [ ] **T4.3 — Agent model: Terra.** Build one `_ProcedureIndex` inside
  `RouteResolver.__init__` (`flightplan.py:883-887`) alongside the existing
  `_WaypointResolver`/`_AirwayIndex` construction, and pass it through
  `_flight_plan_path`/`_tokenize_flight_plan`'s existing `resolver`/
  `airway_index` parameter pattern (add a `procedure_index` parameter
  following the same convention). The module-level `flight_plan_path`
  wrapper continues to build one `RouteResolver` per call, matching its
  existing documented "for repeated calls, prefer `RouteResolver`" contract
  — this task does not change that public guidance, only makes the
  underlying construction cheaper.
  Acceptance: `test_route_resolver_reuses_one_waypoint_index`-style coverage
  (mirroring the existing test at `tests/test_flightplan.py`) is extended to
  confirm `_ProcedureIndex` is also built exactly once per `RouteResolver`
  instance, not once per `.path()` call.
  Dependencies: T4.2.
- [ ] **L4.4 — Agent model: Luna.** Add a regression test reproducing the
  ~430× procedure-vs-direct disparity found in Phase 0, asserting the
  post-fix ratio is materially smaller (do not hardcode an exact ratio —
  hardware-dependent; assert an order-of-magnitude bound, matching
  `ROUTE_PATH_PLAN.md` T4.1's "relative improvement, not absolute
  threshold" convention). Re-run the L1.1 benchmark against the canonical
  cycle and record the new mean/median for both route categories.
  Dependencies: T4.3, L1.1.

**Gate 4:** Sol re-runs L1.1's benchmark against the canonical cycle and
records the before/after mean/median for procedure-containing and
direct/airway-only routes; approves only if the procedure-route mean drops
by at least one order of magnitude and no `tests/test_flightplan.py`
regression exists.

## Phase 5 — Index the plotting lookups (`openNASR/plotting.py`)

- [ ] **T5.1 — Agent model: Terra.** Add a `_PlottingIndex` (or reuse/extend
  `_WaypointResolver`/`_AirwayIndex`/`_ProcedureIndex` directly if their
  shape already fits — decide based on what T4.1 actually produces, don't
  assume a fourth parallel class is needed) covering the tables
  `openNASR/plotting.py` currently full-scans per call:
  `FIX_BASE`/`NAV_BASE` (via `_coordinates`/`_navigation_endpoints`,
  `plotting.py:34-50`, `93-102`), `AWY_BASE`/`AWY_SEG_ALT` (via
  `_airway_segments`, `plotting.py:52-90`), `APT_BASE` (via
  `_airport_projection_center`, `plotting.py:119-139`), `DP_APT`/`DP_RTE`/
  `STAR_APT`/`STAR_RTE` (via `_procedure_segments`, `plotting.py:142-168`),
  and `APT_RWY_END` (via `_runway_segments`, `plotting.py:171-195`).
  `plotting.py` currently has no session/resolver object at all (confirmed
  2026-08-17: every function is a bare module-level function operating
  directly on the `nasr` mapping) — this task introduces the first one.
  Decide the public shape as part of this task: an internal-only index
  object is sufficient if `plot_airspace`/`plot_airport_procedures`/
  `plot_flight_plan` build and discard it per call (fixes the "no full-table
  rescan inside a single plot" cost), but does not fix the repeated-call
  cost L1.2 measured (~14.8s for 10 airports) unless a caller can reuse one
  index across multiple plot calls — if that repeated-call scenario matters
  in practice (confirm with Sol; the existing `plotExamples/` scripts are
  all single-plot, single-process scripts today, so this may be a
  forward-looking API decision rather than a current one), give
  `plot_airport_procedures` an optional pre-built-index parameter mirroring
  `RouteResolver`'s pattern, rather than only fixing the single-call case.
  Acceptance: a unit test confirms the index's lookups match the equivalent
  vectorized boolean-mask filter for each covered table.
  Dependencies: T4.1 (reuse its indexing technique/style; do not diverge).
- [ ] **T5.2 — Agent model: Terra.** Thread the index from T5.1 through
  `_coordinates`, `_navigation_endpoints`, `_airway_segments`,
  `_airport_projection_center`, `_procedure_segments`, and
  `_runway_segments`, replacing their `.to_dict(orient="records")` full-table
  walks with index lookups. Preserve every current dedup/ambiguity rule
  exactly (for example `_procedure_segments`' `len(starts) == 1 and
  len(ends) == 1` single-match requirement at `plotting.py:166`) — this is a
  lookup-mechanism change, not a rendering-policy change.
  Acceptance: `plot_airspace`, `plot_airport_procedures`, and
  `plot_flight_plan` each produce pixel-identical output (or, if exact pixel
  comparison is impractical, identical underlying line/point coordinate
  data) before and after this task, verified by comparing the plotted
  `Line2D`/`PathCollection` data arrays, not just that the function runs
  without error.
  Dependencies: T5.1.
- [ ] **L5.3 — Agent model: Luna.** Add regression tests reproducing the
  ~2.0s `_airway_segments` and ~1.5s-per-call, ~14.8s-for-ten-calls
  `_procedure_segments` costs found in Phase 0, asserting a materially
  smaller post-fix cost using the same relative-improvement convention as
  L4.4. Re-run the L1.2 benchmark against the canonical cycle and record the
  new numbers for all four `plotExamples/`-equivalent cases.
  Dependencies: T5.2, L1.2.
- [ ] **L5.4 — Agent model: Luna.** Run each of the four `plotExamples/*.py`
  scripts end to end (`--output` to a throwaway path, not `--show`, matching
  how they are already meant to be run headlessly) against the canonical
  cycle before and after Phase 5, and confirm each still produces a PNG with
  the same reported line-segment count printed by the script itself (each
  script already prints `len(axes.lines)` — reuse that as the correctness
  check, don't add a new one).
  Dependencies: T5.2.

**Gate 5:** Sol re-runs L1.2's benchmark and confirms the before/after
numbers for `_airway_segments`/`_procedure_segments`/repeated-call plotting,
and that all four `plotExamples/*.py` scripts still run correctly and
produce the same line-segment counts.

## Phase 6 — Documentation and release

- [ ] **L6.1 — Agent model: Luna.** Update `docs/API.md` and/or
  `openNASR/repository.py`'s/`plotting.py`'s module/function docstrings to
  document the new indexing objects' snapshot semantics (mirroring
  `RouteResolver`'s existing documented "construct a new instance after
  mutating a table" contract) and, if T5.1 added a reusable index parameter
  to `plot_airport_procedures`, document the batch-plotting use case it
  enables.
  Dependencies: T4.3, T5.2.
- [ ] **L6.2 — Agent model: Luna.** Record the full before/after benchmark
  report (Phase 2-5 numbers, environment, canonical cycle, cold/warm
  policy) using L1.4's template, linked from both this document and
  `ROUTE_PATH_PLAN.md` (the two plans now share one performance narrative
  for `flightplan.py`; cross-link rather than duplicate numbers). Lead with
  Phase 2's fix (the ~41s-to-under-1s `nasr.airport(...)` first-call
  improvement) since it is the highest-severity result in this plan.
  Dependencies: L2.3, L3.5, L4.4, L5.3.
- [ ] **S6.3 — Agent model: Sol.** Run the full release gate (`pytest`,
  `ruff format --check`, `ruff check`, `mypy openNASR`, `python -m build`,
  `twine check dist/*`) from a clean checkout and confirm all six commands
  pass, matching the convention every other plan in this repository closes
  with.
  Dependencies: L6.1, L6.2.

**Gate 6:** Sol approves release: all three benchmark tools, the audit
table from Phase 0, and the recorded before/after numbers for every phase
are complete and consistent; the full release gate passes.

## Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-17 | Scope this plan to `openNASR/flightplan.py`'s procedure tables and `openNASR/plotting.py`, with a Phase 0 audit rather than assuming every `.to_dict(orient="records")` call site in the package is slow. | Direct inspection found `openNASR/repository.py`'s equivalent lookups (`_class_airspace`, `_military_operations`, `_related_records`) already vectorize-then-materialize and already cache via `_related_index`; only `flightplan.py`'s procedure lookups (never covered by `ROUTE_PATH_PLAN.md`'s Phase 4, which only vectorized `_WaypointResolver` and the `AWY_BASE` airway lookup) and all of `plotting.py` (never covered by any prior performance work) were confirmed slow by direct measurement. Auditing first avoids speculative rewrites of code that is already fine. **Superseded 2026-08-17, see the "Correction:" entry below — the "already cache via `_related_index`" half of this conclusion was wrong.** |
| 2026-08-17 | Benchmark `plotExamples/`-equivalent calls as cold single-call and repeated-call cases, not only a single representative call. | Direct measurement found `_airway_segments` costs ~2.0s and `_procedure_segments` ~1.5s per call with no caching at all, so a batch-plotting scenario (ten airports) pays the full cost every time — ~14.8s for just the departure layer across ten calls. A single-call benchmark would hide this repeated-call multiplier the same way `ROUTE_PATH_PLAN.md`'s single-route Gate 4 benchmark (8.86µs) hid the ~430× procedure-route cost gap this plan's Phase 0 found. |
| 2026-08-17 | Reuse `_WaypointResolver`/`_AirwayIndex`'s exact indexing technique for the new `_ProcedureIndex` and plotting index, rather than inventing a new caching approach. | Two indexing patterns already exist in this codebase (`ROUTE_PATH_PLAN.md`'s T4.1/T4.2, and `openNASR/repository.py`'s pre-existing `_related_index`) and both are proven correct and tested; a third, different style would add maintenance cost without a demonstrated need. **Correction 2026-08-17: `_related_index` was not, in fact, proven correct at scale — see below.** |
| 2026-08-17 | Move all benchmarking code and data (`duckdb_benchmark.py`, `flightplan_benchmark.py`, `route_benchmark.py`, and `tests/exampleRoutes.csv`) from `tools/`/`tests/` into a new `benchmarks/` directory, and add `benchmarks/run_benchmarks.py` as a new, primary, human-readable entry point rather than extending `route_benchmark.py` in place. | Requested directly: one folder for all benchmarking code and data, with clear average-based output from diverse real input (random flight plans) rather than raw JSON or a fixed 6-route synthetic matrix. `route_benchmark.py`'s existing JSON/fixed-matrix report remains useful for machine comparison and was kept as is, alongside the new script, rather than conflating two different report shapes in one file. `tests/exampleRoutes.csv` was untracked (2.3MB, not committed); moved and committed to `benchmarks/data/example_routes.csv` after confirming it contains only public route-field strings with no personal or licensed content, so the benchmark is self-contained for anyone who clones the repository. |
| 2026-08-17 | **Correction:** `openNASR/repository.py`'s `_normalized_index`/`_related_index` are not fine — their caching technique is the single most severe performance bug found across the whole review. Reviewed every domain-type module (`airport.py`, `fix.py`, `nav.py`, `arb.py`/`airspace.py`, `airway.py`, `atc.py`, `communications.py`, `holding.py`, `fss.py`, `locations.py`, `military.py`, `weather.py`, `arrivals.py`, `departure.py`) at the user's request, widening scope beyond `flightplan.py`/`plotting.py`. | Direct measurement found `dict(tuple(frame.groupby(normalized)))` — the exact technique this plan's own earlier decision (above) called "proven correct" — costs ~15.3s to index `FIX_BASE` (70,003 rows, 70,003 distinct values) and ~12.5s for `APT_BASE`'s `ARPT_ID` index alone; the first `nasr.airport(...)` call (which builds six such indexes) costs ~41.3s, and the first `nasr.fixes.get(...)` call ~14.9s. The equivalent `frame.groupby(normalized).indices` (row-position arrays, not materialized per-group DataFrames) costs ~0.09s for the identical `FIX_BASE` input — ~170× faster for the same correctness. This means the codebase's *documented, recommended, modern* public API (`nasr.airport`/`nasr.fixes.get`/`nasr.navaids.get`) is currently far slower on first use than the *legacy* constructors it was meant to replace (`Airport(...)` ~27ms, `NAVAID(...)` ~4.4ms) — the opposite of what both this plan and `ROUTE_PATH_PLAN.md` assumed throughout. Filed as the new Phase 2, ahead of this plan's original Phase 2/3 (now Phase 4/5) despite being written second, because it is a bug in already-shipped, already-recommended code, not a missing optimization in known-legacy code. Also found the identical uncached-`.map()`-per-call pattern (a real but much less severe issue, matching `ROUTE_PATH_PLAN.md`'s already-fixed `flightplan.py` pattern) repeated across roughly a dozen domain-module repositories outside `repository.py`, filed as the new Phase 3. |
