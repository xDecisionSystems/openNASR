# Speedup benchmark report — `<cycle or fixture set>`

Use this non-CI template to summarize a manual run of the benchmark tools
under `benchmarks/`. Keep raw JSON, NASR archives, extracted cycles, and
generated figures outside the repository. Route correctness and baseline
counts are maintained in the [route-path baseline](route_path_baseline_2026-05-14.md)
rather than duplicated here.

## Run identity

| Field | Value |
| --- | --- |
| UTC timestamp | `<...>` |
| Exact effective cycle | `<YYYY-MM-DD>` |
| Git commit / dirty state | `<...>` |
| Commands | `<one command per benchmark>` |
| Cache and report paths | `<outside repository>` |
| Storage backends | `<CSV / DuckDB / both>` |

## Machine and software

Record OS/kernel, architecture, CPU model and logical CPU count, RAM,
filesystem, Python, openNASR, pandas, Matplotlib, Shapely, and DuckDB versions.
State whether each run used a fresh process, already-loaded tables, and a
reusable resolver/session. Timings are diagnostic and must not be treated as
portable CI thresholds.

## Repository results

Copy the seeded identifiers and cold/warm median and p95 values from
`repository_benchmark.py`'s run. Include failures and their reason.

| Workload | Count | Cold median/p95 | Warm median/p95 | Notes |
| --- | ---: | --- | --- | --- |
| Legacy `FIX` | `<...>` | `<...>` | `<...>` | `<...>` |
| Legacy `Airport` | `<...>` | `<...>` | `<...>` | `<...>` |
| Legacy `NAVAID` | `<...>` | `<...>` | `<...>` | `<...>` |
| `NASR.isFix` / `isAirport` / `isNavaid` | `<...>` | `<...>` | `<...>` | `<...>` |
| Modern fix/airport/navaid repositories | `<...>` | `<...>` | `<...>` | `<...>` |
| Coded departure routes | `<...>` | `<...>` | `<...>` | `<...>` |

## Plotting results

Copy the headless `plotting_benchmark.py` report. Confirm Matplotlib used the
`Agg` backend and no PNGs were written. Report table loading separately from
plot construction and distinguish the first call from repeated calls.

| Case | Cold median/p95 | Repeated median/p95 | Error/skips | Notes |
| --- | --- | --- | --- | --- |
| ZOB airspace | `<...>` | `<...>` | `<...>` | `<...>` |
| ATL procedures | `<...>` | `<...>` | `<...>` | `<...>` |
| Ten-airport procedures | `<...>` | `<...>` | `<...>` | `<...>` |
| Direct/airway flight plan | `<...>` | `<...>` | `<...>` | `<...>` |
| Procedure flight plan | `<...>` | `<...>` | `<...>` | `<...>` |

## Route evidence

Link to the route-only report and record only cross-backend or environment
observations here. The canonical sample, hashes, category counts, and route
correctness evidence belong in
[`route_path_baseline_2026-05-14.md`](route_path_baseline_2026-05-14.md).

## Decision

- [ ] Exact cycle and storage backend were available and recorded.
- [ ] CSV/DuckDB used the same loaded-table workloads and seeded identifiers.
- [ ] Load, cold construction, and warm repeated resolution/plotting were
      reported separately.
- [ ] Failures/skips and unsupported data coverage are listed.
- [ ] Before/after comparisons cite the corresponding production commit.

Conclusion: `<diagnostic findings and follow-up decision>`
