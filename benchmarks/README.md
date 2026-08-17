# Benchmarks

All openNASR benchmarking code and data lives here. Nothing in this
directory runs in CI or affects the release gate; every script is an opt-in
diagnostic. See `SPEEDUP.md` and `ROUTE_PATH_PLAN.md` at the repository root
for the performance work these scripts measure.

## Quick start

```bash
python -m benchmarks.run_benchmarks
```

Prints a short, human-readable summary of average route-resolution
performance across a diverse, randomly sampled set of real flight plans —
mean, median, and p95 warm-resolution time, broken out by route shape
(direct/airway-only vs. procedure-containing), since those two categories
have very different costs. It requires one locally cached NASR cycle (any
cycle; add `--cycle YYYY-MM-DD` for an exact one) and never downloads data.

## Files

| File | Purpose |
| --- | --- |
| `run_benchmarks.py` | Primary entry point. Samples diverse real routes from `data/example_routes.csv` and prints human-readable averages. |
| `data/example_routes.csv` | 46,580 real FAA route-field strings, one per line, used as the diverse input pool for `run_benchmarks.py` and `route_path_validation.py` (in `tools/`). Public aeronautical reference data only — no personal information. |
| `route_benchmark.py` | Machine-readable (JSON) CSV/DuckDB route-resolution benchmark against a fixed six-route synthetic matrix (direct, fix/navaid, airway-only, DP-to-airway, airway-to-STAR, DP-and-STAR). Use for exact before/after comparison of one representative case per route shape. |
| `flightplan_benchmark.py` | Synthetic-data microbenchmark comparing the current vectorized `_WaypointResolver`/`_is_published_airway` against the pre-vectorization row-by-row reference implementation. No NASR cycle required. |
| `duckdb_benchmark.py` | CSV-vs-DuckDB storage benchmark (build, cold table access, warm table access) against either a real cached cycle or the committed tiny parity fixtures. Reports raw JSON with machine/package/git provenance for archival comparison. |

`tools/route_path_validation.py` is a related but distinct correctness
tool (not a benchmark): it samples routes the same way and reports
success/failure categories, not timing. It stayed in `tools/`.

## Conventions

- Every script accepts `--cycle`/`--cache-dir` to select a locally cached
  NASR cycle; none of them download data.
- `run_benchmarks.py` prints plain text; `route_benchmark.py` and
  `duckdb_benchmark.py` print JSON (`--output PATH` to write a file instead
  of stdout). Keep generated JSON reports outside this directory and outside
  the repository — only the benchmark *code* and the small input dataset
  belong in `benchmarks/`, not run output.
- Absolute timings are diagnostic evidence, not CI thresholds — they vary by
  machine. When recording a result for a plan's Decision log, report the
  environment (OS, CPU, Python/pandas/DuckDB versions) alongside the
  numbers, matching `docs/DUCKDB_BENCHMARK_REPORT_TEMPLATE.md` and
  `docs/route_path_baseline_2026-05-14.md`.
