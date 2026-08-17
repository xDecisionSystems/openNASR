"""Benchmark CSV/DuckDB route resolution with cold and warm timings.

This is an opt-in diagnostic utility.  It loads the selected cycle through
``NASR`` and resolves routes with the public ``RouteResolver`` API; no SQL is
used for route conversion.  A JSON report keeps table loading separate from
path generation and records procedure legs, coordinates, and transition
tokens for every route.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time

from openNASR.flightplan import RouteResolver, _procedure_path, _tokenize_flight_plan
from openNASR.nasr import NASR


ROUTES = {
    "airport_to_airport": "KAAA KBBB",
    "fix_navaid": "KAAA ALPHA NAV KBBB",
    "airway_only": "KAAA ALPHA V1 BRAVO KBBB",
    "dp_to_airway": "KAAA DEP1 V1 BRAVO KBBB",
    "airway_to_star": "KAAA ALPHA V1 BRAVO ARR1 KBBB",
    "dp_and_star": "KAAA DEP1 ALPHA ARR1 KBBB",
}


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]


def _procedure_details(tables, route: str) -> dict[str, object]:
    resolver = RouteResolver(tables)
    tokens = _tokenize_flight_plan(tables, route, resolver=resolver._waypoints)
    procedures = []
    for index, token in enumerate(tokens):
        if "." not in token.value and not token.value[-1:].isdigit():
            continue
        preceding = tokens[index - 1].value if index else None
        following = tokens[index + 1].value if index + 1 < len(tokens) else None
        points = _procedure_path(
            tables,
            token.value,
            resolver=resolver._waypoints,
            preceding_token=preceding,
            following_token=following,
        )
        if points is None:
            continue
        procedures.append(
            {
                "identifier": token.value,
                "transition": "." in token.value,
                "legs": max(0, len(points) - 1),
                "coordinates": [
                    [point.latitude, point.longitude] for point in points
                ],
            }
        )
    return {"procedures": procedures}


def benchmark(
    cycle: str,
    storage: str,
    cache_dir: Path | None,
    repetitions: int,
    warm_iterations: int,
) -> dict[str, object]:
    started = time.perf_counter()
    nasr = NASR(cycle=cycle, cache_dir=cache_dir, storage=storage)
    tables = {name: nasr[name] for name in nasr}
    load_seconds = time.perf_counter() - started
    results = {}
    for name, route in ROUTES.items():
        cold = []
        for _ in range(repetitions):
            started = time.perf_counter()
            resolver = RouteResolver(tables)
            try:
                path = resolver.path(route)
                error = None
            except Exception as raised:  # report unsupported matrix rows, don't stop
                path = None
                error = f"{type(raised).__name__}: {raised}"
            cold.append(time.perf_counter() - started)
        resolver = RouteResolver(tables)
        try:
            path = resolver.path(route)
            error = None
        except Exception as raised:
            path = None
            error = f"{type(raised).__name__}: {raised}"
        warm = []
        for _ in range(warm_iterations):
            started = time.perf_counter()
            try:
                resolver.path(route)
            except Exception:
                pass
            warm.append(time.perf_counter() - started)
        details = _procedure_details(tables, route)
        results[name] = {
            "route": route,
            "cold_seconds": {"median": statistics.median(cold), "p95": _p95(cold)},
            "warm_seconds": {"median": statistics.median(warm), "p95": _p95(warm)},
            "coordinates": path,
            "error": error,
            **details,
        }
    return {
        "cycle": cycle,
        "storage": storage,
        "load_seconds": load_seconds,
        "cold_repetitions": repetitions,
        "warm_iterations": warm_iterations,
        "routes": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle", required=True)
    parser.add_argument("--storage", choices=("csv", "duckdb"), default="csv")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--warm-iterations", type=int, default=20)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = benchmark(
        arguments.cycle,
        arguments.storage,
        arguments.cache_dir,
        arguments.repetitions,
        arguments.warm_iterations,
    )
    serialized = json.dumps(report, indent=2, sort_keys=True)
    if arguments.output:
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
