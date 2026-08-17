# Speedup benchmark report — 2026-05-14

This is the dated, non-CI report for the table-lookup and plotting speedup
plan. The most severe result is Phase 2: the first `nasr.airport(...)` lookup
fell from approximately 41.3 seconds to 138.936 ms (about 297x faster), while
the first `nasr.fixes.get(...)` lookup fell from approximately 14.9 seconds to
103.860 ms (about 143x faster).

## Run identity

| Field | Value |
| --- | --- |
| UTC timestamp | 2026-08-17; exact command timestamps were not retained in the gate notes |
| Exact effective cycle | `2026-05-14` |
| Git commit / dirty state | `d7debd8`, dirty working tree during the phase-gate run; production and test changes were present |
| Commands | `.venv/bin/python -m benchmarks.repository_benchmark --cycle 2026-05-14 --cache-dir /home/aev/.cache/openNASR --storage csv`; `.venv/bin/python -m benchmarks.run_benchmarks --cycle 2026-05-14 --cache-dir /home/aev/.cache/openNASR --storage csv`; `.venv/bin/python -m benchmarks.plotting_benchmark --cycle 2026-05-14 --cache-dir /home/aev/.cache/openNASR --storage csv` |
| Cache and report paths | NASR cache: `/home/aev/.cache/openNASR`; this report is part of the integrated release change set; raw benchmark output and figures remain outside the repository |
| Storage backends | CSV for the canonical gate; DuckDB parity was separately verified for route/repository paths |

## Machine and software

The gate host was Linux 6.8.0-137-generic, x86-64, 8 logical CPUs, 15 GiB
RAM, and an NVMe filesystem. The current environment reports Python 3.12.3,
pandas 3.0.5, Matplotlib 3.11.1, Shapely 2.1.2, and DuckDB 1.5.5.

Tables were loaded before lookup timing. Repository and route measurements use
one cold lookup followed by warmed repetitions; Phase 3's exact-key checks use
20 warm repetitions. Plotting uses Matplotlib's `Agg` backend. Each plotting
case constructs a fresh lazy `PlottingIndex`; its first plot includes lazy
feature-index construction, and subsequent calls reuse that same index. The
ten-airport case reuses one index across all ten airport plots. Timings are
diagnostic evidence, not portable CI thresholds.

## Repository results

The formal comparisons below use the exact keys and call shapes recorded by
the Phase 2/3 gates. The fresh seeded repository run additionally reported
warm medians of 1.740 ms for legacy `FIX`, 1.013 ms for legacy `Airport`,
3.876 ms for legacy `NAVAID`, 2.191 ms for modern fixes, 15.012 ms for modern
airports, 3.175 ms for modern navaids, 0.694 ms for coded departure routes,
1.113 ms for location identifiers, 1.684 ms for frequencies, 3.535 ms for
preferred routes, 27.836 ms for the seeded multi-key airway sample, 4.545 ms
for holding patterns, 4.763 ms for military routes, and 3.558 ms for ATC
facilities. The formal single-key airway comparison remains the `A216` row
below.

| Workload | Baseline warm | Current warm | Improvement | Notes |
| --- | ---: | ---: | ---: | --- |
| `nasr.fixes.get(...)` first call | ~14.9 s | 103.860 ms | ~143x | First-build-inclusive; repeated call 1.764 ms |
| `nasr.airport(...)` first call | ~41.3 s | 138.936 ms | ~297x | First-build-inclusive; repeated call 15.793 ms |
| Legacy `FIX("AABEE")` | 32.780 ms | 1.529 ms | 21.43x | Exact successful probe |
| Legacy `Airport("XS29")` | ~27.5 ms | 0.928 ms | 29.63x | Exact successful probe; avoids known geometry failures |
| Legacy `NAVAID("ABR")` | 4.210 ms | 3.714 ms | 1.13x | Meets the amended ≤5 ms floor |
| `isFix` / `isAirport` / `isNavaid` | 16.003 / ~5.6 / 0.511 ms | 0.267 / 0.915 / 0.714 ms | policy pass | Exact identifiers; Airport and NAVAID pass the ≤5 ms floor |
| Airway `A216` | 147.626 ms | 12.419 ms | 11.89x | Exact seven-segment key |
| Holding `AABEE INT*GA*K7` | 40.916 ms | 4.359 ms | 9.39x | Meets the amended ≤5 ms floor |
| Preferred route | 29.794 ms | 3.314 ms | 8.99x | Exact composite key |
| Location identifier | 21.970 ms | 1.024 ms | 21.45x | Exact composite key |
| Military training route | 20.905 ms | 4.008 ms | 5.22x | Exact composite key |
| ATC facility | 14.206 ms | 3.607 ms | 3.94x | Meets the amended ≤5 ms floor |
| Frequency | 12.565 ms | 1.646 ms | 7.63x | Exact composite key |
| Coded departure route | 10.606 ms | 0.639 ms | 16.60x | Exact route code |

The benchmark records known failures separately. The expanded legacy-airport
sample includes airports that hit a pre-existing runway-geometry `TypeError`;
the formal Airport row above measures the successful `XS29` call only.

## Route results

The canonical 100-route sample resolved 85/100 routes after Phase 4, including
84/84 domestic routes under the plan's denominator. Direct/airway-only route
mean timing improved from approximately 422 µs to 57.9 µs. Procedure-containing
route mean timing improved from approximately 183 ms to 16.34 ms (about 11.2x),
with no route-count regression. CSV/DuckDB route-table parity and source order
are documented in [`docs/route_path_baseline_2026-05-14.md`](route_path_baseline_2026-05-14.md).

## Plotting results

| Case | Baseline cold / repeated mean | Post-Phase-5 cold / repeated mean | Result |
| --- | ---: | ---: | --- |
| ZOB airspace | 6.24 s / 6.74 s | 2.94 s / 2.71–2.77 s | ~2.4x warm |
| ATL procedures | 5.21 s / 4.96 s | 0.67–0.69 s / 0.209 s | ~23.7x warm |
| Ten-airport procedures | 48.47 s / 47.43 s | 1.80–1.81 s / 1.69–1.81 s | ~26–28x warm |
| Direct flight plan | 0.45 s / 0.40 s | 0.55–0.56 s / 5.4–5.7 ms | ~70x warm |
| Procedure flight plan | 0.39 s / 0.43 s | 0.424–0.425 s / 15.9–16.5 ms | ~26x warm |

Helper probes separated lookup work from artist creation: `_airway_segments`
fell from approximately 2.0 s to 0.323 s cold and 1.64 µs warm; ATL departure
and STAR lookup calls fell from approximately 1.5 s each to 23.7 ms and
18.2 ms; and ten airports across both procedure layers took 59.6 ms warm,
versus approximately 14.8 s for the Phase 0 departure-layer baseline alone.
The remaining airspace and batch totals are predominantly Matplotlib artist
creation rather than repeated full-table scans.

All four plotting examples completed headlessly and wrote non-empty PNGs:
ATL reported 643 lines, ZOB 4,518 lines, the airport-ILS example 10 wedges,
and runway-localizer views completed successfully with unchanged output.

## Decision

- [x] Exact cycle, CSV backend, machine, and cold/warm policy are recorded.
- [x] Before/after repository, route, and plotting evidence is recorded.
- [x] Plotting errors were absent in the canonical five-case benchmark, and
      example-script output/PNG checks completed.
- [x] Timings are explicitly diagnostic rather than CI thresholds.
- [x] Gate 6 release approval was subsequently granted on the complete dirty
      integration tree; `SPEEDUP.md` records the commands, results, package
      inspection, and explicit clean-checkout caveat.

Conclusion: Phases 2–5 meet their approved performance and parity gates. The
public `PlottingIndex` provides lazy, snapshot-scoped reuse for batch plotting;
the subsequent Gate 6 release validation passed on the complete dirty
integration tree. This report and `SPEEDUP.md` do not characterize that run as
a clean-checkout validation.
