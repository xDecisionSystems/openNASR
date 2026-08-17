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

Most production work in this plan is against `openNASR/flightplan.py`
(currently 504 lines: `_Waypoint`, `_WaypointResolver`, `_waypoint`,
`_airway_vertices`, `_route_rows_points`, `_procedure_path`,
`_tokenize_flight_plan`, `flight_plan_path`) and its test file
`tests/test_flightplan.py`. If Phase 4 exposes `RouteResolver` as a package
API, `openNASR/__init__.py` must also export it; benchmark tooling and API
documentation may change their respective files.

## Agent roster and roles

Reuses the roster convention from `DUCKDB_PLAN.md`. The model named in every
task heading is its assigned agent model; roles describe the expected work.
Each in-flight task has exactly one owning agent.

| Agent model | Role | Responsibility |
| --- | --- | --- |
| **Sol** | Research/review | Diagnosis, benchmark/measurement design, ambiguity-policy and disambiguation-rule design, gate approval. Sol does not implement production fixes; Sol verifies findings against real code/data and reviews implementations against them. |
| **Terra** | Implementation | Production implementation in `openNASR/flightplan.py`: parser, procedure resolution, airway resolution, performance/caching. |
| **Luna** | Tests/tooling | Fixtures, regression tests, the batch-validation utility, benchmark tooling, and documentation. Luna's tests must fail against the current, unfixed behavior and pass once Terra's fix lands. |

## Coordination rules

- **One file, sequential ownership.** Nearly every task below edits
  `openNASR/flightplan.py`. Do not run two Terra tasks on this file in
  parallel from the same base — merge task *N* before starting task *N+1*
  when both touch `flightplan.py`, even if they are nominally in different
  phases. Tasks that only add tests or fixtures (Luna) may run in parallel
  with an open Terra task, but must rebase before merging if Terra's task
  merges first.
- **Every task cites the exact function and line(s) it changes** so a
  sub-agent can locate the edit without re-reading the whole module first.
- **Every numbered task names its required model explicitly** as `Agent
  model: Sol`, `Agent model: Terra`, or `Agent model: Luna` in its heading.
- **Every task ends with a test that fails before the fix and passes
  after.** Reproduction routes are given verbatim in each task; use them as
  fixture input, not just as manual verification.
- **Gate authority:** Sol signs off each phase gate below (`**Gate N:**`)
  by adding a dated Decision-log row naming the gate. The next phase's
  tasks should not start until the prior gate is recorded, except where a
  task explicitly says it is unblocked early (see Phase 4's dependency
  note).
- Every task that changes matching/dispatch/disambiguation behavior adds a
  Decision-log row.

## Baseline and Success Measures

- [x] **T0.1 — Agent model: Sol. Done (2026-08-17).** Record a reproducible baseline.
  The canonical comparison baseline is 100 rows selected with Python's
  `random.Random(20260514).sample(...)` from the 46,580 non-empty rows of
  `tests/exampleRoutes.csv`, using NASR cycle `2026-05-14`, CSV storage, and
  one shared read-only waypoint resolver. Its source-file SHA-256 is
  `9c52331afa6c8ac5fe661050370bc2fa7ecd87412e241fc55c4f6daf65e6f03c`,
  selected-index SHA-256 is
  `e4a8cbf7b5428f7dc01fc5b89d4264fc2b25e5c85010f3f19ffd2775944773b2`,
  selected-route SHA-256 is
  `71e060c887646a17681bd8541c8b8f8f0916bfb5cf370290b2aec321e9961750`,
  and the result is 38 successes / 62 failures. The dominant observed
  category is bare procedure names reaching airway resolution — see T1.1.
  The separate 60-row, `2024-06-13` reproduction remains diagnostic evidence
  only; do not compare phase-gate counts across different cycle dates.
- [ ] **T0.2 — Agent model: Sol.** Categorize each of T0.1's failures as: parser error,
  procedure-resolution error, airway-resolution error, waypoint ambiguity,
  missing NASR data, or malformed input. Retain at least one representative
  route per category as a named fixture (not just a CSV row reference) for
  reuse by later regression tests.
  Caution verified during T0.1: a misclassified-bare-procedure failure
  (T1.1) surfaces as `RecordNotFoundError` naming "Airway path" — do not
  accept that message at face value as an airway-resolution error; check
  whether the failing token resolves via `_procedure_path` before
  classifying it.
  Acceptance: a table (in this file or a linked note) listing each of the
  60-100 sampled routes' category, with the representative fixture routes
  named explicitly.
- [ ] **T0.3 — Agent model: Luna.** Add a non-flaky regression sample: a fixed, curated
  list of route strings (not a random sample) covering each category from
  T0.2, checked into `tests/` as a small fixture file or Python list. Must
  not depend on `tests/exampleRoutes.csv` being present, since that file is
  local-only test data, not a tracked repository asset (verified 2026-08-17:
  `tests/exampleRoutes.csv` is untracked and un-ignored in this repository).
  Dependencies: T0.2.
- [ ] **T0.4 — Agent model: Sol.** Set and document a domestic-only success target once
  T0.2's categorization exists. Exclude rows requiring non-NASR
  international/oceanic data (Phase 6) from the domestic denominator;
  report them as a separate count, not silently dropped.
  Dependencies: T0.2.
- [x] **T0.5 — Agent model: Sol. Done (2026-08-17).** Benchmark cold vs. warm
  conversion separately; a warm benchmark measures path generation only
  after NASR tables and resolver indexes are ready. Measured: a single
  `flight_plan_path` call costs ~2.7s end to end on a real cycle, almost
  entirely `_WaypointResolver` construction (~2.8s standalone, within
  timing noise of the full call). At that cost, a 100-route baseline sample
  costs minutes and the full 46,580-row file is impractical
  (~35h extrapolated) until Phase 4 lands. See Phase 4.

## Product Contract

- [ ] **T0.6 — Agent model: Terra.** Keep `flight_plan_path(nasr, flight_plan)` as the
  public API (`openNASR/flightplan.py:410`) returning ordered
  `(latitude, longitude)` tuples; every task in this plan must preserve
  this signature and return type.
- [ ] **T0.7 — Agent model: Luna.** Document supported input forms in the module
  docstring and/or `docs/API.md`: whitespace-separated and FAA dotted route
  fields; `..` direct routing; optional trailing `/speed-altitude`;
  airports, fixes, navaids, airways, DPs, STARs, and transitions.
  Dependencies: Phase 1-3 tasks (so the documented contract matches actual
  behavior, not aspirational behavior).
- [ ] **T0.8 — Agent model: Sol.** Define the typed result/error policy precisely:
  which existing `openNASR.exceptions` class is raised for each of unknown
  domestic record, ambiguous record, unsupported external/oceanic content,
  malformed route text, and broken published connectivity. Verified
  2026-08-17: the current code already uses `RecordNotFoundError` and
  `AmbiguousRecordError` from `openNASR.exceptions` throughout
  `flightplan.py`; confirm this is sufficient or specify any new typed
  exception needed (e.g. for unsupported oceanic content, Phase 6).
- [ ] **T0.9 — Agent model: Terra.** Preserve source coordinates and source ordering in
  every fix in this plan. Do not infer missing legs, manufacture
  geometries, or claim a returned path is a legal or cleared route — this
  is a standing constraint checked in code review for every task below, not
  a separate task to schedule.

## Phase 1 — Parser and Token Classification

- [x] **T1.0 — Agent model: Sol. Verified (2026-08-17).** `flight_plan_path`'s airway
  branch gates only on a lexical `_AIRWAY.fullmatch(token)` and the presence
  of the `AWY_BASE` table (`flightplan.py:451-452`); it does **not** verify
  that the token has a matching airway record until `_airway_vertices` runs.
  Dispatch order still lets that lexical branch win over procedure resolution
  for a *bare* (non-dotted) token, because
  `_procedure_path` is only called `if "." in token`
  (`flightplan.py:441-442`). Confirmed against 60 real
  `tests/exampleRoutes.csv` rows on the `2024-06-13` cycle: this is the
  dominant failure, roughly two-thirds of all failures in the sample —
  bare STAR/DP names such as `GNDLF3`, `SCAMR4`, `JASPA7`, `RETYR8` reach
  the airway branch and fail as
  `Airway path record 'GNDLF3' was not found` instead of resolving as a
  procedure.
- [ ] **T1.1 — Agent model: Terra.** Fix the bug found in T1.0. In
  `flight_plan_path`'s main dispatch loop (`flightplan.py:436-500`), before
  the airway-regex branch at line 451, probe `_procedure_path` for any bare
  token that matches `_AIRWAY.fullmatch`, not only dotted tokens. A bare
  `DP_COMPUTER_CODE`/`STAR_COMPUTER_CODE` match must take priority over an
  `AWY_BASE` lookup.
  Reproduction (use as the regression fixture): route text
  `...GOLLM.GNDLF3.KATL/0043` on the `2024-06-13` cycle (or an equivalent
  bare-STAR-name fixture built for a synthetic cycle) must resolve `GNDLF3`
  as a STAR, not raise `RecordNotFoundError` naming "Airway path".
  Acceptance: a regression test asserts the expected ordered procedure
  connection identifiers (or their exact coordinates), verifies that the
  following route segment begins at the procedure's intended exit point, and
  fails on the current code rather than only asserting a non-empty path.
  Dependencies: none (this is the first Terra task in the plan).
- [ ] **T1.2 — Agent model: Terra.** Parse dotted route fields into a lossless token
  stream in `_tokenize_flight_plan` (`flightplan.py:364-407`). Preserve the
  distinction between `.` component separators and `..` direct segments;
  this is largely already implemented (verify with a test, don't assume a
  rewrite is needed) — confirm existing behavior with
  `test_flight_plan_path_accepts_double_dot_direct_routing`
  (`tests/test_flightplan.py:242`) before changing anything.
- [ ] **T1.3 — Agent model: Terra.** Strip only the trailing speed/altitude suffix from
  each whitespace field (`flightplan.py:381`, `field.split("/", 1)[0]`);
  retain the original token positions for diagnostics used by Phase 5's
  error reporting (T5.2).
- [ ] **T1.4 — Agent model: Terra.** Recognize airport endpoint context, including FAA
  location identifiers and domestic ICAO identifiers, in
  `_waypoint`/`_WaypointResolver` (`flightplan.py:30-163`) via the existing
  `preferred_tables` mechanism. Verify against a route with both an FAA
  identifier and an ICAO identifier endpoint (e.g. `KBWI...` vs. `BWI...`
  if both resolve).
  Dependencies: T1.1 (avoid rebasing token-classification changes twice).
- [ ] **T1.5 — Agent model: Luna.** Add parser tests for mixed spaces/dots, consecutive
  direct segments, repeated airways, empty components, and malformed
  suffixes, extending `tests/test_flightplan.py`.
  Dependencies: T1.1-T1.4 merged.

**Gate 1:** Sol confirms T1.1's fix resolves the dominant real-world failure
category (re-run the T0.1 sample or an equivalent subset) and records the
gate with the before/after success count.

## Phase 2 — Departures and Arrivals

- [ ] **T2.1 — Agent model: Terra.** Resolve a bare departure name (e.g. `RUGGD3`,
  `BAYLR6`) following the departure airport. **Depends on and is largely
  satisfied by T1.1** — confirm with a dedicated bare-DP-after-departure-
  airport regression rather than assuming T1.1 alone covers every case
  (T1.1's fixture is a bare *arrival* mid-route; a bare *departure*
  immediately after the origin airport is a related but distinct code path
  through `_tokenize_flight_plan`/dispatch and needs its own test).
  Dependencies: T1.1.
- [ ] **T2.2 — Agent model: Terra.** Resolve a bare arrival name preceding the
  destination airport. **This and T2.1 are the single largest observed
  failure category (Phase 1's T1.0 finding), not an already-working case**
  — prioritize ahead of the dotted forms below (T2.3-T2.4).
  Dependencies: T1.1.
- [ ] **T2.3 — Agent model: Terra.** Resolve `PROCEDURE.TRANSITION` forms such as
  `ORCO8.TRM` and `TORGY4.SSWAN` via `_procedure_path`
  (`flightplan.py:262-361`), which already implements this for the
  documented cases — verify with
  `test_flight_plan_path_expands_departure_and_arrival_procedures`
  (`tests/test_flightplan.py:118`) before assuming new work is needed here
  beyond T2.4's fix.
- [ ] **T2.4 — Agent model: Terra.** Fix the greedy-dot-merge bug verified 2026-08-17:
  `_tokenize_flight_plan` (`flightplan.py:393-406`) merges any dotted pair
  into one token whenever `_procedure_path(combined, ...)` returns
  non-`None` — but it does not verify the *second* component is actually a
  published transition/runway identifier for that procedure. Reproduction:
  route `KIAD.MCRAY2.MCRAY.Q178.LEJOY.DEMME5.KPIT/0037` on the `2024-06-13`
  cycle. `MCRAY2` is a real DP name; `MCRAY` is a plain enroute fix filed
  redundantly after it, not a transition. `_procedure_path("MCRAY2.MCRAY")`
  silently falls back to the DP's default routing (ending at `HAYGR`, not
  `MCRAY`), so the airway lookup that follows for `Q178` uses the wrong
  `from` waypoint with no error raised — verified directly:
  `_tokenize_flight_plan` returns `('KIAD', 'MCRAY2.MCRAY', 'Q178',
  'LEJOY.DEMME5', 'KPIT')` and `_procedure_path('MCRAY2.MCRAY', ...)`
  returns a path whose last point is `HAYGR`.
  Fix: `_procedure_path` (or a new check in `_tokenize_flight_plan` before
  it merges the pair) must verify the candidate after the dot is an actual
  published `TRANSITION_COMPUTER_CODE` (or runway/common-portion
  identifier) for the matched `DP_COMPUTER_CODE`/`STAR_COMPUTER_CODE`, not
  merely that *some* route exists for the procedure name. When the
  candidate is not a valid transition, the tokenizer must fall back to
  treating the two components as separate tokens: the bare procedure name
  (resolved by T2.1/T2.2's fix), then a plain waypoint.
  Acceptance: for the reproduction route, the airway lookup for `Q178` uses
  `MCRAY` as its `from` waypoint, not `HAYGR`; a new test fails on current
  code and passes after the fix.
  Dependencies: T1.1, T2.1, T2.2 (shares dispatch/tokenizer code with all
  three; land after them to avoid re-resolving merge conflicts in the same
  functions).
- [ ] **T2.5 — Agent model: Terra.** Use neighboring route tokens to choose the
  applicable procedure transition or runway/common portion. If more than
  one published candidate remains, raise a typed ambiguity
  (`AmbiguousRecordError`, already used elsewhere in this module) instead
  of selecting arbitrarily.
  Dependencies: T2.4.
- [ ] **T2.6 — Agent model: Terra.** Support routes that combine a DP, direct segment,
  airway, fix/navaid, and STAR in one route string; deduplicate only
  adjacent identical coordinates at joins (matches the existing dedup
  pattern already used in `flight_plan_path`, e.g. lines 447-448, 498-499 —
  reuse it, don't add a second dedup mechanism).
  Dependencies: T2.1-T2.5.
- [ ] **T2.7 — Agent model: Luna.** Test a current-cycle valid route for each of: bare
  DP, dotted DP, bare STAR, dotted STAR, DP-to-airway, airway-to-STAR, and
  procedure-only airport pairs. Also add the two real-route regressions
  verified 2026-08-17 as their own named fixtures: a bare mid-route STAR
  name (`GOLLM.GNDLF3.KATL`, T1.1) and a DP name immediately followed by a
  plain enroute fix, not a transition (`MCRAY2.MCRAY.Q178...`, T2.4).
  Dependencies: T2.1-T2.6 merged.

**Gate 2:** Sol re-runs the T0.1/T0.2 categorized sample and confirms the
procedure-resolution and parser-classification failure categories have
measurably shrunk; records the gate with the new counts.

## Phase 3 — Airways and Contextual Waypoints

- [ ] **T3.1 — Agent model: Terra.** Fix the airway-designation matching bug verified
  2026-08-17. `_airway_vertices` (`flightplan.py:166-225`) extracts a
  `designation` letter from the token text via the `_AIRWAY` regex (e.g.
  `Q822` → `designation="Q"`) and requires
  `record["AWY_DESIGNATION"] == designation`
  (`flightplan.py:179-185`, the `or` condition). But real `AWY_BASE` data
  does not use the token's leading letters as `AWY_DESIGNATION`: for
  `AWY_ID="Q822"` (a real RNAV airway), the actual `AWY_DESIGNATION` value
  is `"RN"`, not `"Q"` (verified against the `2024-06-13` cycle's
  `AWY_BASE.csv`; every `Q`/`T`-prefixed `AWY_ID` in that cycle has
  `AWY_DESIGNATION` of `AT` or `RN`, never the bare prefix letter). This
  means the `or` short-circuits on the designation mismatch alone and
  **every `Q`- and `T`-prefixed airway currently fails to resolve
  regardless of whether its waypoints are correct** — reproduced directly:
  `_airway_vertices(tables, "Q822", "FNT", <its real last TO_POINT>)`
  raises `RecordNotFoundError` even when `start`/`end` are read directly
  from `Q822`'s own `AWY_SEG_ALT` rows.
  `AWY_ID` alone is not a safe replacement without the existing
  `REGULATORY`/`AWY_LOCATION` disambiguation the code already applies
  downstream (verified: 53 of 1,483 `AWY_ID` values are duplicated across
  regions in the `2024-06-13` cycle, e.g. `V1`, `V11`, `T370`) — do not
  simply delete the designation check without confirming the downstream
  `REGULATORY`/`AWY_LOCATION` filter (already present at
  `flightplan.py:186-191`) still disambiguates correctly on its own.
  Fix: remove or correct the direct string-equality comparison between the
  regex-extracted letter prefix and `AWY_DESIGNATION`; rely on `AWY_ID`
  matching (already required by the `or` clause's second branch) combined
  with the existing per-candidate `REGULATORY`/`AWY_LOCATION` key, and let
  a genuine multi-region collision surface as the existing
  `AmbiguousRecordError` path (`flightplan.py:220-224`), not a silent
  `RecordNotFoundError`.
  Acceptance: a `Q`-prefixed and a `T`-prefixed real airway (or synthetic
  equivalents) both resolve correctly; a new test fails on current code and
  passes after the fix; existing airway tests
  (`test_flight_plan_path_expands_airways_and_resolves_airports`,
  `test_flight_plan_path_expands_an_airway_in_reverse`) still pass
  unchanged.
  Dependencies: none (independent of Phase 1/2's tokenizer changes; may
  proceed in parallel with Phase 2 once Phase 1 merges, per the
  coordination rules' file-sequencing note — confirm no open Phase 2 task
  is mid-edit on `_airway_vertices` before starting).
- [ ] **T3.2 — Agent model: Terra.** Resolve airway paths only between confirmed
  endpoint records and support both directions through the published
  sequence — already implemented
  (`flightplan.py:204-211`, verified by
  `test_flight_plan_path_expands_an_airway_in_reverse`); confirm coverage
  rather than re-implementing.
- [ ] **T3.3 — Agent model: Luna.** Clarify what "airway designation" means for this
  codebase before writing new classification logic: verified 2026-08-17
  that `AWY_DESIGNATION` values in the `2024-06-13` cycle are two-letter
  codes (`A, AT, B, BF, G, J, PA, PR, R, RN, V`), not literal `Q`/`T`/`V`
  single letters — those single letters are `AWY_ID` *prefixes*, not
  `AWY_DESIGNATION` values. Document this distinction in the module
  docstring or a code comment near `_AIRWAY` so a future contributor does
  not reintroduce T3.1's bug by re-deriving "designation" from the token
  text.
  Dependencies: T3.1.
- [ ] **T3.4 — Agent model: Terra.** Use context to disambiguate duplicate identifiers
  such as `ABQ`, `SEA`, `STL`, `PVD`: procedure/airway connection fields
  take priority, then fix/navaid, with airports preferred at route
  endpoints. This is the existing `preferred_tables` mechanism in
  `_waypoint`/`_WaypointResolver.resolve` (`flightplan.py:52-84`,
  `109-163`) — verify with
  `test_flight_plan_path_uses_route_position_to_disambiguate_waypoints`
  (`tests/test_flightplan.py:90`) and extend only if a specific real-route
  case is found not to be covered.
- [ ] **T3.5 — Agent model: Terra.** Prefer a non-`VOT` navaid when a bare `NAV_ID`
  collides within `NAV_BASE` itself. Verified 2026-08-17 against the
  `2024-06-13` cycle: `ICT` matches two distinct `NAV_BASE` rows
  (`NAV_TYPE=VORTAC` at one coordinate, `NAV_TYPE=VOT` at another), so
  route `KBBG..EOS..ICT..KHUT/0038` currently raises `AmbiguousRecordError`
  even though a VOT ("VOR test facility," a ground calibration signal) is
  never a valid filed route fix. This is a same-*table* collision inside
  `NAV_BASE`, distinct from the existing cross-table
  (`APT_BASE`/`FIX_BASE`/`NAV_BASE`) disambiguation `_WaypointResolver`
  already performs.
  Fix: in `_WaypointResolver`/`_waypoint`'s `NAV_BASE` candidate collection
  (`flightplan.py:33-50`, `102-106`), when multiple `NAV_BASE` rows share a
  `NAV_ID` and exactly one has a non-`VOT` `NAV_TYPE`, prefer it instead of
  passing all candidates through to the ambiguity check. If more than one
  non-`VOT` candidate remains, still raise `AmbiguousRecordError` as today.
  Acceptance: `KBBG..EOS..ICT..KHUT` resolves `ICT` to the `VORTAC`
  coordinates without raising; a new test fails on current code and passes
  after the fix; the existing
  `test_flight_plan_path_uses_route_position_to_disambiguate_waypoints`
  test (a genuine cross-table ambiguity) still passes unchanged.
  Dependencies: none (independent of T3.1's airway-table fix; touches
  `_WaypointResolver`/`_waypoint`, not `_airway_vertices`).
- [ ] **T3.6 — Agent model: Terra.** Validate that an airway endpoint exists on the
  selected airway and that every expanded intermediate identifier resolves
  to one unambiguous source coordinate — already implemented via
  `vertices.index(start)`/`vertices.index(end)`
  (`flightplan.py:204-208`, raising via the `not matches` check) and the
  per-vertex `_waypoint` call in `flight_plan_path`
  (`flightplan.py:476-483`); confirm coverage, do not re-implement.
  Dependencies: T3.1 (validate against the corrected designation logic).
- [ ] **T3.7 — Agent model: Luna.** Add regression tests for forward/reverse routes,
  repeated airway designations, airway transition joins, and intentionally
  ambiguous names. Include the `ICT`-style same-table `VOT`-versus-
  operational-navaid case (T3.5) and a `Q`/`T`-prefixed airway case (T3.1)
  as their own fixtures, not only cross-table duplicates.
  Dependencies: T3.1, T3.5.

**Gate 3:** Sol confirms T3.1 and T3.5 close their respective real-data
reproductions and records the gate. Re-run the T0.1/T0.2 sample; the
airway-resolution and waypoint-ambiguity failure categories should shrink.

## Phase 4 — Performance and Reuse

**T4.1 is not strictly gated behind Phase 1-3.** It touches only
`_WaypointResolver` construction, not matching/dispatch logic, and can
start once Phase 1 merges (so the tokenizer/dispatch base is stable)
without waiting for Gate 2 or Gate 3 — see the rationale in the 2026-08-17
Decision log entries. **T4.2 is different: it depends on T3.1**
(vectorizing `_airway_vertices`'s broken `AWY_DESIGNATION` comparison
before T3.1 fixes it would just make the wrong answer faster), so it
cannot start early the way T4.1 can. T4.3 depends on both T4.1 and T4.2 and
therefore inherits T4.2's gating.

**Measured severity (2026-08-17, real `2024-06-13` cycle, ~68k `FIX_BASE` +
~20k `APT_BASE` + ~1.8k `NAV_BASE` rows):** a single `flight_plan_path` call
took ~2.7 seconds end to end (table load ~0.4s, everything else essentially
all resolver construction — a standalone `_WaypointResolver` build measured
~2.8s on its own, matching within timing noise). `flight_plan_path` builds
one from scratch on every call (`flightplan.py:429`) by converting all
three tables to Python dicts row-by-row (`.to_dict(orient="records")`)
rather than reusing anything across calls. At that per-call cost, the full
46,580-row `tests/exampleRoutes.csv` would take on the order of 35 hours
sequentially.

- [ ] **T4.1 — Agent model: Terra.** Vectorize `_WaypointResolver.__init__`
  (`flightplan.py:33-50`); do not just cache the slow version. The ~2.8s
  cost is `.to_dict(orient="records")` plus a Python `for` loop
  materializing a dict per row across ~90k rows. Replace it with
  column-oriented pandas operations: for each `(table, columns)` pair in
  `_WAYPOINT_TABLES` (`flightplan.py:102-106`), drop rows with missing
  `LAT_DECIMAL`/`LONG_DECIMAL` via a vectorized mask, then build the
  identifier index by iterating `zip(frame[column], frame["LAT_DECIMAL"],
  frame["LONG_DECIMAL"])` (a column-array walk, not a per-row dict
  allocation) or a single `frame.groupby(column)` per identifier column.
  Verified directionally: a prototype vectorized mask-plus-`zip` walk over
  the real `FIX_BASE` table (68,122 rows, the largest of the three) ran in
  ~0.14s versus multiple seconds for the existing per-row loop.
  Acceptance: on the documented benchmark machine and canonical cycle, a
  standalone microbenchmark records at least a 10x improvement over the
  preserved baseline; report the absolute timing as diagnostic evidence, not
  as a portable CI threshold. All existing `_WaypointResolver`/`_waypoint`
  tests pass unchanged (same candidates, same ambiguity behavior, same dedup
  via `dict.fromkeys`).
  Dependencies: Phase 1 merged (stable tokenizer/dispatch base); may run in
  parallel with Phase 2/3 tasks that do not touch
  `_WaypointResolver`/`_waypoint` (confirm via the coordination rules
  before starting).
- [ ] **T4.2 — Agent model: Terra.** Vectorize `_airway_vertices`'s `AWY_BASE` lookup
  (`flightplan.py:178-185`) the same way: replace the
  `for record in base.to_dict(orient="records")` scan with a boolean-mask
  filter on `AWY_ID` (post-T3.1 fix; do not reintroduce the wrong
  `AWY_DESIGNATION` comparison here), matching the `.map(_text).eq(...)`
  pattern already used later in the same function
  (`flightplan.py:190-191`) and elsewhere in the codebase (e.g.
  `AirportRepository`). Then only convert the *matched* rows (typically one
  airway, a handful of rows) to records, not the full ~1,537-row table.
  This table is smaller than the waypoint tables but is rescanned once per
  airway token in a route, not once per call, so its relative cost grows
  with route complexity.
  Acceptance: a microbenchmark of `_airway_vertices` for a known airway
  token drops materially versus the current full-table scan; existing
  airway tests pass unchanged.
  Dependencies: T3.1 (fix the matching bug before vectorizing the same
  comparison — vectorizing a wrong comparison just makes it wrong faster).
- [ ] **T4.3 — Agent model: Terra.** Add an explicit route resolver/session object
  (e.g. `RouteResolver(nasr)` built once, `.path(flight_plan)` called per
  route) that caches T4.1/T4.2's vectorized structures, while preserving
  the existing one-call `flight_plan_path` function (T0.6) as a thin
  wrapper that builds a resolver internally for single-call convenience. If
  `RouteResolver` is a supported package-level API, export it from
  `openNASR/__init__.py` and document it; otherwise explicitly keep it as
  `openNASR.flightplan.RouteResolver` internal/advanced API.
  Prefer this explicit object over an implicit module-level or
  `NASR`-attached cache: a plain `functools.lru_cache` is not safe here
  since DataFrames are unhashable and mutable, and an explicit object makes
  the cache's lifetime and invalidation visible to the caller.
  Acceptance: repeated `RouteResolver.path(...)` calls against the same
  instance are measurably faster than repeated `flight_plan_path(...)`
  calls after the first; `flight_plan_path`'s public results and errors
  are byte-identical with and without the new object (same route in, same
  path/exception out).
  Dependencies: T4.1, T4.2.
- [ ] **T4.4 — Agent model: Luna.** Adopt and test the resolver snapshot policy: a
  `RouteResolver` indexes the supplied mapping at construction and callers
  must create a new resolver after mutating that mapping or any contained
  DataFrame. `NASR` is a mutable `dict` subclass, so do not describe it as
  immutable or promise automatic cache invalidation. Test CSV and DuckDB
  isolation by showing that a fresh `NASR`/fresh resolver does not share
  cached state across cycles, and document this lifetime rule in the API.
  Dependencies: T4.3.
- [ ] **T4.5 — Agent model: Luna.** Benchmark CSV and DuckDB storage with the same
  already-loaded tables, fixed routes, warm-up policy, sample count,
  median, and p95. The benchmark matrix must include direct
  airport-to-airport routing, fix/navaid routing, airway-only routing,
  DP-to-airway routing, airway-to-STAR routing, and a route containing both
  a DP and STAR. Report loading time separately from path resolution.
  Dependencies: T4.3.
- [ ] **T4.6 — Agent model: Luna.** For every procedure benchmark in T4.5, report the
  number of procedure legs and expanded path coordinates, the selected
  procedure/transition identifiers, and whether the timing is cold (first
  procedure-table materialization) or warm (all required procedure tables
  and indexes already loaded).
  Dependencies: T4.5.
- [ ] **T4.7 — Agent model: Sol.** Confirm no raw SQL API is introduced for route
  conversion (T4.1-T4.3 use pandas/DataFrame operations, not
  `openNASR.query`'s SQL surface) and that source-order fidelity is
  retained in DuckDB-backed reads — review, not new code.
  Dependencies: T4.1-T4.3.

**Gate 4:** Sol records the benchmark machine, Python/pandas/DuckDB versions,
canonical cycle, source backend, cold/warm policy, and before/after numbers
for `_WaypointResolver` construction and a representative `flight_plan_path`
call. T4.1 must meet its documented relative-improvement target.

## Phase 5 — Batch Validation and Diagnostics

- [ ] **T5.1 — Agent model: Luna.** Add a maintained validation command or test utility
  (e.g. `tools/route_path_validation.py`, matching the existing
  `tools/duckdb_benchmark.py` convention of a standalone, non-pytest
  script) that samples route rows deterministically by seed and records
  success/failure totals without modifying the input CSV.
  Dependencies: T4.3 (use `RouteResolver` so the utility is not itself
  bottlenecked by per-call resolver rebuilds — running this against
  hundreds of routes on unvectorized `flight_plan_path` would reintroduce
  the T0.5 performance problem this utility is meant to make practical to
  run).
- [ ] **T5.2 — Agent model: Terra.** Report failure type, token, token position,
  selected cycle, and route text in raised exceptions or the validation
  utility's output. Avoid printing entire candidate datasets in normal
  output (matches `AmbiguousRecordError`'s existing `candidates` field
  being available but not auto-printed).
  Dependencies: T1.3 (token positions), T5.1.
- [ ] **T5.3 — Agent model: Luna.** Run the T0.1 deterministic sample (or T0.3's fixed
  regression sample) after each phase gate and compare it to the baseline
  by category from T0.2.
  Dependencies: T5.1, each phase's gate.
- [ ] **T5.4 — Agent model: Luna.** Maintain a small, cycle-pinned procedure evaluation
  set containing a bare DP, dotted DP transition, bare STAR, dotted STAR
  transition, DP-to-airway, airway-to-STAR, and DP-to-airway-to-STAR route.
  Verify both the expected ordered procedure connection identifiers and
  non-empty lat/lon output before using these routes in T4.5/T4.6's
  performance measurements.
  Dependencies: T2.7 (reuses those fixtures where possible).
- [ ] **T5.5 — Agent model: Luna.** Add an opt-in full-file validation mode (an
  environment variable or CLI flag on T5.1's utility) suitable for CI
  artifacts or a local benchmark; do not make routine unit tests depend on
  the large, untracked `tests/exampleRoutes.csv` file (confirmed
  2026-08-17: this file is not committed to the repository).
  Dependencies: T5.1.

**Gate 5:** Sol confirms T5.1's utility runs the full sample in a practical
time (using T4's caching) and that its category breakdown matches manual
spot-checks from T0.2.

## Phase 6 — Explicit Non-Domestic and Oceanic Policy

- [ ] **T6.1 — Agent model: Terra.** Detect and label records outside domestic NASR
  coverage: foreign ICAO airports (verified 2026-08-17 against real route
  data: `EGLL`, `EIKY`, `EBLG`, `CYYZ`, `MMUN`, `TJSJ`, `RCTP` all appear in
  `tests/exampleRoutes.csv`), international airway/procedure identifiers
  (`UL207`, `UA758`, `RTE2`, `RTE6` observed), and coordinate fixes such as
  `4500N/05000W` (the format `DDDDN/DDDDDW`/`DDDDN/DDDDDE` — verified
  present in real route data, e.g. `2612N/09442W`).
  Acceptance: a route containing one of these raises a distinguishable
  typed error (see T0.8) rather than the generic `RecordNotFoundError`
  used for a genuinely-missing domestic record, or is otherwise reported
  separately per T0.4's denominator policy.
  Dependencies: T0.8 (error-type decision).
- [ ] **T6.2 — Agent model: Sol.** Decide whether coordinate fixes should be parsed
  locally into latitude/longitude (the format is a fixed, parseable
  pattern with no NASR lookup required) while still treating their
  connecting non-NASR route structure (foreign airways/procedures around
  them) as unsupported. Record the decision in the Decision log either way.
- [ ] **T6.3 — Agent model: Terra.** If T6.2 decides to parse coordinate fixes locally,
  implement the `DDDDN/DDDDDW`-style parser as a small, self-contained
  addition to `flightplan.py` (not a new module) and wire it into
  `_waypoint`'s dispatch as a fallback only after normal table lookup
  fails, so it never shadows a real NASR fix/navaid that happens to share
  the pattern.
  Dependencies: T6.2 (only if T6.2 decides to implement it).
- [ ] **T6.4 — Agent model: Sol.** Evaluate optional data providers for international
  aeronautical data; require a source license, cycle/effective-date,
  provenance, and cache policy before adding one. This is explicitly a
  future/opt-in evaluation, not a task to implement in this plan's release
  (see Release Gates).
- [ ] **T6.5 — Agent model: Terra.** Keep this expansion opt-in so the domestic
  NASR-only contract remains deterministic and offline-capable — no
  network access or external provider call may be introduced by T6.1/T6.3.

**Gate 6 (optional, does not block the Phase 1-5 release):** Sol confirms
T6.1's detection correctly separates domestic-failure routes from
genuinely-international routes in the T0.1 sample, and that T0.4's reported
denominator is accurate.

## Release Gates

- [ ] Full unit suite passes for CSV and DuckDB storage.
- [ ] New procedure, airway, ambiguity, and parser regression tests pass
  (T1.5, T2.7, T3.7, T4.4).
- [ ] The deterministic validation sample (T5.3) improves without
  increasing known domestic-parser regressions, measured against T0.1/T0.2.
- [ ] Documentation (T0.7) states the selected-cycle requirement, supported
  syntax, external/oceanic limitations, and non-operational-use disclaimer.
- [ ] Record benchmark environment, cycle, storage backend, and warm/cold
  timings (T4.5, T4.6) in the release notes or benchmark artifact.
- [ ] Phases 1-5 gates are recorded in the Decision log. Phase 6 (Gate 6)
  is explicitly optional for this release per its own scope note.

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
| 2026-08-17 | Use one cycle-pinned, hash-identified 100-route sample as the phase-gate baseline; retain other cycle samples as diagnostic evidence only. | A change in FAA cycle can legitimately change procedures, fixes, and airway data, so counts from 2024 and 2026 cannot demonstrate an implementation improvement unless the sampled inputs and selected cycle are held constant. |
| 2026-08-17 | Give `RouteResolver` snapshot semantics and use a relative benchmark target. | `NASR` and pandas DataFrames are mutable, so implicit cache invalidation would be ambiguous and costly. Absolute timing thresholds also vary by hardware; a recorded environment plus before/after ratio gives a reproducible performance gate. |
| 2026-08-17 | Restructure the entire plan into numbered tasks (`T0.x`-`T6.x`) with an assigned agent role, explicit dependencies, and a per-task acceptance test, reusing the Sol/Terra/Luna roster and coordination-rules convention from `DUCKDB_PLAN.md`; fact-check the previously-unreviewed Phase 3/5/6 bullets against real code and data during the restructure rather than only reformatting the existing prose. | The plan's four already-verified findings (bare-procedure misclassification, greedy dot-merge, `VOT` disambiguation, resolver vectorization) were implementable by a cold subagent, but most of the original bullets were outcome statements ("resolve a bare departure name") with no task boundary, acceptance criterion, or file-ownership guidance — two subagents assigned different Phase 2 bullets would likely collide on the same functions in `flightplan.py` with no sequencing rule to prevent it. |
| 2026-08-17 | Fix `_airway_vertices`'s `AWY_DESIGNATION` comparison (T3.1): stop comparing the token's regex-extracted letter prefix against `AWY_DESIGNATION`; rely on `AWY_ID` matching plus the existing `REGULATORY`/`AWY_LOCATION` disambiguation instead. | Verified against the real `2024-06-13` cycle that `AWY_DESIGNATION` values (`A, AT, B, BF, G, J, PA, PR, R, RN, V`) are not the token's leading letters — every real `Q`/`T`-prefixed `AWY_ID` (e.g. `Q822`, a genuine RNAV airway) has `AWY_DESIGNATION` of `AT` or `RN`, never `"Q"` or `"T"` — so the current `or`-joined check silently rejects every `Q`/`T`-prefixed airway regardless of whether its waypoints are correct, reproduced directly against `Q822`'s own segment data. `AWY_ID` alone is not fully unique (53 of 1,483 values in this cycle are duplicated across regions), so the existing downstream `REGULATORY`/`AWY_LOCATION` filter must be confirmed to still disambiguate correctly, not simply dropped alongside the wrong comparison. |
