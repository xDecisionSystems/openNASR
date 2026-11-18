# openNASR handover

State of the project on **2026-11-18**. Read this first; `REPLAN.md` is the long working plan and decision log behind it.

## 1. What this is

openNASR resolves an FAA flight-plan route string (or an ICAO FPL message) to an ordered list of latitude/longitude points, using FAA NASR 28-day subscription data. The work is deterministic data expansion: same route + same cycle = byte-identical output. It is **not** trajectory prediction, wind, performance, or comparison of flown tracks (the owner ruled those out of scope).

It has three runnable parts:

| Part | Where | Does |
|---|---|---|
| **Archiver** | `archiver/`, deployed in LXC 124 | Daily: fetch the FAA cycle (current + upcoming), build a DuckDB file, validate, upload zip + db + sidecar + manifest to S3. |
| **Bucket** | Garage S3, bucket `opennasr` | Immutable, content-addressed keys; the manifest is uploaded last and is the "validated" marker. |
| **API** | `api/`, deployed in LXC 125 | Read-only FastAPI service; fetches verified cycles from the bucket. Live at `https://opennasr.xds-lab.com`. |
| **Local mode** | core CLI | `opennasr route | serve | fetch` give the same JSON as the API. |

## 2. Repository map (`/srv/projects/openNASR`, GitHub `xDecisionSystems/openNASR`)

```
openNASR/            core library (package "openNASR", version 2.0.1). No I/O policy; depends on neither contract, archiver nor api.
  flightplan.py      import point for route resolution (re-exports the public API and the private names tests use)
  _route_common.py, _route_waypoints.py, _route_airways.py, _route_procedures.py, _route_tokenizer.py, _route_resolver.py
                     the implementation, layered in that order (a module imports only from earlier ones). Flat files on purpose: the wheel lists only the top package
  routeresult.py     RouteResult / RoutePoint / RouteDiagnostic
  routejson.py       route_result_to_dict(): THE JSON shape, used by the API and the CLI
  geo.py             great-circle densify
  icaomessage.py     ICAO FPL parser
  schemas.py, schema_manifests/*.json   FAA schema catalog; the manifests ship inside the wheel
  duckdb_builder.py, duckdb_metadata.py, nasr.py, cycles.py, cli.py ...
contract/            package openNASR-contract: bucket key layout, Manifest, LocalBucket/S3Bucket, list/select/fetch (the ONLY coupling between archiver and api)
archiver/            package openNASR-archiver: publish_cycle, run_once (alerts, pruning, upcoming), backfill, rebuild, CLI
api/                 package openNASR-api: CycleStore, FastAPI app, lookups, airspace index, rate limiter
deploy/proxmox/install.sh, deploy/guest/guest-setup.sh   container creation + in-container setup
archiver/deploy, api/deploy   systemd units and env examples
archiver/Dockerfile, api/Dockerfile   images built and smoke-tested in GitHub CI
docs/openapi.json    the published API contract (generated; a test fails if stale)
docs/route-coverage.md, docs/local-mode.md
tests/               about 75 entries; tests/fixtures are small synthetic cycles
tools/               export_openapi.py, route_corpus.py, route_path_validation.py (batch over a route pool) ...
REPLAN.md            plan, phase tables, decisions log, findings with numbers
```

`archiver` and `api` must never import each other. `core` must not import either.

## 3. Git state

- The long-running branch `phase0-housekeeping` was **merged to `main` as PR #2 on 2026-11-18**. GitHub CI passes on `main` (Python 3.10/3.12/3.14 matrix, lint, mypy, package build). **Workflow (owner's rule): commit directly to `main`. No feature branches, no PRs, no merge commits.** Tags are the only release step.
- Added after the first handover: Python 3.10 test compatibility, a cache-preserving store refresh, hardened `max_segment_nm` limits, `NASR.close()`, the signed-release workflow (`.github/workflows/release.yml`) and the updater (`deploy/opennasr-update`, tested by `tests/test_deployment_update.py`).
- The route-module split and validation-tool fix in `ee450d1` are on `main`. The live guests use the earlier signed `v2.0.1` tag at `d74c1a5`.
- [`v2.0.1`](https://github.com/xDecisionSystems/openNASR/releases/tag/v2.0.1) is the current signed release. Its Sigstore manifest covers the four wheels, the updater, and both dependency locks. All seven hashes and the signature were verified independently. A `v*` tag starts the signed deployment release (`release.yml`). PyPI publishing remains pending and uses a separate manual workflow with owner approval. The owner said PyPI is lower priority.
- The first `v2.0.0` tag was moved once: its release run failed after signing because the publish job had no checkout (`gh` needs `GH_REPO`), the fix was merged (PR #5), and the unreleased tag was re-created on the fixed commit. Cutting a release is therefore tested end to end. If a release run fails after tagging, nothing is published; fix on `main`, then delete and re-create the tag only if no release exists.

## 4. Build, test, lint (all green at handover)

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,plot]"          # dev includes pytest, ruff, mypy, fastapi, httpx, uvicorn
pytest                                 # 592 passed, 1 skipped, ~80 s. pytest config puts contract/, archiver/, api/ on the path.
ruff format --check openNASR contract archiver api tests benchmarks tools
ruff check          openNASR contract archiver api tests benchmarks tools      # line length 88
MYPYPATH=contract:archiver:api mypy openNASR contract/openNASR_contract archiver/openNASR_archiver api/openNASR_api
python tools/export_openapi.py         # REQUIRED after any API change, then commit docs/openapi.json
```

Fixtures: use `make_nasr_from_fixture("core/pre_2026_09")` (builds a cycle once per session into a cache and copies it) or `"schema_only/nasr_2026_09"` (recognised schema, empty tables). Archiver/API tests publish the schema-only fixture to a `LocalBucket`.

Optional S3 extra needs boto3; tests use a fake client and do not need it.

## 5. Facts that cost time to learn

1. **DP and STAR rows are stored in flight order.** The code once reversed them (every procedure came out backwards). Verified on a full cycle: the served airport is at the first point of 1,021/1,024 DP bodies and the last point of 1,179/1,186 STAR bodies. The convention is declared per schema in `SchemaCatalog.PROCEDURE_ORDER`, recorded in the sidecar/manifest as `procedure_order`, and `RouteResolver` refuses anything but `flight_order`. Do not reverse rows.
2. **DuckDB 2.x crashes ("Illegal instruction") on CPUs without AVX2.** The devbox and proxopotamus are Xeon E5-2620 (Sandy Bridge). Core pins `duckdb>=1.2.2,<2`; the installer *runs* DuckDB to probe (1.5.6 works). Do not lift the cap without testing on that CPU.
3. **All tables are stored as source text.** Numeric accessors go through `as_number`. Tests assert source-text values (`"121.500"`, not `121.5`).
4. **Runway-dependent branches are normal FAA data**, not errors. An arrival/departure with several bodies (per runway/config) returns only the portion common to all, plus a `procedure_branches` *warning* diagnostic (so `complete: false`). The owner was explicit about this.
5. **`info` diagnostics do not affect `complete`** (ignored speed/level groups, a departure with no published points ending at its computer-code suffix). `warning` ones do.
6. **FAA site**: past, current and upcoming cycles all have detail pages (`FaaCycleProvider.for_date`). HEAD requests to the zip return 503; use GET. A re-posted preview zip gets a new hash and so new keys (key = date + zip sha); readers pick the newest build per date.
7. **Garage needs `request_checksum_calculation="when_required"`** on the boto3 client (already set in `S3Bucket`). Path-style addressing, region `garage`.
8. **`s3.xds-lab.com` is tailnet-only.** Containers reach Garage at `http://10.10.30.121:3900` over the VLAN.
9. **`/tmp` on the devbox is a 7.9 GB RAM-backed tmpfs.** One extracted cycle is ~1.4 GB. Put caches on disk. This broke two runs.
10. **`pip wheel archiver` fetches an unrelated PyPI package.** Always pass paths: `pip wheel --no-deps -w DIR . ./contract ./archiver ./api`.
11. **FastAPI with `from __future__ import annotations`**: any object used inside an annotation (`Depends(...)`, `Annotated` aliases) must be module-level, not local to `create_app`, or the dependency silently stops working.
12. **Shapely `STRtree.query(point, predicate="intersects")`** is the right direction for point-in-polygon. Some regions cross the antimeridian (Alaska): handled by a second tree with longitudes shifted by 360.
13. **The FAA CSV has no Class B/C/D/E polygons** (`CLS_ARSP` only flags a class per airport). `/v1/airspace/at` covers ARTCC/FIR/CTA/UTA from `ARB_SEG` and says so in `not_covered`.
14. Never `source` an `.env` file (values contain `|`, quotes). Read variables with a parser; `S3Bucket`'s `load_env_file` does.

## 6. Real-data results (cycle 2026-10-29, pool `benchmarks/data/example_routes.csv`, 46,580 routes)

Run with `python tools/route_path_validation.py --full-file benchmarks/data/example_routes.csv --cycle 2026-10-29 --cache-dir <cache>` (12-20 minutes):

| Outcome | Routes | Meaning |
|---|---|---|
| resolved | 18,042 | exact |
| resolved_with_branches | 14,815 | runway branches reported |
| **usable** | **32,857 (70.5%)** | |
| not_in_cycle | 8,023 | pool was filed against older cycles; names retired/replaced; foreign points |
| outside_scope | 5,632 | foreign airports, oceanic coordinates, external routes |
| ambiguous | 68 | e.g. `ZFP`: an NDB and a VOR/DME share one identifier |

`not_in_cycle` is not a defect; a fair rate needs routes filed for the cycle under test (the owner's data).

## 7. What is deployed (proxopotamus, `ssh root@100.100.10.10`; the devbox key works)

| | Archiver | API |
|---|---|---|
| LXC | 124 `opennasr-archiver`, VLAN 20 `10.10.20.124` | 125 `opennasr-api`, VLAN 20 `10.10.20.125` |
| Install | Signed `v2.0.1` under `/opt/openNASR/releases/`, user `opennasr` | same |
| Settings | `/etc/openNASR/archiver.env` (mode 640) | `/etc/openNASR/api.env` (mode 640) |
| Run | `openNASR-archiver.timer` daily 06:15 UTC +<=20 min; service is a oneshot | `openNASR-api.service`, port 8000 |
| Disk / RAM | 24 G / 2 GB | 8 G / 3 GB (`MemoryMax=3G`) |

- Published through NPMplus: proxy host **id 30** `opennasr.xds-lab.com` -> `http://10.10.20.125:8000`, certificate 1, HTTPS forced. DNS is the Cloudflare wildcard `*.xds-lab.com` -> a tailnet-only address, so only tailnet clients can reach it.
- **The API runs with no keys** (`OPENNASR_API_AUTH=none`, the owner's decision "no key for now"). It warns at startup, refuses to start without keys unless that is set, and rate-limits 600/min per client address (first `X-Forwarded-For` hop). To enable keys: set `OPENNASR_API_KEYS=a,b` in `api.env`, remove `OPENNASR_API_AUTH`, `systemctl restart openNASR-api`.
- Bucket `opennasr` holds four cycles on the current FAA schema `nasr_2026_09`: 2026-09-03, 2026-10-01, 2026-10-29, 2026-11-26 (the last is the upcoming one). **Owner decision: backfill the current format only; nothing older.**
- **Monitoring (added 2026-11-17/18):** Gatus check `private-sites_opennasr-api` (`/ready` every 2 min: HTTP 200, `status == ready`, certificate > 48 h; Slack after two failures, recovery notice) and a Homepage tile in the Research group; see the lab's `changes/2026-11-17-opennasr-monitoring.md` for the rollback files. The archiver itself has no Gatus check; it alerts to Slack on its own.
- Alerts: Slack via `OPENNASR_ALERT_WEBHOOK_URL`; fire once, resolve once, state in `/var/lib/openNASR-archiver/state.json`. Kinds: source_unavailable, validation_failed, build_failed, bucket_unavailable, no_new_cycle (28+3 days), upcoming_cycle_failed.
- Garage keys (created 2026-11-16 via the Garage CLI in LXC 121): `opennasr-archiver` read+write, `opennasr-api` read-only, neither can create buckets.

### Quick health checks

```sh
curl -s https://opennasr.xds-lab.com/ready
curl -s https://opennasr.xds-lab.com/v1/cycles
curl -s -X POST https://opennasr.xds-lab.com/v1/route/resolve -H 'content-type: application/json' -d '{"route":"KABQ.DOOKK3.TXO..KTYR"}'
ssh root@100.100.10.10 'pct exec 124 -- systemctl list-timers openNASR-archiver.timer --all; pct exec 124 -- journalctl -u openNASR-archiver -n 10 --no-pager'
ssh root@100.100.10.10 'pct exec 124 -- systemctl show openNASR-archiver.timer -p LastTriggerUSec -p NextElapseUSecRealtime; pct exec 124 -- systemctl show openNASR-archiver.service -p ExecMainStartTimestamp -p ExecMainStatus -p Result'
```

Compare the timer trigger with the service start. The most recent service
status can belong to a manual run. Active alert kinds are under `active` in
`/var/lib/openNASR-archiver/state.json`.

### Secrets (names only; never print values)
- `openNASR/.env` (gitignored, mode 600): `OPENNASR_S3_*`, `OPENNASR_ARCHIVER_S3_*`, `OPENNASR_API_S3_*`, `OPENNASR_ALERT_WEBHOOK_URL`.
- `/srv/projects/IT-management-UCF/.env`: the lab's admin tokens (NPMplus, Tailscale, Garage, Slack). Used only for infra tasks the owner asked for.

## 8. Next steps

Both guests run signed `v2.0.1` with DuckDB 1.5.6 and retain `v2.0.0` for rollback. The updater verifies dependency locks, checks archiver bucket access before switching, and prunes superseded venvs. For non-login `pct exec` shells, export `PATH="/usr/local/bin:/usr/local/sbin:$PATH"` so the updater can find Cosign. See [RELEASE.md](RELEASE.md) for the rollout procedure.

1. **Phase 7 observation is in progress.** The manual production pass on `v2.0.1` exited 0 with `already_published 2026-10-29` and no active alerts. Verify the first timer-triggered pass, then check that the API defaults to 2026-11-26 when that prepublished cycle takes effect. When the FAA posts 2026-12-24, verify its Garage manifest, artifact hashes, and explicit-cycle API response. See [the observation checklist](REPLAN.md#8g-phase-7-observation).
2. **API keys** when the owner asks (see section 7). Document who holds which key in the IT-management-UCF repo.
3. **Refactors**: `flightplan.py` is already split (done 2026-11-18, verified identical on 9,316 real routes). Remaining: `_route_procedures.py` is still ~900 lines (its `_ProcedureIndex` could move out); move core into a `core/` directory. Verify any routing change with `tools/route_corpus.py` and by running the same pool sample through the old and new code (usable must stay at 70.3% of every 5th route, 70.5% of the full pool).
4. **Backups**: Garage is single-node, replication factor 1, no backup. The zips are re-downloadable from the FAA only while the FAA keeps them.
5. **Pending owner discussion**: what counts as "ambiguous" (the `ZFP` NDB-vs-VOR/DME class). The owner said "we can discuss later". Do not change that behaviour unasked.
6. Class B/C/D/E polygons need a different FAA data source, such as shapefiles.

Docker deployment smoke coverage is complete. CI builds both images and runs
them as their configured non-root users with networking disabled. The archiver
publishes a synthetic cycle to a local bucket, and the API fetches it and
answers readiness and route requests. Production runs in the Proxmox LXCs.
[First passing CI run](https://github.com/xDecisionSystems/openNASR/actions/runs/44235847511)

## 9. Owner preferences and working agreements

- **Commit straight to `main`.** The owner does not want PRs, feature branches or merge commits ("everything should just be committed"). `git config pull.ff only` is set so a pull never creates a merge commit.
- **Do the work; do not keep re-asking.** The owner reacted badly to repeated, rephrased questions. Make a recommendation, state it, proceed. Ask only for decisions that are really theirs (hosts, keys, outward-facing actions).
- Tagging releases, publishing to PyPI, creating infrastructure, using admin tokens, and sending messages require the owner's go-ahead.
- **Precise language matters.** They pushed back on calling normal FAA branching a "failure" and on "ambiguous". Prefer the outcome classes in section 6. Never present a guess as a resolved point; unsupported things become diagnostics.
- **Infrastructure changes are documented in `/srv/projects/IT-management-UCF/documentation`** (host page, service page, a dated change record, inventory/README links), then committed and pushed. See `changes/2026-11-18-create-opennasr-lxcs.md` and `services/opennasr.md` for the pattern.
- Do not print secrets in output, commit messages, docs or Slack. Delete temporary secret files (`shred -u`).
- Licence: GPL-3.0 (the owner: "address licence later; GPL 3 is fine").
- The dev machine is the "devbox" (LXC 122). Its CPU lacks AVX2, so run tests with DuckDB 1.x.

## 10. Where the details are

- `REPLAN.md`: phase tables (8a–8g), decision log (section 9), and real-data findings.
- `CHANGELOG.md`: release notes for 2.0.1 and earlier versions.
- `docs/openapi.json` (API contract), `docs/route-coverage.md` (what each route construct does), `docs/local-mode.md`.
- `archiver/README.md`, `api/README.md`, `deploy/proxmox/install.sh --help`.
- Lab docs: `IT-management-UCF/documentation/services/{opennasr,garage}.md`, `hosts/{opennasr-api,opennasr-archiver,npmplus}.md`.
