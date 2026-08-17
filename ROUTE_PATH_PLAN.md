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
- [ ] Categorize each failure as a parser error, procedure-resolution error,
  airway-resolution error, waypoint ambiguity, missing NASR data, or malformed
  input. Retain at least one representative route for every category.
- [ ] Add a non-flaky regression sample covering each supported route form.
- [ ] Set and document a domestic-only success target after the sample is
  classified. Exclude rows requiring non-NASR international/oceanic data from
  the domestic coverage denominator, but report them separately.
- [ ] Benchmark cold and warm conversion separately. A warm benchmark must
  measure path generation only after the NASR tables and resolver indexes are
  ready.

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
- [ ] Resolve `PROCEDURE.TRANSITION` forms such as `ORCO8.TRM` and
  `TORGY4.SSWAN` using the FAA procedure tables.
- [ ] Use neighboring route tokens to choose the applicable procedure
  transition or runway/common portion. If more than one published candidate
  remains, raise a typed ambiguity instead of selecting arbitrarily.
- [ ] Support routes that combine a DP, direct segment, airway, fix/navaid,
  and STAR; deduplicate only adjacent identical coordinates at joins.
- [ ] Test a current-cycle valid route for each of: bare DP, dotted DP,
  bare STAR, dotted STAR, DP-to-airway, airway-to-STAR, and procedure-only
  airport pairs.

## Phase 3 — Airways and Contextual Waypoints

- [ ] Resolve airway paths only between confirmed endpoint records and support
  both directions through the published sequence.
- [ ] Correctly distinguish high/low/Q/T/other FAA airway designations from
  arbitrary alphanumeric tokens.
- [ ] Use context to disambiguate duplicate identifiers such as `ABQ`, `SEA`,
  `STL`, and `PVD`: procedure/airway connection fields take priority, then
  fix/navaid, with airports preferred at route endpoints.
- [ ] Validate that an airway endpoint exists on the selected airway and that
  every expanded intermediate identifier resolves to one unambiguous source
  coordinate.
- [ ] Add regression tests for forward/reverse routes, repeated airway
  designations, airway transition joins, and intentionally ambiguous names.

## Phase 4 — Performance and Reuse

- [ ] Build the airport/fix/navaid candidate index once per immutable NASR
  dataset instead of rebuilding it for every `flight_plan_path` call.
- [ ] Keep public results and errors identical with and without the cache;
  add mutation/isolation tests for CSV and DuckDB storage.
- [ ] Add an optional route resolver/session object for batch conversion while
  preserving the existing one-call function.
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
