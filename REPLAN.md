# openNASR replan

Status: **decisions complete; ready to start Phase 0**. Supersedes the scope of the plans now in `docs/archive/` (`PLAN.md`, `DUCKDB_PLAN.md`,
`SPEEDUP.md` and `ROUTE_PATH_PLAN.md` once accepted (those become archive).

## 1. Goal

Three components, one product:

| # | Component | Job |
|---|-----------|-----|
| A | **Archiver** | Every 28-day cycle, download the FAA NASR subscription and keep it in S3 forever. |
| B | **API service** | Query NASR data over HTTP. Headline feature: *flight plan string in, ordered lat/lon sequence out.* |
| C | **Local mode** | The same service logic, run in-process from Python (and a local server) with no S3 or network. |

The rule that keeps these honest: **B and C are the same code.** The HTTP layer is a thin
shell over a Python core. If a query works in C it works in B, and the reverse.

## 2. Where the code is today

- Library, CSV backend plus optional DuckDB backend, typed repositories, CLI
  (`opennasr`), local cycle cache with checksums (`cycles.py`).
- `flightplan.py` (1.4k lines) already resolves a route string to a coordinate path
  (`RouteResolver.path`, `flight_plan_path`), including SIDs/STARs and airways.
- **Missing:** S3 archive, scheduler, any HTTP API, versioned API contract, coverage
  measurement of route resolution.
- Cost today: two storage backends (CSV and DuckDB) and large plan documents; the
  route resolver's correctness is asserted by unit tests but not measured against
  reality.

## 3. Architecture

```
FAA NASR site ──(A) archiver──▶ S3: <year>/<cycle>_<sha256>.zip   (immutable)
                                   │
                          cycle build (per cycle, once)
                                   ▼
                       cycle index  (DuckDB file, read-only, per cycle)
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
     (C) openNASR core (Python)  ◀── same code ──  (B) FastAPI shell
         NASR / RouteResolver                          /v1/...
```

Decisions proposed:

1. **One storage backend for serving: DuckDB, built once per cycle.** CSV stays only as
   the import format. Dropping the dual path removes the "parity" test burden
   (`test_duckdb_repository_parity` etc.) and the main source of complexity. *Open
   question 1.*
2. **Cycles are immutable.** A cycle index is built from the archived zip, checksummed,
   and never edited. The API serves any cycle by effective date, default = the one
   effective today. This gives "what was the route on date X" for free.
3. **Core has no I/O assumptions.** It takes a cycle index handle. Archiver and API
   both depend on core; core depends on neither.
4. **Own project, no ties to WhoDatJet.** Nothing is imported from or shared with it.
   Good operating practices (immutable keys, outage staging, de-duplicated alerts,
   signed releases) are re-implemented here as needed, not depended on.
5. **Store the derived DuckDB files in S3 too** (decided). The zip is the source of
   truth; a DuckDB file is a rebuildable product. See section 4.

### Repository shape: a super project with subprojects

Each subproject has its own package, tests, version, and container image. They share
**no runtime state**; the only interface between the archiver and the API is the S3
bucket contract (keys + manifest schema).

```
openNASR/
  core/       openNASR-core   library: schemas, DuckDB access, route resolver   (no I/O policy)
  archiver/   openNASR-archiver   download, build DuckDB, validate, publish to S3   -> container 1
  api/        openNASR-api        FastAPI service, fetches validated builds from S3 -> container 2
  contract/   bucket key layout + manifest JSON schema (the only coupling)
  docs/  tests/integration/
```

- `archiver` and `api` depend on `core`, never on each other.
- Each deploys independently as its own LXC or Docker container, own env file, own
  health endpoint. The archiver has no inbound port; the API has no write access to S3.
- Local mode (component C) is `core` plus a thin CLI/server, installable alone.
- Separate packages per subproject (decided, question 5).

## 4. Component A: archiver

Decided: the archiver also builds the DuckDB file, validates it, and stores both zip and
DuckDB in S3 (zip = source of truth; DuckDB = rebuildable, keyed by builder version, with
a manifest uploaded last as the "validated" marker).


- Daily timer (cheap check; FAA publishes every 28 days, so most runs are no-ops).
- Discover the current and upcoming cycle from the FAA subscription page
  (`cycles.py` provider already does this).
- Download, validate zip, compute SHA-256, upload to S3 as
  `<year>/<effective-date>_<sha256>.zip`. Skip if the same hash exists.
- **Keep the upcoming cycle too**: FAA posts it ~20 days early, which lets the API
  pre-build the next index before it takes effect.
- S3 down: stage locally, retry, alert once, resolve once.
- Failure alerts: no new cycle within N days of expected effective date.
- Backfill command for historical cycles (FAA archive availability: *verify*).

Acceptance: a fresh machine with only S3 credentials can rebuild every index.

### DuckDB version selection (installer requirement)

DuckDB 2.0.0 crashes ("Illegal instruction") on CPUs without AVX2 (found on the devbox
Xeon E5-2620); 1.x runs. Therefore:

- Installers and updaters **probe, not guess**: in a throwaway venv, try DuckDB `2.x`,
  then `1.4.x`, then `1.3.x`; run `connect().execute('select 1')` in a subprocess; keep the
  first that works. If none works, stop with a clear error.
- The chosen version is recorded in the container's state file; the updater re-probes.
  Optional `--duckdb-version` forces a version (non-interactive installs).
- **Fleet rule:** the archiver builds with the oldest DuckDB any reader can run. The
  manifest records the builder's DuckDB version. The API checks it can open a new build
  before switching; otherwise it keeps serving the previous cycle and alerts.
- Until installers exist, `pyproject.toml` caps the optional dependency at `<2`.

## 5. Component B: API service

Read-only, API-key protected, versioned under `/v1`.

**Headline endpoint**

```
POST /v1/route/resolve        (GET with ?route= also allowed)
{ "route": "KLAX DOTSS2 ... J74 ... KDFW", "cycle": "2026-11-12" (optional) }
→ {
    "cycle": "2026-11-12",
    "points": [ {"lat": 33.94, "lon": -118.41, "name": "KLAX", "kind": "airport",
                 "via": null, "segment": "origin"}, ... ],
    "geojson": { "type": "LineString", ... },
    "diagnostics": [ {"token": "XYZ", "code": "UNRESOLVED_TOKEN", "detail": "..."} ],
    "complete": true
  }
```

Key design points for the headline feature:

- **Return provenance per point** (which token and which procedure/airway produced it),
  so callers can trust or debug a path.
- **Partial results are normal.** Unknown token, unsupported content, or ambiguous
  procedure returns what could be resolved plus structured `diagnostics`, with
  `complete: false`. Never a bare 500.
- **Deterministic.** Same route and cycle always give the same output; cycle is echoed.
- Densify option (`?max_segment_nm=`) for great-circle interpolation between fixes, as
  an opt-in, so default output stays "the published points only".

**Input modes** (all return the same response shape):
- `route`: a route string.
- `icao_message`: a full ICAO flight-plan message; the API extracts the route field and
  the departure/destination airports, and reports what it extracted so callers can check.
- Lat/lon waypoints (`4530N07330W`, `45N073W`) are parsed directly; speed/altitude
  groups (`N0450F350`, `FIX/N0450F350`) are skipped and echoed in diagnostics as ignored.

**Supporting endpoints** (thin wrappers over existing repositories):
`/v1/airports/{id}`, `/fixes/{id}`, `/navaids/{id}`, `/airways/{id}`,
`/airspace/at?lat=&lon=`, `/cycles`, `/health`, `/ready`.

Non-goals: write APIs, user accounts, a UI, weather/NOTAM.

## 6. Component C: local mode

- `from openNASR import NASR` keeps working (library compatibility).
- `opennasr serve` runs the same FastAPI app locally against the local cache.
- `opennasr route "KLAX ... KDFW"` prints points/GeoJSON.
- Local mode uses the same cycle cache; `opennasr fetch` pulls from S3 (or FAA directly
  when no S3 is configured).

## 7. Route resolution: fidelity and coverage

Flight plan to lat/lon is a deterministic expansion of NASR data. Flown tracks, wind,
performance and trajectory prediction are **out of scope**. Comparing or studying
differences between plans is a later, separate project.

Success means:

1. **Deterministic.** Same route string and cycle give byte-identical output.
2. **Faithful to NASR.** Every point comes from a NASR record (fix, navaid, airport,
   airway segment, procedure leg), with its source recorded.
3. **Honest about gaps.** An unsupported or ambiguous construct produces a diagnostic and
   `complete: false`, never a guessed point.
4. **Cycle-aware.** The cycle used is part of the result, so a changed plan or changed
   data is detectable.

Plan:

1. **Corpus**: real route strings (filed, preferred routes, coded departure routes from
   NASR) with expected point sequences, checked in and run in CI. This is a regression
   guard, not a claim about flown tracks.
2. **Coverage table**: each construct marked supported / diagnostic-only / unsupported.
   Launch scope is fixed (question 4b). Constructs: airport/fix/navaid tokens, airways (`J74`), `DCT`, SID/STAR names with
   and without transitions, dotted procedure forms, lat/lon waypoints, ICAO-format
   speed/level groups (`N0450F350`), oceanic tracks.
3. Report the resolution rate per cycle in CI.
4. Split `flightplan.py` into tokenizer / resolver / procedure expander / airway
   expander so each can be tested alone.

## 8. Phases

| Phase | Outcome | Exit criterion |
|-------|---------|----------------|
| 0 | Housekeeping | `python -m pytest` and `pytest` both green; download timeout and size limits fixed; plan docs archived to `docs/archive/` |
| 1 | Core consolidation | Single DuckDB serving backend; CSV only for import; parity tests removed; public API unchanged |
| 2 | Route corpus + metrics | Corpus checked in; resolution rate reported in CI |
| 3 | Archiver | Timer-driven download to S3, immutable keys, outage staging, alerts; fresh-machine rebuild works |
| 4 | API v1 | `/v1/route/resolve` + supporting endpoints, API keys, OpenAPI published, contract tests |
| 5 | Local mode polish | `serve`, `route` CLI, docs, same contract tests run against both modes |
| 6 | Deploy | Per-subproject container images (LXC or Docker), signed releases, reverse proxy, monitoring; installer probes for a working DuckDB version |
| 7 | Observation | A week of cycle checks, checksum and index verification, then go live |

Phases 2 and 3 are independent and can run in parallel.

## 8a. Phase 1 task breakdown (DuckDB-only core)

Finding: the `NASR` facade still needs the extracted CSV folder even in DuckDB mode, for
(a) schema identification (`SchemaCatalog.identify_schema`), (b) the source fingerprint,
(c) table discovery, and (d) CSV fallbacks in `query.py`. An API container that holds only
a `.duckdb` file must not need any of these.

| Task | Change | Acceptance |
|------|--------|------------|
| 1.1 | Builder records `schema_id` in the sidecar (optional field, older sidecars still read) | **done**: tests for present/absent |
| 1.2 | `NASR` opens from `.duckdb` + sidecar alone: schema id and table list come from metadata, columns from DuckDB; no CSV folder or archive needed | **done**: `test_artifact_alone_is_enough_to_serve_a_cycle` |
| 1.3 | Cycle lookup works from DuckDB artifacts alone (`CycleManager.get/latest`) | **done**: `CycleManager.ensure_duckdb` serves artifact-only cycles |
| 1.4 | Default and only storage is DuckDB; first use builds from archive/CSV if missing (shim); `storage="csv"` raises a clear migration error | **done**: `storage="csv"` raises a migration error |
| 1.5 | Remove CSV serving code: `TableRepository` use in `NASR`, `_query_csv_frame`, CSV branches in `query.py`, CLI `--storage` | **done** (CLI `list --storage` kept: it lists artifacts) |
| 1.6 | Drop CSV/DuckDB parity tests; test fixtures build a DuckDB once per session | **done**: fixtures cached per session; suite ~40 s |
| 1.7 | `duckdb` becomes a required dependency (capped `<2` until installer probe exists); README, MIGRATION, CHANGELOG updated | **done**: fresh venv installs duckdb 1.x; 412 tests pass |

## 9. Decisions log (all six resolved)

1. ~~Drop the CSV serving path?~~ **Decided: DuckDB only.** CSV is only the import
   format. The archiver builds, validates and stores DuckDB files in S3 next to the zips.
   Check first that DuckDB runs on the target host (it crashes on the devbox CPU).
2. ~~Where does the archiver live?~~ **Decided:** a subproject of this super project;
   unrelated to WhoDatJet.
3. ~~Who calls the API?~~ **Decided:** tailnet-only to start. Tailscale controls network
   access; API keys remain as a second layer (per-caller, revocable). Public exposure is a
   later, separate decision that adds rate limits, request-size limits and a public host.
4. ~~Is route accuracy "good enough for display" or "for analysis"?~~ **Decided: the
   question was mis-framed.** A flight plan is deterministic and maps directly to
   lat/lon. How an aircraft *flies* it is out of scope. The requirement is therefore
   fidelity, not accuracy: expand the plan exactly as NASR defines it, give the same
   answer every time, and say so explicitly when a construct is not supported. What
   remains is *coverage* (question 4b).
   - 4b. **Decided:** launch scope = core constructs **plus** lat/lon waypoints, speed/
     altitude groups (skipped, not geometry), and full ICAO flight-plan messages
     (route + departure/destination extracted). Oceanic tracks and other non-NASR
     constructs return a diagnostic. See section 7.
5. ~~Versioning/packaging~~ **Decided: option A.** Release **openNASR 2.0** (the CSV
   removal is a breaking change, so the major bump is honest). `core` keeps the PyPI name
   and import `openNASR`; `openNASR-archiver` and `openNASR-api` are separate packages with
   independent versions and containers. 1.x gets security fixes only, then ends.
6. ~~License~~ **Decided:** keep GPL-3.0-only for now; revisit if/when the project goes public.

## 8b. Phase 2 progress

| Task | Status |
|------|--------|
| 2.1 Corpus format and runner (`tools/route_corpus.py`, inline tables, exact point expectations) | done |
| 2.2 Synthetic corpus in CI with resolution-rate report (`tests/fixtures/route_corpus/synthetic.json`) | done |
| 2.3 Coverage table per construct (`docs/route-coverage.md`) | done |
| 2.4 Real-cycle corpus from `benchmarks/data/example_routes.csv` once a real cycle is cached | open |
| 2.5 ICAO lat/lon waypoint tokens (`3800N07730W`, `37S078E`) resolve with range checks; FAA slash form (`4300N/05000W`) stays a diagnostic | done |
| 2.7 Narrow DP/STAR records and bodies by the route's end airports (`STAR_APT`/`DP_APT`): done, resolved 15,987 -> 16,666 (+679). Runway-dependent bodies (`GRNCH-BRICE` vs `GRNCH-YAGGO` at MCO) are expected: the resolver returns the portion all bodies share (decided with the owner: arrivals branch by runway and airport configuration). Phase 4 must surface this as a diagnostic with `complete:false`; today `RouteResolver.path` returns the shared part silently | done |
| 2.8 **DP/STAR rows are stored in flight order; the resolver reversed them.** Verified over a full cycle (airport at first point of 1,021/1,026 DP bodies, last point of 1,179/1,186 STAR bodies). Fixed, fixtures rewritten | done |
| 2.6 Split `flightplan.py` into tokenizer / resolver / procedure and airway expanders | open |

### Real-cycle baseline (2.4, cycle 2026-10-29, 46,580-route pool, 20 s DuckDB build, schema_id `nasr_2026_09`)

| Outcome | Routes | Share |
|---------|--------|-------|
| Resolved | 15,987 | 34% |
| DP/STAR matched several records | 18,603 | 40% |
| Missing NASR data (unknown fix/procedure/airport) | 6,293 | 14% |
| Unsupported content (foreign airports, oceanic, external routes) | 5,632 | 12% |

Phase 1 caused none of this: a 400-route sample gave identical per-route results on `main` (CSV) and
this branch (DuckDB). The largest failure class is a pre-existing resolver weakness: a procedure
name such as `VIEWS.DEHAN3` is shared by several airports' records and the resolver does not use
the route's own origin/destination airport to choose. New task **2.7**: disambiguate DP/STAR
records by the route's airports. Pool routes predate this cycle, so some "missing" are retired names.

### Pool result after 2.7 and 2.8 (cycle 2026-10-29)

| Outcome | Routes | Share |
|---------|--------|-------|
| Resolved | 31,216 | 67% |
| Missing NASR data | 9,044 | 19% |
| Unsupported (foreign airports, oceanic, external) | 5,632 | 12% |
| Still ambiguous | 688 | 1.5% |

Missing is dominated by names that are not in this cycle: retired procedure versions
(`CHSLY7` is now `CHSLY9`), `U.S. CANADIAN BORDER-n`, and airports absent from the FAA file
(`PBI` is not in this cycle's APT_BASE; the build kept all 19,434 source rows). The pool predates this
cycle, so a fair rate needs routes filed for the cycle under test. **Open:** the silent partial
path (see 2.7), and a pool of current-cycle routes.

### 2.9 Procedure order is declared per schema (decided with the owner)

The FAA's DP and STAR DATA LAYOUT documents (in every download) say points are "in order adapted
for given Segment" and `NEXT_POINT` "directly follows the current Point": flight order. That is
prose in a PDF, so the convention is declared once per supported schema
(`SchemaCatalog.PROCEDURE_ORDER`), recorded in the sidecar as `procedure_order`, exposed as
`NASR.procedure_order`, and enforced by `RouteResolver`. The FAA announces format changes, and a new
schema must be added to the catalog by a person, who declares its convention then. An earlier
per-cycle measurement of every DP/STAR was removed as redundant.

### 2.10 Structured result (done)

`RouteResolver.resolve()` -> `RouteResult(route, cycle, points, diagnostics, complete)`; the phase 4
API serializes it. Codes so far: `procedure_branches` (partial, with `split_after` and `branches`),
the typed error names (`RecordNotFoundError`, `AmbiguousRecordError`, `UnsupportedRouteContentError`,
...) and `MalformedRoute`. Still to add for the API: per-point provenance and GeoJSON.

### Pool result after 2.11 and 2.12 (cycle 2026-10-29)

| Outcome | Routes | Share |
|---------|--------|-------|
| Resolved | 31,566 | 68% |
| Missing NASR data | 9,119 | 20% |
| Unsupported (foreign airports, oceanic, external) | 5,632 | 12% |
| Still ambiguous | 263 | 0.6% |

- **2.11** Departures that publish transitions but no body rows (radar-vector, e.g. `LARGO3`) now resolve from the transition: ambiguity 688 -> 263.
- **2.12** Fan markers that share a navaid's name (`MCK`, `AST`) are not route-point candidates. Run after the figures above, so it adds roughly 65 more resolved routes (not yet re-measured).
- Remaining ambiguity is genuine (`ZFP`: an NDB and a VOR/DME with one identifier). Remaining "airway" misses are mostly foreign-FIR airways (`J5` out of CYVR).

### Pool result with honest outcome classes (cycle 2026-10-29, 46,580 routes)

The earlier "failure" wording was wrong. The report (`tools/route_path_validation.py`) now classifies:

| Outcome | Routes | Meaning |
|---------|--------|---------|
| resolved | 18,040 | every part resolved exactly |
| resolved_with_branches | 14,814 | resolved; a procedure's runway/configuration-dependent branches are reported as a `procedure_branches` diagnostic and only the shared portion is included |
| **usable** | **32,854 (70.5%)** | the two rows above |
| not_in_cycle | 8,023 | a fix, airway, procedure or airport that is not in this cycle (pool filed against older cycles; foreign points) |
| outside_scope | 5,632 | foreign airports, oceanic coordinates, external routes |
| ambiguous | 68 | one identifier names two records and the route does not decide (`ZFP`: NDB and VOR/DME) |
| internal_error | 3 -> 0 | resolver bugs (empty procedure bodies); fixed after this run |

Runway-dependent branching (departures such as `MONTN2.SEA`, `CONLE5.SCOOB`; arrivals such as
`GRNCH5`) is expected FAA data, not an error. Open: a dotted departure with no published points
(`SLC4.TCH`, `LAKES5.MCI`) starts the following airway from the whole token instead of its exit
fix, so those routes report `RecordNotFoundError`.

### 2.13 Departures with no published geometry (done)

117 of 1,189 DPs have no `DP_RTE` rows (radar-vector SIDs), and others have transitions but no body. The code's
suffix (`SLC4.TCH`) is the DP's terminal fix in ~90% of the DPs that do publish geometry, so it is used and an
`info` diagnostic (`procedure_geometry_unpublished`) records the source. Info diagnostics do not make a route
incomplete. Pool: 32,857 usable (70.5%), 0 internal errors.

## 8c. Phase 3 progress (archiver)

| Task | Status |
|------|--------|
| 3.1 `contract/` package: key layout (`<year>/<date>_<zipsha>.zip`, `.b<N>.duckdb`, `.b<N>.json`) and strict manifest parse/serialize | done |
| 3.2 `archiver/` package: `Bucket` protocol, `LocalBucket` (immutable keys), `publish_cycle` with gates (recognised schema, supported procedure order, required tables non-empty, read-only smoke test), zip -> db -> manifest-last | done |
| 3.3 `S3Bucket` (boto3, optional `s3` extra; sha256 kept as object metadata; tested against a fake client, **not yet against a real bucket**) | done |
| 3.4 `run_once`: discover -> download -> publish (current cycle). Upcoming cycle and backfill need provider support (the provider only offers the current cycle) | partly done |
| 3.5 Outage staging (the local cache), de-duplicated alerts persisted in a state file (fail once, resolve once), "no new cycle" alert after 28 + 3 days | done (notifier is log-only so far) |
| 3.6 CLI + systemd timer + container image | open |
| 3.7 Fresh-machine rebuild test (acceptance) | open |

Repo layout so far: the existing `openNASR/` package at the root is `core`; `contract/` and `archiver/`
sit beside it. Moving core into `core/` is deferred until the API package exists, to keep history readable.
