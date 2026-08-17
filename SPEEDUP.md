# Table-Lookup Speedup Plan

## Goal

Remove the remaining unindexed, per-call, full-table scan/`.map()`/
`.to_dict(orient="records")` cost from every openNASR code path that resolves
NASR table rows repeatedly, using the same technique already proven correct
in `ROUTE_PATH_PLAN.md`'s Phase 4 (`_WaypointResolver`, `_AirwayIndex`):
build a vectorized index once per immutable table set, reuse it across calls,
and never regress raw-value fidelity, public return types, or source
ordering to get there.

This plan is scoped to two confirmed-slow modules — `openNASR/flightplan.py`
(the procedure-lookup tables `_WaypointResolver`/`_AirwayIndex` did not
cover) and `openNASR/plotting.py` (not covered by any prior performance
work) — plus a first task that audits the rest of the package so "all the
other table lookups" is answered with evidence, not assumption. Most of the
package's other `.to_dict(orient="records")` call sites already follow the
correct pattern (filter with a vectorized boolean mask first, materialize
only the small matched slice); this plan does not touch code that is already
fine, and Phase 0 exists specifically to establish which is which before any
fix work starts.

## Non-negotiable product rules

- Preserve every public function signature, return type, and exception type
  in `openNASR.flightplan` and `openNASR.plotting`. Speed is an
  implementation change, not an API or behavior change.
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
| **Terra** | Implementation | Production implementation in `openNASR/flightplan.py` and `openNASR/plotting.py`. |
| **Luna** | Tests/tooling | Fixtures, regression tests, benchmark tooling (routes and `plotExamples/`-equivalent plotting calls), documentation. |

## Coordination rules

- **Two files, sequential ownership per file.** `openNASR/flightplan.py` and
  `openNASR/plotting.py` are edited by different tasks below; treat each
  file the way `ROUTE_PATH_PLAN.md` treats `flightplan.py` alone — merge
  task *N* on a file before starting task *N+1* on the same file, even
  across phases. A task touching only one of the two files may run in
  parallel with an open task on the other file.
- **Every task cites the exact function and line(s) it changes.** Line
  numbers drift fast in these two files (`flightplan.py` grew from 504 to
  931 lines during `ROUTE_PATH_PLAN.md`'s Phase 1-4 work) — re-check before
  citing a new line number in a task, and re-check before starting a task
  that cites one written earlier.
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

## Phase 0 — Audit: which lookups are actually slow

- [ ] **S0.1 — Agent model: Sol.** Enumerate every `.to_dict(orient="records")`
  call site across the package (currently 17 modules — confirmed 2026-08-17
  via `grep -rl`) and classify each as one of:
  (a) **already vectorized-then-materialized** — a boolean-mask filter
  narrows the frame first, and `.to_dict()` only converts the small matched
  result (the pattern already used correctly in `openNASR/repository.py`'s
  `_class_airspace`/`_military_operations`/`_related_records`, which already
  has a cached `_related_index`);
  (b) **full-table scan per call, no cache** — the pattern this plan exists
  to fix, confirmed so far in `openNASR/flightplan.py`'s `_procedure_path`/
  `_is_published_dotted_procedure` (`DP_BASE`, `DP_RTE`, `STAR_BASE`,
  `STAR_RTE`) and `openNASR/plotting.py`'s `_coordinates`,
  `_airway_segments`, `_airport_projection_center`, `_procedure_segments`,
  `_runway_segments`;
  (c) **full-table scan, but called at most once per process/instance
  lifetime with no realistic repeated-call scenario** — lower priority, note
  but do not schedule a fix without a concrete repeated-call use case.
  Acceptance: a table in this document (replacing this bullet once done)
  listing every call site, its table(s), approximate real-cycle row count,
  and its (a)/(b)/(c) classification. Only (b) sites get phases below.
- [ ] **S0.2 — Agent model: Sol.** For each confirmed (b) site, measure its
  real-cycle cost directly (not estimated) using the canonical `2026-05-14`
  cycle already established as this repository's benchmark baseline in
  `ROUTE_PATH_PLAN.md`. Verified 2026-08-17 as a starting point (single
  representative call, CSV backend, already-loaded tables):
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
  Acceptance: the measurements above are reproduced independently (or
  superseded with corrected numbers) and recorded with the exact commands
  used, so Phase 2/3's before/after comparisons have a trustworthy baseline.

**Gate 0:** Sol confirms the (b) classification and baseline measurements
are reproducible, and that the phases below cover every confirmed (b) site
(or explicitly defers a site with a stated reason).

## Phase 1 — Benchmark harness (routes and `plotExamples/`)

**Directory move (2026-08-17):** all benchmarking code and data now live
under `benchmarks/`, not `tools/`. `benchmarks/duckdb_benchmark.py`,
`benchmarks/flightplan_benchmark.py`, and `benchmarks/route_benchmark.py`
are straight moves of the former `tools/*_benchmark.py` scripts (paths and
docstrings updated, behavior unchanged). `tools/route_path_validation.py`
stayed in `tools/` — it is a correctness validator, not a benchmark. Every
task below that references `tools/route_benchmark.py` or a new
`tools/plotting_benchmark.py` should read `benchmarks/` instead.

- [x] **L1.1 — Agent model: Luna. Substantially done (2026-08-17), as a new
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
  **Still open:** the acceptance criterion's "report loading time separately
  from path resolution" is satisfied (table load and index build are
  reported as separate lines), but `run_benchmarks.py` does not yet support
  `--storage duckdb` end-to-end validation (the flag exists and is passed
  through to `NASR`, but has not been exercised against a real DuckDB
  artifact as part of this task) or JSON output for machine comparison
  against `route_benchmark.py`'s existing report format — leave both as
  follow-up work under this same task rather than a new one.
  Dependencies: none.
- [ ] **L1.2 — Agent model: Luna.** Add a `plotExamples/`-equivalent
  benchmark to a new `tools/plotting_benchmark.py` (a new tool, not an
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
  `tools/route_benchmark.py`. Support `--cycle`/`--cache-dir` matching every
  `plotExamples/*.py` script's existing CLI convention, and default to CSV
  storage with an option for DuckDB (`plotExamples/duckdb_example_setup.py`
  currently hardcodes DuckDB; the benchmark should support both so a
  regression in either backend is visible).
  Acceptance: running the tool against the canonical cycle reproduces this
  session's measured order of magnitude for `_airway_segments`/
  `_procedure_segments` before any Phase 3 fix lands.
- [ ] **L1.3 — Agent model: Luna.** Add a non-CI benchmark report template
  for this plan's numbers, following `docs/DUCKDB_BENCHMARK_REPORT_TEMPLATE.md`'s
  existing convention (environment, versions, canonical cycle, cold/warm
  policy, before/after table). Do not duplicate
  `docs/route_path_baseline_2026-05-14.md`; link to it for the route-only
  numbers and add the new plotting section here.
  Dependencies: L1.1, L1.2.

**Gate 1:** Sol confirms both benchmark tools run against the canonical
cycle, report numbers consistent with Phase 0's baseline, and are wired to
`--cycle`/`--cache-dir` so they work against any locally cached cycle, not
only `2026-05-14`.

## Phase 2 — Index the procedure tables (`openNASR/flightplan.py`)

- [ ] **T2.1 — Agent model: Terra.** Add a `_ProcedureIndex` class,
  structurally parallel to the existing `_AirwayIndex`
  (`openNASR/flightplan.py:272-293`): snapshot `DP_BASE`, `DP_RTE`,
  `STAR_BASE`, `STAR_RTE` once at construction and build vectorized
  lookup structures keyed by normalized `DP_COMPUTER_CODE`,
  `TRANSITION_COMPUTER_CODE` (both `DP_RTE` and `STAR_RTE`), and
  `STAR_COMPUTER_CODE` — the exact three lookups `_procedure_path`
  currently repeats as full-column `.map(_text).eq(token)` scans on every
  call (`flightplan.py:499-528`). Use the same "vectorized mask once, cache
  the result, no per-call `.to_dict()` over the full table" technique
  `_WaypointResolver`/`_AirwayIndex` already use — do not introduce a third
  distinct indexing style.
  Acceptance: a unit test constructs a `_ProcedureIndex` against a small
  synthetic table set and confirms each of the three lookups returns the
  same rows a direct `.map(_text).eq(...)` filter would.
  Dependencies: none (new class, no existing call site changes yet).
- [ ] **T2.2 — Agent model: Terra.** Thread `_ProcedureIndex` through
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
  Dependencies: T2.1.
- [ ] **T2.3 — Agent model: Terra.** Build one `_ProcedureIndex` inside
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
  Dependencies: T2.2.
- [ ] **L2.4 — Agent model: Luna.** Add a regression test reproducing the
  ~430× procedure-vs-direct disparity found in Phase 0, asserting the
  post-fix ratio is materially smaller (do not hardcode an exact ratio —
  hardware-dependent; assert an order-of-magnitude bound, matching
  `ROUTE_PATH_PLAN.md` T4.1's "relative improvement, not absolute
  threshold" convention). Re-run the L1.1 benchmark against the canonical
  cycle and record the new mean/median for both route categories.
  Dependencies: T2.3, L1.1.

**Gate 2:** Sol re-runs L1.1's benchmark against the canonical cycle and
records the before/after mean/median for procedure-containing and
direct/airway-only routes; approves only if the procedure-route mean drops
by at least one order of magnitude and no `tests/test_flightplan.py`
regression exists.

## Phase 3 — Index the plotting lookups (`openNASR/plotting.py`)

- [ ] **T3.1 — Agent model: Terra.** Add a `_PlottingIndex` (or reuse/extend
  `_WaypointResolver`/`_AirwayIndex`/`_ProcedureIndex` directly if their
  shape already fits — decide based on what T2.1 actually produces, don't
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
  Dependencies: T2.1 (reuse its indexing technique/style; do not diverge).
- [ ] **T3.2 — Agent model: Terra.** Thread the index from T3.1 through
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
  Dependencies: T3.1.
- [ ] **L3.3 — Agent model: Luna.** Add regression tests reproducing the
  ~2.0s `_airway_segments` and ~1.5s-per-call, ~14.8s-for-ten-calls
  `_procedure_segments` costs found in Phase 0, asserting a materially
  smaller post-fix cost using the same relative-improvement convention as
  L2.4. Re-run the L1.2 benchmark against the canonical cycle and record the
  new numbers for all four `plotExamples/`-equivalent cases.
  Dependencies: T3.2, L1.2.
- [ ] **L3.4 — Agent model: Luna.** Run each of the four `plotExamples/*.py`
  scripts end to end (`--output` to a throwaway path, not `--show`, matching
  how they are already meant to be run headlessly) against the canonical
  cycle before and after Phase 3, and confirm each still produces a PNG with
  the same reported line-segment count printed by the script itself (each
  script already prints `len(axes.lines)` — reuse that as the correctness
  check, don't add a new one).
  Dependencies: T3.2.

**Gate 3:** Sol re-runs L1.2's benchmark and confirms the before/after
numbers for `_airway_segments`/`_procedure_segments`/repeated-call plotting,
and that all four `plotExamples/*.py` scripts still run correctly and
produce the same line-segment counts.

## Phase 4 — Documentation and release

- [ ] **L4.1 — Agent model: Luna.** Update `docs/API.md` and/or
  `openNASR/plotting.py`'s module/function docstrings to document the new
  indexing objects' snapshot semantics (mirroring
  `RouteResolver`'s existing documented "construct a new instance after
  mutating a table" contract) and, if T3.1 added a reusable index parameter
  to `plot_airport_procedures`, document the batch-plotting use case it
  enables.
  Dependencies: T2.3, T3.2.
- [ ] **L4.2 — Agent model: Luna.** Record the full before/after benchmark
  report (Phase 2 and Phase 3 numbers, environment, canonical cycle,
  cold/warm policy) using L1.3's template, linked from both this document
  and `ROUTE_PATH_PLAN.md` (the two plans now share one performance
  narrative for `flightplan.py`; cross-link rather than duplicate numbers).
  Dependencies: L2.4, L3.3.
- [ ] **S4.3 — Agent model: Sol.** Run the full release gate (`pytest`,
  `ruff format --check`, `ruff check`, `mypy openNASR`, `python -m build`,
  `twine check dist/*`) from a clean checkout and confirm all six commands
  pass, matching the convention every other plan in this repository closes
  with.
  Dependencies: L4.1, L4.2.

**Gate 4:** Sol approves release: both benchmark tools, the audit table from
Phase 0, and the recorded before/after numbers are complete and consistent;
the full release gate passes.

## Decision log

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-17 | Scope this plan to `openNASR/flightplan.py`'s procedure tables and `openNASR/plotting.py`, with a Phase 0 audit rather than assuming every `.to_dict(orient="records")` call site in the package is slow. | Direct inspection found `openNASR/repository.py`'s equivalent lookups (`_class_airspace`, `_military_operations`, `_related_records`) already vectorize-then-materialize and already cache via `_related_index`; only `flightplan.py`'s procedure lookups (never covered by `ROUTE_PATH_PLAN.md`'s Phase 4, which only vectorized `_WaypointResolver` and the `AWY_BASE` airway lookup) and all of `plotting.py` (never covered by any prior performance work) were confirmed slow by direct measurement. Auditing first avoids speculative rewrites of code that is already fine. |
| 2026-08-17 | Benchmark `plotExamples/`-equivalent calls as cold single-call and repeated-call cases, not only a single representative call. | Direct measurement found `_airway_segments` costs ~2.0s and `_procedure_segments` ~1.5s per call with no caching at all, so a batch-plotting scenario (ten airports) pays the full cost every time — ~14.8s for just the departure layer across ten calls. A single-call benchmark would hide this repeated-call multiplier the same way `ROUTE_PATH_PLAN.md`'s single-route Gate 4 benchmark (8.86µs) hid the ~430× procedure-route cost gap this plan's Phase 0 found. |
| 2026-08-17 | Reuse `_WaypointResolver`/`_AirwayIndex`'s exact indexing technique for the new `_ProcedureIndex` and plotting index, rather than inventing a new caching approach. | Two indexing patterns already exist in this codebase (`ROUTE_PATH_PLAN.md`'s T4.1/T4.2, and `openNASR/repository.py`'s pre-existing `_related_index`) and both are proven correct and tested; a third, different style would add maintenance cost without a demonstrated need. |
| 2026-08-17 | Move all benchmarking code and data (`duckdb_benchmark.py`, `flightplan_benchmark.py`, `route_benchmark.py`, and `tests/exampleRoutes.csv`) from `tools/`/`tests/` into a new `benchmarks/` directory, and add `benchmarks/run_benchmarks.py` as a new, primary, human-readable entry point rather than extending `route_benchmark.py` in place. | Requested directly: one folder for all benchmarking code and data, with clear average-based output from diverse real input (random flight plans) rather than raw JSON or a fixed 6-route synthetic matrix. `route_benchmark.py`'s existing JSON/fixed-matrix report remains useful for machine comparison and was kept as is, alongside the new script, rather than conflating two different report shapes in one file. `tests/exampleRoutes.csv` was untracked (2.3MB, not committed); moved and committed to `benchmarks/data/example_routes.csv` after confirming it contains only public route-field strings with no personal or licensed content, so the benchmark is self-contained for anyone who clones the repository. |
