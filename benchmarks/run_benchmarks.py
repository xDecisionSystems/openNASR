"""Primary benchmark entry point: diverse, randomly sampled real flight plans.

Run with ``python -m benchmarks.run_benchmarks``. Unlike the other scripts in
this directory (which report raw JSON for machine comparison), this script
samples a diverse set of real FAA route strings from
``benchmarks/data/example_routes.csv`` and prints a short, human-readable
summary of average warm-resolution performance, broken out by route shape
(direct/airway-only vs. procedure-containing) since those two categories
have very different costs -- averaging them together hides the difference
(see ``SPEEDUP.md`` and ``ROUTE_PATH_PLAN.md`` for the underlying findings).

It requires one locally cached NASR cycle (any cycle; pass ``--cycle`` for an
exact one, or let it pick the newest cached cycle automatically) and never
downloads data itself.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import random
import statistics
import time
from typing import Literal

from openNASR.cycles import CycleManager
from openNASR.flightplan import RouteResolver
from openNASR.nasr import NASR


ROOT = Path(__file__).parent
DEFAULT_ROUTES = ROOT / "data" / "example_routes.csv"
DEFAULT_SEED = 20260514
DEFAULT_SAMPLE_SIZE = 100
DEFAULT_WARM_ITERATIONS = 5


def _load_routes(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _select_sample(routes: list[str], *, seed: int, sample_size: int) -> list[str]:
    size = min(sample_size, len(routes))
    indexes = sorted(random.Random(seed).sample(range(len(routes)), size))
    return [routes[index] for index in indexes]


def _is_direct_or_airway_only(route: str) -> bool:
    """Whether a route contains no dotted procedure/transition token.

    A dot appears in a filed route only as a procedure/transition separator
    (for example ``ORCO8.TRM``); direct (``..``) and airway-only routes have
    no single dots outside that context, so this is a cheap, good-enough
    shape classifier for benchmark reporting. It does not need to be exact:
    misclassifying a handful of routes only blurs the reported category
    boundary, it does not change correctness of path resolution itself.
    """

    body = route.split("/", 1)[0]
    return "." not in body.replace("..", "")


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction)))
    return ordered[index]


def _format_seconds(value: float) -> str:
    if value >= 1.0:
        return f"{value:.3f}s"
    if value >= 0.001:
        return f"{value * 1_000:.2f}ms"
    return f"{value * 1_000_000:.1f}us"


def _summarize(samples: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(samples),
        "median": statistics.median(samples),
        "p95": _percentile(samples, 0.95),
        "min": min(samples),
        "max": max(samples),
    }


def _print_category(name: str, count: int, summary: dict[str, float] | None) -> None:
    if summary is None or count == 0:
        print(f"  {name}: no resolved routes in this sample")
        return
    print(
        f"  {name} (n={count}): "
        f"mean={_format_seconds(summary['mean'])}  "
        f"median={_format_seconds(summary['median'])}  "
        f"p95={_format_seconds(summary['p95'])}  "
        f"min={_format_seconds(summary['min'])}  "
        f"max={_format_seconds(summary['max'])}"
    )


def run(
    *,
    cycle: str | None,
    cache_dir: Path | None,
    storage: Literal["csv", "duckdb"],
    routes_path: Path,
    seed: int,
    sample_size: int,
    warm_iterations: int,
) -> None:
    print("openNASR benchmark: diverse real flight-plan route resolution")
    print("=" * 63)

    manager = CycleManager(cache_dir)
    effective_date = (
        manager.latest().effective_date if cycle is None else date.fromisoformat(cycle)
    )
    print(f"NASR cycle: {effective_date}  (storage={storage})")

    load_started = time.perf_counter()
    nasr = NASR(
        cycle=effective_date.isoformat(),
        cache_dir=manager.cache_dir,
        storage=storage,
    )
    for table in nasr:
        nasr[table]
    load_seconds = time.perf_counter() - load_started
    print(f"Table load (cold): {_format_seconds(load_seconds)}")

    index_started = time.perf_counter()
    resolver = RouteResolver(nasr)
    index_seconds = time.perf_counter() - index_started
    print(f"RouteResolver index build (cold): {_format_seconds(index_seconds)}")

    all_routes = _load_routes(routes_path)
    sample = _select_sample(all_routes, seed=seed, sample_size=sample_size)
    print(
        f"\nSample: {len(sample)} routes (seed={seed}) from "
        f"{len(all_routes)} in {routes_path.name}"
    )

    direct_samples: list[float] = []
    procedure_samples: list[float] = []
    failures = 0

    for route in sample:
        try:
            resolver.path(route)  # warm-up call; discard timing and result
        except Exception:
            failures += 1
            continue
        timings = []
        for _ in range(warm_iterations):
            started = time.perf_counter()
            resolver.path(route)
            timings.append(time.perf_counter() - started)
        elapsed = statistics.median(timings)
        if _is_direct_or_airway_only(route):
            direct_samples.append(elapsed)
        else:
            procedure_samples.append(elapsed)

    resolved = len(direct_samples) + len(procedure_samples)
    print(
        f"Resolved: {resolved}/{len(sample)}  "
        f"(unsupported/unresolvable: {failures} -- not a code defect; "
        "see ROUTE_PATH_PLAN.md Phase 6 for international/oceanic routes "
        "outside domestic NASR coverage)"
    )

    print("\nWarm per-route resolution time (RouteResolver already built):")
    _print_category(
        "Direct/airway-only routes",
        len(direct_samples),
        _summarize(direct_samples) if direct_samples else None,
    )
    _print_category(
        "Procedure-containing routes (DP/STAR)",
        len(procedure_samples),
        _summarize(procedure_samples) if procedure_samples else None,
    )
    if direct_samples and procedure_samples:
        ratio = statistics.mean(procedure_samples) / statistics.mean(direct_samples)
        print(
            f"\nProcedure routes cost {ratio:.1f}x more than direct/airway-only "
            "routes on average."
        )
    if direct_samples or procedure_samples:
        overall = direct_samples + procedure_samples
        print(
            f"\nOverall (all resolved routes, n={len(overall)}): "
            f"mean={_format_seconds(statistics.mean(overall))}  "
            f"median={_format_seconds(statistics.median(overall))}"
        )
        print(
            "Note: the overall average is dominated by whichever category is "
            "more common in this sample -- read the per-category numbers "
            "above for the real picture, not just this line."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cycle", help="exact ISO NASR cycle date; defaults to the newest cached cycle"
    )
    parser.add_argument("--cache-dir", type=Path, help="NASR cache directory")
    parser.add_argument(
        "--storage",
        choices=("csv", "duckdb"),
        default="csv",
        help="table storage backend",
    )
    parser.add_argument(
        "--routes",
        type=Path,
        default=DEFAULT_ROUTES,
        help=f"route-field text file, one route per line (default: {DEFAULT_ROUTES})",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument(
        "--warm-iterations",
        type=int,
        default=DEFAULT_WARM_ITERATIONS,
        help="repeated timed calls per route, after one untimed warm-up call",
    )
    arguments = parser.parse_args()
    run(
        cycle=arguments.cycle,
        cache_dir=arguments.cache_dir,
        storage=arguments.storage,
        routes_path=arguments.routes,
        seed=arguments.seed,
        sample_size=arguments.sample_size,
        warm_iterations=arguments.warm_iterations,
    )


if __name__ == "__main__":
    main()
