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

## 2. Starting point before the replan

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
4. Split route resolution into separate layers behind the `flightplan.py` facade.
   Done, including separate modules for procedure indexing and expansion.
   Extracting the procedure index produced byte-identical serialized results
   for all 9,316 sampled routes (every fifth route in the pool, cycle
   2026-10-29). The sample had 3,580 fully resolved routes and 2,978 resolved
   with procedure branches before and after the extraction.

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
| 7 | Observation | Observe the scheduled archiver, confirm the API cycle rollover, and verify the next publication in Garage |

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
3. ~~Who calls the API?~~ **Decided:** tailnet-only access through NPMplus. The API
   supports revocable per-caller keys, and the owner chose explicit no-key mode
   for the current deployment. Public exposure would require a separate decision.
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
| 2.6 Split `flightplan.py` into layered modules (`_route_common`, `_route_waypoints`, `_route_airways`, `_route_procedures`, `_route_tokenizer`, `_route_resolver`; `flightplan.py` stays the import point). Verified identical on 9,316 real routes (coordinates, diagnostics, completeness) | done |

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
| 3.3 `S3Bucket` (boto3, optional `s3` extra; sha256 kept as object metadata; `S3Bucket.from_env` reads `OPENNASR_*`; verified against the real Garage server on 2026-11-16) | done |
| 3.4 `run_once`: discover -> download -> publish the current cycle, then best-effort the upcoming one (not posted yet = silent; build failure = one alert). `FaaCycleProvider.for_date` fetches any named cycle; `backfill` publishes a range of the 28-day grid, skipping what the bucket already holds | done |
| 3.5 Outage staging (the local cache), de-duplicated alerts persisted in a state file (fail once, resolve once), "no new cycle" alert after 28 + 3 days | done (notifier is log-only so far) |
| 3.6 CLI (`run`, `status`, `publish`, `rebuild`), webhook alerts, systemd service and timer, Dockerfile, README. The service and timer are deployed on LXC 124. CI builds the Docker image and publishes a synthetic cycle from it. | done |
| 3.7 Fresh-machine test: a cache holding only the fetched `nasr.duckdb` + sidecar opens and resolves routes (synthetic test, and the real 2026-10-29 cycle). `openNASR-archiver rebuild` recreates the database from only the zip in the bucket and compares tables, schema and fingerprint: verified against Garage with the real cycle | done |

Repo layout so far: the existing `openNASR/` package at the root is `core`; `contract/` and `archiver/`
sit beside it. Moving core into `core/` remains deferred.

The bucket clients (`Bucket`, `LocalBucket`, `S3Bucket`) and the reader side (`list_builds`, `select_build`,
`fetch_build`) live in `contract/` so the API can read a bucket without depending on the archiver. The manifest
carries a `sidecar` reference; a reader verifies the database hash against the manifest before installing.
Real cycle: zip 259 MB, DuckDB 55 MB. The build used DuckDB 1.5.6, which is pinned
on both live guests. The archiver should build with the oldest DuckDB version
used by a fleet reader.

### Storage (Garage at s3.xds-lab.com, created 2026-11-16)

Bucket `opennasr` on the Garage S3 store (path-style, region `garage`, Tailscale clients only). Two keys, in the
gitignored `.env`: `opennasr-archiver` (read + write) and `opennasr-api` (read only). Verified live: archiver write and
API read work, the API key is refused a write (`AccessDenied`), overwriting a key is refused by the client, and the real
2026-10-29 cycle published (zip, database, sidecar, manifest) and fetched back into an empty cache with the API key,
resolving a route. Neither key can create buckets.

### Backfill (2026-11-16)

`openNASR-archiver backfill --from 2026-09-03` published every cycle on the new FAA schema (`nasr_2026_09`,
first effective 2026-09-03): 2026-09-03, 2026-10-01, 2026-10-29 and the upcoming 2026-11-26 (the FAA had posted it).
All four are `flight_order`; zips 251-259 MB, databases 54 MB. **Decision (owner): backfill the current format only; no older cycles.** The daily `run` keeps adding each new cycle as the FAA posts it.
Slack alerts use the infrastructure repo's webhook, stored as `OPENNASR_ALERT_WEBHOOK_URL` in the gitignored `.env`
(one test message delivered, HTTP 200).

Operational note: an extracted cycle needs ~1.4 GB. `/tmp` on the devbox is a 7.9 GB RAM-backed tmpfs and filled up during
testing (builds then failed with "No space left on device"); caches must live on disk (`/home/aev/.cache/...`,
`/var/lib/openNASR-archiver`). Re-posted preview zips get new keys (the key holds the zip hash); readers pick the newest.

## 8d. Phase 4 progress (API)

| Task | Status |
|------|--------|
| 4.1 Per-point provenance in core: `RouteResult.waypoints` (name, kind, via, segment) | done |
| 4.2 `api/` package: `CycleStore` (fetches verified builds with the read-only key, serves from disk, a failed refresh never drops a working cycle, only the 11 route tables are loaded, LRU of loaded cycles), FastAPI app, `X-API-Key`/Bearer auth with constant-time compare | done |
| 4.3 `POST/GET /v1/route/resolve` (points, GeoJSON LineString in lon/lat, structured diagnostics, `complete`, cycle echoed), `/v1/cycles`, `/health`, `/ready`; unresolved routes are a 200 with diagnostics, bad input 422, unknown cycle 404, no cycle 503 | done |
| 4.4 Real-data check: server against Garage, `KABQ.DOOKK3.TXO..KTYR` complete with provenance; `GRNCH5` returns the branch warning; ~40 ms per request warm, 2.5 s first load of a cycle, ~330 MB per loaded cycle | done |
| 4.5 `icao_message` input mode: `parse_icao_flight_plan` (FPL fields 7, 13, 15, 16; opening speed/level dropped), `RouteResolver.resolve_icao_message`, API accepts exactly one of `route` / `icao_message`, response `input` echoes the extraction; non-FPL or malformed messages are a 422 with the reason | done |
| 4.6 Ignored speed/level/time groups (`FIX/N0450F350`, `KMSP/0354`, standalone `N0450F350`) echoed as `ignored_speed_level` info diagnostics (do not affect `complete`) | done |
| 4.7 Supporting endpoints `/v1/airports/{id}` (FAA or ICAO id, with runways and runway ends), `/v1/fixes/{id}`, `/v1/navaids/{id}` (several records when a name is shared, e.g. VOR/DME and fan marker), `/v1/airways/{id}` (ordered segments); the FAA's own rows as source text, empty columns dropped, optional `?cycle=`; lookups on one cycle take turns on its DuckDB connection (60 concurrent requests tested). Checked on the real cycle | done |
| 4.7b `/v1/airspace/at?lat=&lon=`: the FAA CSV has **no Class B/C/D/E polygons** (`CLS_ARSP` only flags which class an airport has), so the endpoint searches the ARTCC low/high, FIR, CTA and UTA boundaries from `ARB_SEG` (spatial index, antimeridian-safe, arcs approximated by their vertices) and says what is not covered. Real cycle: ABQ -> ZAB, Anchorage -> ZAN, mid-Atlantic -> ZWY oceanic | done |
| 4.8 `max_segment_nm` (great-circle points, kind `interpolated`, capped at 10,000 points); `docs/openapi.json` generated by `tools/export_openapi.py` with contract tests that fail when it is stale or an operation loses auth/429/401 documentation; per-key token-bucket rate limit (429 + Retry-After, `/health` and `/ready` exempt); `X-Request-ID` echo/generation and one JSON access-log line per request (key label only, never the key or route text); clean 500 with a request id | done |
| 4.9 `api/deploy/openNASR-api.service`, `api.env.example`, `api/Dockerfile`, `api/README.md`. systemd deployment verified on LXC 125. CI boots the Docker image and checks readiness and routing. | done |

**Phase 4 exit criterion met** (API v1 + supporting endpoints, API keys, OpenAPI published, contract tests); deployment is Phase 6.

## 8e. Phase 5 (local mode) - done

| Task | Status |
|------|--------|
| 5.1 One serialization of a route result for both modes: `openNASR.routejson.route_result_to_dict` (+ `openNASR.geo`, `RouteResolver.from_nasr`, `ROUTE_TABLES` now in core); the API builds its response from it | done |
| 5.2 `opennasr route` (json / geojson / table, `--icao-message`, `--cycle`, `--max-segment-nm`, `--strict`, stdin) | done |
| 5.3 `opennasr serve` (the same FastAPI app on the local cache; session key printed, or `--no-auth` on loopback only) | done |
| 5.4 `opennasr fetch` (validated cycles from the bucket with hash checks, else FAA direct); `CycleManager.servable_cycles()` counts database-only cycles | done |
| 5.5 Contract parity: the same six request bodies (complete, unknown fix, ignored group, densified, named cycle, ICAO message) give identical JSON from the CLI and the API; docs in `docs/local-mode.md` | done |

Checked on the real cycle: `fetch latest` from Garage, `route` (table, geojson, stdin, `--strict` exit 1 for the branching arrival),
and `serve --no-auth` answering a route and an airspace lookup. **Phase 5 exit criterion met.** Next: Phase 6 (deploy), which
needs the host, network, key and proxy decisions listed in the Phase 4 summary.

## 8f. Phase 6 (deploy) progress, 2026-11-18

Owner decisions: containers on proxopotamus; Garage reached over the VLAN (`http://10.10.30.121:3900`); **no API keys for
now** (explicit `OPENNASR_API_AUTH=none`); published **through NPMplus** (the `*.xds-lab.com` wildcard is tailnet-only), so the
containers are not joined to Tailscale.

| Task | Status |
|------|--------|
| 6.1 Host installer `deploy/proxmox/install.sh` + in-container `deploy/guest/guest-setup.sh`: unprivileged Debian 13 LXC, venv from local wheels, **DuckDB probed by running it** (1.5.6 kept on the Xeon E5-2620; 2.x is not a candidate while core caps `duckdb<2`), systemd units, health check | done |
| 6.2 LXC 125 `opennasr-api` (10.10.20.125) created from scratch twice (the first run found the packaging bug below); real routes answered | done |
| 6.3 LXC 124 `opennasr-archiver` (10.10.20.124): first real pass fetched the FAA cycle and found it already published; timer 06:15 UTC | done |
| 6.4 NPMplus proxy host id 30 `opennasr.xds-lab.com`, cert 1, HTTPS forced; verified | done |
| 6.5 No-key mode: refuses to start without keys unless `OPENNASR_API_AUTH=none`; warns at start; rate limit per client address (first `X-Forwarded-For` hop), 600/min | done |
| 6.6 Archiver cache pruning keeps the two newest cached cycles and removes older cycles once published | done |
| 6.7 Packaging fix: schema manifests moved to `openNASR/schema_manifests/` and shipped in the wheel (they were read from `tests/` and did not exist in an installed package); core version set to 2.0.0 | done |
| 6.8 Gatus + Homepage entry and Slack alert for the API | done (2026-11-17/18) |
| 6.9 Signed releases and updater. Rollback and roll-forward were exercised on `v2.0.0`. Both guests now run `v2.0.1` and retain `v2.0.0` for rollback. | done |
| 6.10 Updater verifies hash-pinned dependencies, checks archiver bucket access, and prunes superseded venvs while preserving rollback. Both guests kept DuckDB 1.5.6. | shipped in `v2.0.1` |
| 6.11 Docker smoke test in CI. Both images run as non-root, the archiver publishes a synthetic cycle to a local bucket, and the API fetches it and answers `/ready` and `/v1/route/resolve`. [First passing run](https://github.com/xDecisionSystems/openNASR/actions/runs/44235847511) | done |
| 6.12 PyPI publishing is manual and lower priority. API keys await the owner’s direction. | open |

Docs for the lab: `IT-management-UCF/documentation/{hosts/opennasr-api,hosts/opennasr-archiver,services/opennasr}.md` and the
`2026-11-17-opennasr-v2-0-1-rollout.md` change record. [Release and updater procedure](RELEASE.md)

## 8g. Phase 7 observation

| Checkpoint | Evidence or exit criterion | Status |
|------------|---------------------------|--------|
| Signed deployment baseline | Independently verified the Sigstore signature and seven asset hashes for [`v2.0.1`](https://github.com/xDecisionSystems/openNASR/releases/tag/v2.0.1). Both guests run that release. | done |
| First production pass on `v2.0.1` | Manual run on November 17 at 10:38 p.m. ET exited 0 and logged `already_published 2026-10-29`. Four manifests remained in Garage, with no active archiver alerts. | done |
| API and cached-cycle baseline | Gatus was green and the API defaulted to 2026-10-29. Explicit queries for 2026-10-29 and 2026-11-26 each resolved `KABQ.DOOKK3.TXO..KTYR` completely with eight points. The archive, DuckDB, and sidecar hashes matched the Garage manifests for both cycles. | done |
| First timer-triggered pass on `v2.0.1` | Record the timer's last trigger, the service run start and exit status, and any active alerts. The most recent check still showed no timer trigger. | open |
| 2026-11-26 becomes effective | Confirm `/v1/cycles` and `/ready` select the prepublished 2026-11-26 cycle and a default-cycle route resolves. | open |
| First publication of 2026-12-24 | Once the FAA posts the cycle, confirm the timer publishes its manifest, verify archive, DuckDB, and sidecar hashes, and resolve a route explicitly against it before it becomes the default. Check alert state. | waiting for FAA publication |

For each check run `deploy/proxmox/observe.sh --env-file .env` (read-only: API default cycle and a route on every cycle, timer last/next trigger, last service result, active alerts, deployed releases, Gatus, and every manifest's DuckDB and sidecar hashes; add `--zips` to also re-download and hash the archives). It exits 1 on any FAIL; "the timer has not fired yet" is a WARN until about 06:24 UTC on 2026-11-18. Baseline run 2026-11-18 04:30 UTC: all PASS.

Bucket integrity alone: `python tools/verify_bucket.py --env-file .env [--cycle D] [--zips]`.

The API selects its default from the newest cached cycle effective on the current
UTC date. The November 26 rollover tests selection of a cached cycle. The
December 24 checkpoint tests delivery of a newly published build as well as API
resolution against that explicit cycle. For the integrity check, use
`openNASR_contract.fetch_build` with a fresh temporary cache for the DuckDB and
sidecar, then download the archive with read-only bucket access and compare its
SHA-256 with the manifest's archive hash.

### 2.14 Ambiguity returns every candidate (owner decision, 2026-11-18)

An ambiguous identifier (about 68 of 46,580 pool routes, e.g. `ZFP` as NDB and VOR/DME) stays unresolved, but its diagnostic now carries `detail.candidates`: name, kind, navaid type and coordinates of each record, so the caller decides. `_Waypoint.subtype` holds the navaid type. Needs a release to reach the live API.

### 2.15 Class B/C/D/E airspace polygons (owner decision, 2026-11-18: add the FAA shapefile data)

Findings (checked against the real 2026-10-29 page and file):
- Each cycle page links `https://nfdc.faa.gov/webContent/28DaySub/<date>/class_airspace_shape_files.zip` ("Class B,C,D,E Airspace Shape Files"), next to the CSV zip the archiver already reads. It is downloadable for the current (2026-10-29) and the upcoming (2026-11-26) cycle. 150 MB.
- It holds one shapefile, `Shape_Files/Class_Airspace.shp`: 5,621 POLYGONZ records (CLASS B 369, C 340, D 578, E 4,334; LOCAL_TYPE such as CLASS_E5, CLASS_D). Fields include IDENT, NAME, UPPER_VAL/UPPER_UOM/UPPER_CODE, LOWER_VAL/LOWER_UOM/LOWER_CODE, CLASS, LOCAL_TYPE, MIL_CODE, SECTOR, WKHR_CODE.

Proposed design, not built yet:
- Archiver downloads the shapefile zip as a second input of the same cycle; the manifest records its SHA-256 (new key, layout/builder bump so older builds stay valid).
- Polygons are stored as a table in the same DuckDB file (WKB geometry plus the attributes), so the fetch, sidecar and update paths stay unchanged.
- The API builds a shapely index from it, as it does for ARTCC boundaries, and `/v1/airspace/at` adds class B/C/D/E regions with their altitude limits (an altitude parameter can filter by floor and ceiling).
- Open sub-questions for the owner: whether to filter by an `alt` parameter, and whether to keep older builds without the table.

### Repository layout (changed 2026-11-18, owner decision)

The core library moved from the repository root into `core/` (`core/openNASR`, `core/pyproject.toml`, `core/README.md`,
`core/LICENSE`, `core/MANIFEST.in`), matching the layout planned in section 3. The root keeps shared tests, tools, docs,
deploy files, a short project README and a `pyproject.toml` with only the shared pytest/ruff/mypy settings. Install with
`pip install -e "./core[dev,plot]"`. History is preserved (`git mv`). Verified: 622 tests pass; the core wheel built from `core/` has
exactly the same 59 files and contents as the wheel built before the move; all five artifacts pass `twine check`. CI, the release
workflow, the PyPI workflow, both Dockerfiles, Dependabot and Read the Docs were updated; the Docker job and the release workflow's
build job run on the first push to `main` and are the final check of the paths.

#### 2.15 progress (Class B/C/D/E polygons) and what is left

Design change from the first sketch: the polygons are a **separate Parquet artifact**, not a table in the main DuckDB file
(every table in that file must be modeled in the FAA schema catalog or the library refuses to open the cycle). The manifest gets an
optional `class_airspace` block; readers ignore unknown keys, so the deployed 2.0.1 readers keep working on new builds.

| Step | State |
|------|-------|
| C1 Contract: `BuildKeys.class_airspace`, `class_airspace_source_key`, `Manifest.class_airspace` (source zip, parquet, rows), `fetch_build` installs `class_airspace.parquet` with hash checks; tests | done (3917b5f) |
| C2 `archiver/openNASR_archiver/classairspace.py` `build_class_airspace(zip, parquet)`: reads `Class_Airspace.shp` with pyshp, keeps FAA attributes as text, 2D WKB in `GEOMETRY_WKB`, repairs and counts invalid outlines, refuses implausible input; `pyshp` added to the archiver and core dev dependencies; tests with a synthetic shapefile | done |
| C3 Provider discovers the cycle-specific NFDC shapefile link and `CycleManager.download_airspace` streams it into the archive cache with a size cap, ZIP validation, atomic rename, and a SHA-256 sidecar. Verified with the actual 149,804,280-byte archive for 2026-10-29. | done |
| C4 Archiver publishes builder 2 with the source shapefile ZIP and Parquet, commits the manifest last, and blocks missing or invalid shapefiles. Daily runs, backfill, and rebuild use the new artifacts. Builder 1 remains readable. Verified the October 29 publication and fetch with all 5,621 polygons in a local bucket. | done |
| C5 API indexes the verified shapefile derivative alongside existing boundaries. Class results include `airspace_class`, `local_type`, and the published lower and upper values, units, and codes. The response identifies cycles that lack the derivative. OpenAPI and tests cover the new fields, older cycles, and refresh. Altitude filtering remains a separate decision. | done |
| C6 The local API loaded the real 2026-10-29 data (B 369, C 340, D 578, E 4,334) and returned the expected class at test points near Dallas/Fort Worth, Albuquerque, Santa Monica, and Hillsboro, alongside ARTCC boundaries. Pending: sign the release, update both containers, backfill the four published cycles as builder 2 in Garage, and verify the rollout. | locally verified |

Real-data facts: the zip is 150 MB; `Class_Airspace.shp` is POLYGONZ; example record NAME 'HILLSBORO CLASS E5', LOCAL_TYPE CLASS_E5, UPPER_VAL -9998 (UPPER_DESC 'AA'), LOWER_VAL 700, LOWER_UOM FT, LOWER_CODE SFC.
