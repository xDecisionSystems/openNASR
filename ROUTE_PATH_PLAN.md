# FAA Route-Field to Lat/Lon Path Improvement Plan

## Goal

Convert a filed FAA domestic route field into a faithful ordered sequence of
latitude/longitude coordinates using a selected NASR cycle.  The conversion
must understand airports, fixes, navaids, published low/high airways,
departures, arrivals, and direct segments without presenting the result as an
operational route validation or clearance tool.

The immediate target is substantially better coverage of the representative
`tests/exampleRoutes.csv` data when using the matching NASR cycle.  Domestic
NASR route content is in scope. International airports, foreign procedures,
oceanic routes, and coordinate fixes are deliberately recorded as separate
coverage work rather than silently guessed from domestic data.

## Baseline and Success Measures

- [ ] Record a reproducible baseline using 100 randomly selected rows from
  `tests/exampleRoutes.csv`, a fixed seed, and an explicitly selected cycle.
  The 2026-05-14 baseline is 38 successful paths and 62 failures.
- [x] **Independently reproduced (2026-08-17):** a separate 60-route,
  seed-42 sample against the `2024-06-13` cycle scored 21 successes / 39
  failures (~35%), consistent with the recorded baseline. The dominant
  failure category by a wide margin (roughly two-thirds of failures in this
  sample) was a bare procedure name reaching the airway-resolution branch
  and failing there — see the new Phase 1/Phase 2 bullets. This confirms
  procedure-resolution/parser-classification errors, not missing NASR data
  or genuinely international content, are the largest lever for the
  domestic success rate; prioritize Phase 1/2 fixes accordingly.
- [ ] Categorize each failure as a parser error, procedure-resolution error,
  airway-resolution error, waypoint ambiguity, missing NASR data, or malformed
  input. Retain at least one representative route for every category.
  **A misclassified-bare-procedure failure currently surfaces as an
  airway-resolution error (`RecordNotFoundError` naming "Airway path"); when
  building the categorized sample, verify each such failure's route text
  against the procedure tables before accepting the error type at face
  value, since the message alone is misleading for this category.**
- [ ] Add a non-flaky regression sample covering each supported route form.
- [ ] Set and document a domestic-only success target after the sample is
  classified. Exclude rows requiring non-NASR international/oceanic data from
  the domestic coverage denominator, but report them separately.
- [ ] Benchmark cold and warm conversion separately. A warm benchmark must
  measure path generation only after the NASR tables and resolver indexes are
  ready. **This bullet is not optional polish: measured today, a single call
  costs ~2.7s dominated by a from-scratch resolver rebuild (see Phase 4), so
  a 100-route baseline sample alone costs minutes and the full
  46,580-row file is impractical until that is fixed.**

## Product Contract

- [ ] Keep `flight_plan_path(nasr, flight_plan)` as the simple public API and
  return ordered `(latitude, longitude)` tuples.
- [ ] Document supported input forms: whitespace-separated and FAA dotted
  route fields; `..` direct routing; optional trailing `/speed-altitude`;
  airports, fixes, navaids, airways, DPs, STARs, and transitions.
- [ ] Define a typed result/error policy: unknown domestic record,
  ambiguous record, unsupported external/oceanic content, malformed route
  text, and broken published connectivity must be distinguishable.
- [ ] Preserve source coordinates and source ordering. Do not infer missing
  legs, manufacture geometries, or claim that a returned path is a legal or
  cleared route.

## Phase 1 — Parser and Token Classification

- [ ] Replace the broad lexical airway decision with a data-backed decision:
  a token is an airway only when it has a matching `AWY_BASE` record in the
  selected NASR cycle.
- [x] **Verified against `openNASR/flightplan.py` (2026-08-17):** the current
  `flight_plan_path` dispatch already does this for the airway *branch*
  (`_AIRWAY.fullmatch(token)` gated behind `"AWY_BASE" in nasr`), but the
  dispatch order still lets the regex win over procedure resolution for a
  bare token. Confirmed against 60 real `tests/exampleRoutes.csv` rows on
  the `2024-06-13` cycle: the dominant failure (roughly two-thirds of all
  failures) is a bare STAR/DP name such as `GNDLF3`, `SCAMR4`, `JASPA7`, or
  `RETYR8` reaching the airway branch and failing as
  `Airway path record 'GNDLF3' was not found`, because
  `flight_plan_path` only calls `_procedure_path` when `"." in token` (line
  442) — a bare procedure never gets the chance. See the new Phase 1 bullet
  below and the `2026-08-17` Decision log entry.
- [ ] **Check bare tokens against the procedure tables before the airway
  regex, not only dotted tokens.** `_tokenize_flight_plan` already probes
  `_procedure_path` for dotted pairs to decide whether to merge them; extend
  the same probe to every bare token that matches the airway regex, so a
  bare `DP_COMPUTER_CODE`/`STAR_COMPUTER_CODE` match takes priority over an
  `AWY_BASE` lookup. Add a regression fixture reproducing `GNDLF3` (a real
  arrival transition name that also happens to match the airway
  letters-then-digit pattern) resolving as a procedure, not an airway
  lookup failure.
- [ ] Parse dotted route fields into a lossless token stream. Preserve the
  distinction between `.` component separators and `..` direct segments.
- [ ] Strip only the trailing speed/altitude suffix from the route field;
  retain the original token positions for diagnostics.
- [ ] Recognize airport endpoint context, including FAA location identifiers
  and the currently supported domestic ICAO/airport identifiers.
- [ ] Add parser tests for mixed spaces/dots, consecutive direct segments,
  repeated airways, empty components, and malformed suffixes.

## Phase 2 — Departures and Arrivals

- [ ] Resolve a bare departure name such as `RUGGD3` or `BAYLR6` when it
  follows the departure airport. It must not be interpreted as an airway.
- [ ] Resolve a bare arrival name when it precedes the destination airport.
  **This is the single largest observed failure category (Phase 1), not an
  already-working case** — prioritize accordingly relative to the dotted
  forms below.
- [ ] Resolve `PROCEDURE.TRANSITION` forms such as `ORCO8.TRM` and
  `TORGY4.SSWAN` using the FAA procedure tables.
- [ ] **Do not let the tokenizer's greedy dot-merge silently accept a wrong
  procedure interpretation.** Verified against real data: `MCRAY2.MCRAY`
  (filed as `KIAD.MCRAY2.MCRAY.Q178.LEJOY...`) is not
  `PROCEDURE.TRANSITION` — `MCRAY2` is the DP name and `MCRAY` is a plain
  enroute fix filed redundantly after it, not a transition identifier. The
  current tokenizer merges the pair anyway because `_procedure_path`
  silently returns a non-`None` result for it (falling back to the DP's
  default routing, which does not end at `MCRAY`), so the airway lookup
  that follows uses the wrong `from` waypoint (`HAYGR` instead of `MCRAY`)
  with no error raised. Resolving `PROCEDURE.CANDIDATE` must verify the
  candidate is actually a published transition/runway identifier for that
  procedure (not just that *some* procedure route exists), and fall back to
  treating the two components as separate tokens — procedure name, then
  plain waypoint — when it is not.
- [ ] Use neighboring route tokens to choose the applicable procedure
  transition or runway/common portion. If more than one published candidate
  remains, raise a typed ambiguity instead of selecting arbitrarily.
- [ ] Support routes that combine a DP, direct segment, airway, fix/navaid,
  and STAR; deduplicate only adjacent identical coordinates at joins.
- [ ] Test a current-cycle valid route for each of: bare DP, dotted DP,
  bare STAR, dotted STAR, DP-to-airway, airway-to-STAR, and procedure-only
  airport pairs. **Also add the two real-route regressions found above:**
  a bare mid-route STAR name (`GOLLM.GNDLF3.KATL`) and a DP name
  immediately followed by a plain enroute fix, not a transition
  (`MCRAY2.MCRAY.Q178...`).

## Phase 3 — Airways and Contextual Waypoints

- [ ] Resolve airway paths only between confirmed endpoint records and support
  both directions through the published sequence.
- [ ] Correctly distinguish high/low/Q/T/other FAA airway designations from
  arbitrary alphanumeric tokens.
- [ ] Use context to disambiguate duplicate identifiers such as `ABQ`, `SEA`,
  `STL`, and `PVD`: procedure/airway connection fields take priority, then
  fix/navaid, with airports preferred at route endpoints.
- [ ] **Prefer a non-`VOT` navaid when a `NAV_ID` collides within `NAV_BASE`
  itself.** Verified against real data: `ICT` matches two distinct
  `NAV_BASE` rows (`NAV_TYPE=VORTAC` and `NAV_TYPE=VOT`) at different
  coordinates, so `KBBG..EOS..ICT..KHUT` currently raises
  `AmbiguousRecordError` even though only one of the two is ever a valid
  filed waypoint. A VOT ("VOR test facility") is a ground calibration
  signal, never a route fix; when a same-table `NAV_ID` collision includes
  exactly one non-`VOT` candidate, prefer it instead of raising ambiguity.
  This is a same-*table* collision, distinct from the existing
  cross-table (`APT_BASE`/`FIX_BASE`/`NAV_BASE`) disambiguation the
  resolver already performs.
- [ ] Validate that an airway endpoint exists on the selected airway and that
  every expanded intermediate identifier resolves to one unambiguous source
  coordinate.
- [ ] Add regression tests for forward/reverse routes, repeated airway
  designations, airway transition joins, and intentionally ambiguous names.
  **Include the `ICT`-style same-table `VOT`-versus-operational-navaid
  case as its own fixture**, not only cross-table duplicates.

## Phase 4 — Performance and Reuse

**Measured severity (2026-08-17, real `2024-06-13` cycle, ~68k `FIX_BASE` +
~20k `APT_BASE` + ~1.8k `NAV_BASE` rows):** a single `flight_plan_path` call
took **~2.7 seconds** end to end (table load ~0.4s, everything else
essentially all resolver construction — a standalone `_WaypointResolver`
build measured ~2.8s on its own, matching within timing noise).
`flight_plan_path` builds one from scratch on every call
(`openNASR/flightplan.py` line 429) by converting all three tables to Python
dicts row-by-row (`.to_dict(orient="records")`) rather than reusing anything
across calls. At that per-call cost, the full 46,580-row
`tests/exampleRoutes.csv` would take on the order of **35 hours**
sequentially — this makes Phase 5's "run the deterministic sample after each
phase" and any full-file validation mode practically unusable until this
phase lands, so **this phase should not be scheduled strictly after Phases
1-3 finish**; at minimum, the once-per-dataset resolver cache should land
early enough that Phase 5's baseline/regression sampling isn't itself
bottlenecked on it. `_airway_vertices` has the same anti-pattern on
`AWY_BASE` (a full `.to_dict(orient="records")` scan of ~1,537 rows per
airway token instead of vectorized pandas filtering); both need to move off
row-by-row Python iteration, not only the waypoint resolver named below.
- [ ] Build the airport/fix/navaid candidate index once per immutable NASR
  dataset instead of rebuilding it for every `flight_plan_path` call.
- [ ] **Vectorize `_WaypointResolver.__init__`; do not just cache the slow
  version.** The ~2.8s cost is `.to_dict(orient="records")` plus a Python
  `for` loop materializing a dict per row across ~90k rows. Replace it with
  column-oriented pandas operations: for each `(table, columns)` pair, drop
  rows with missing `LAT_DECIMAL`/`LONG_DECIMAL` via a vectorized mask
  (`frame[["LAT_DECIMAL", "LONG_DECIMAL"]].notna().all(axis=1)`, or the
  DuckDB-backed equivalent), then build the identifier index by iterating
  `zip(frame[column], frame["LAT_DECIMAL"], frame["LONG_DECIMAL"])` — a
  column-array walk, not a per-row dict allocation — or a single
  `frame.groupby(column)` per identifier column. Target: this construction
  drops from ~2.8s to well under 100ms on the same real cycle; verify with
  a microbenchmark before and after, not just the end-to-end call time.
- [ ] **Vectorize `_airway_vertices`'s `AWY_BASE` lookup the same way.**
  Replace the `for record in base.to_dict(orient="records")` scan with a
  boolean-mask filter on `AWY_DESIGNATION`/`AWY_ID` (matching the pattern
  `AirportRepository`/other domain repositories already use elsewhere in
  the codebase — grep for `.map(_text).eq(` for the existing convention),
  then only convert the *matched* rows (typically one airway, a handful of
  rows) to records, not the full ~1,537-row table. This table is smaller
  than the waypoint tables but is rescanned once per airway token in a
  route, not once per call, so its relative cost grows with route
  complexity.
- [ ] **Cache the vectorized resolver, keyed by the identity of the
  underlying table set, so repeated calls against the same loaded `NASR`
  reuse it.** Vectorizing fixes the *per-build* cost; caching fixes the
  *rebuild-every-call* cost — both are needed for the batch/Phase-5 use
  case, since even a sub-100ms rebuild is wasted work when nothing in the
  underlying tables changed between calls. A plain `functools.lru_cache`
  is not safe here (DataFrames are unhashable and mutable); key on
  `id(nasr)` plus each relevant table's row count as a cheap staleness
  check, or accept an explicit resolver/session object (see the next
  bullet) as the real cache boundary instead of an implicit global cache.
- [ ] Keep public results and errors identical with and without the cache;
  add mutation/isolation tests for CSV and DuckDB storage.
- [ ] Add an optional route resolver/session object for batch conversion while
  preserving the existing one-call function. **This is the primary
  mechanism for avoiding repeated resolver construction across many
  `flight_plan_path`-equivalent calls** (e.g. `RouteResolver(nasr)` built
  once, then `.path(flight_plan)` called per route) — prefer it over an
  implicit module-level or `NASR`-attached cache, since an explicit object
  makes the cache's lifetime and invalidation visible to the caller instead
  of hidden behind the existing one-call function signature.
- [ ] Benchmark CSV and DuckDB storage with the same already-loaded tables,
  fixed routes, warm-up policy, sample count, median, and p95. The benchmark
  matrix must include direct airport-to-airport routing, fix/navaid routing,
  airway-only routing, DP-to-airway routing, airway-to-STAR routing, and a
  route containing both a DP and STAR. Report loading time separately from
  path resolution.
- [ ] For every procedure benchmark, report the number of procedure legs and
  expanded path coordinates, the selected procedure/transition identifiers,
  and whether the timing is cold (first procedure-table materialization) or
  warm (all required procedure tables and indexes already loaded).
- [ ] Ensure no raw SQL API is introduced for route conversion and retain
  source-order fidelity in DuckDB-backed reads.

## Phase 5 — Batch Validation and Diagnostics

- [ ] Add a maintained validation command or test utility that samples route
  rows deterministically by seed and records success/failure totals without
  modifying the input CSV.
- [ ] Report failure type, token, token position, selected cycle, and route
  text. Avoid printing entire candidate datasets in normal output.
- [ ] Run the 100-route deterministic sample after each phase and compare it
  to the baseline by category.
- [ ] Maintain a small, cycle-pinned procedure evaluation set containing a
  bare DP, dotted DP transition, bare STAR, dotted STAR transition, DP-to-
  airway, airway-to-STAR, and DP-to-airway-to-STAR route. Verify both the
  expected ordered procedure connection identifiers and non-empty lat/lon
  output before using these routes in performance measurements.
- [ ] Add an opt-in full-file validation mode suitable for CI artifacts or a
  local benchmark; do not make routine unit tests depend on the large file.

## Phase 6 — Explicit Non-Domestic and Oceanic Policy

- [ ] Detect and label records outside domestic NASR coverage: foreign ICAO
  airports, international airways/procedures, and coordinate fixes such as
  `4500N/05000W`.
- [ ] Decide whether coordinate fixes should be parsed locally into latitude/
  longitude while still treating their connecting non-NASR route structure as
  unsupported.
- [ ] Evaluate optional data providers for international aeronautical data;
  require a source-license, cycle/effective-date, provenance, and cache policy
  before adding one.
- [ ] Keep this expansion opt-in so the domestic NASR-only contract remains
  deterministic and offline-capable.

## Release Gates

- [ ] Full unit suite passes for CSV and DuckDB storage.
- [ ] New procedure, airway, ambiguity, and parser regression tests pass.
- [ ] The deterministic validation sample improves without increasing known
  domestic-parser regressions.
- [ ] Documentation states the selected-cycle requirement, supported syntax,
  external/oceanic limitations, and non-operational-use disclaimer.
- [ ] Record benchmark environment, cycle, storage backend, and warm/cold
  timings in the release notes or benchmark artifact.

## Decisions

| Date | Decision | Rationale |
| --- | --- | --- |
| 2026-08-17 | Treat a token as an airway only after confirming it in the selected cycle's FAA airway table. | Procedure names frequently resemble airway identifiers; lexical matching caused departures such as `RUGGD3` to be misclassified. |
| 2026-08-17 | Separate domestic NASR correctness from international/oceanic coverage. | The example data includes both categories, but NASR alone cannot authoritatively resolve foreign records. |
| 2026-08-17 | Measure warm resolution independently of NASR loading and index construction. | Batch callers need route-conversion performance, while cold loading is a distinct storage/cache concern. |
| 2026-08-17 | Include procedure expansion in correctness and performance evaluation. | Departures and arrivals exercise different tables, transition selection, and path expansion than direct or airway-only routes; excluding them would give a misleading conversion benchmark. |
| 2026-08-17 | Reviewed the plan against the actual `openNASR/flightplan.py` implementation and a real 60-route sample on the `2024-06-13` cycle before editing it; found and recorded four concrete gaps rather than only rephrasing the existing bullets. | The plan already existed as a proposal; verifying it against real code and real data (not just prose review) surfaced specific, reproducible bugs the original bullets described in principle but not in enough detail to implement directly, and one severity finding (Phase 4's performance cost) that changes phase sequencing advice. |
| 2026-08-17 | Prioritize bare (non-dotted) procedure misclassification as an airway over other Phase 1/2 work. | It is the dominant real-world failure mode (roughly two-thirds of the reproduced sample's failures, e.g. `GOLLM.GNDLF3.KATL`): `flight_plan_path` only probes `_procedure_path` when a token contains a dot, so a bare STAR/DP name always reaches the airway regex first and fails with a misleading "Airway path... not found" error instead of resolving as a procedure. |
| 2026-08-17 | Require `PROCEDURE.CANDIDATE` resolution to verify the candidate is a published transition/runway identifier, not merely that some route exists for the procedure name. | Verified against real data that the tokenizer's greedy dot-merge accepts `MCRAY2.MCRAY` as one procedure token even though `MCRAY` is a plain enroute fix filed after the DP, not a transition; `_procedure_path` silently falls back to the DP's default routing and the airway lookup that follows then uses the wrong endpoint with no error raised. |
| 2026-08-17 | Prefer a non-`VOT` navaid when a bare `NAV_ID` collides within `NAV_BASE` itself, instead of always raising ambiguity. | Verified against real data (`ICT`: one `VORTAC` row, one `VOT` row, different coordinates) that a VOR-test-facility component can share an identifier with the real operational navaid; a VOT is never a valid filed route fix, so this collision has one correct answer, unlike a genuine cross-table or cross-airport ambiguity. |
| 2026-08-17 | Do not schedule Phase 4's resolver-caching work strictly after Phases 1-3 finish. | Measured a single `flight_plan_path` call at ~2.7s on a real cycle, almost entirely spent rebuilding `_WaypointResolver` from three full tables (~90k rows) on every call; at that cost a 100-route baseline sample takes minutes and the full 46,580-row example file is impractical (~35h extrapolated), which would bottleneck Phase 5's own "run the sample after each phase" requirement before Phase 4 ever starts. |
| 2026-08-17 | Specify vectorization (column-oriented pandas operations, not just caching the existing row-by-row builder) as the primary Phase 4 fix for both `_WaypointResolver.__init__` and `_airway_vertices`, with an explicit resolver/session object as the caching layer on top. | A quick vectorized-mask-plus-`zip` prototype over the real `FIX_BASE` table (68,122 rows, the largest of the three) ran in ~0.14s versus multiple seconds for the existing `.to_dict(orient="records")` loop, confirming the row-by-row conversion itself — not merely the lack of a cache — is the dominant cost; caching a slow builder would still leave the first call (and any cache miss) slow, while a plain `functools.lru_cache` cannot key on unhashable, mutable DataFrames safely. |
