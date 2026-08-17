"""Deterministic batch validation for the tracked route regression sample.

The default input is the small cycle-pinned JSON fixture, so routine runs do
not require the untracked ``tests/exampleRoutes.csv``.  A full-file run is
explicit opt-in with ``--full-file PATH`` and never writes to that input.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random

from openNASR.flightplan import RouteResolver
from openNASR.nasr import NASR


ROOT = Path(__file__).parents[1]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "route_regressions" / "routes.json"


def load_routes(path: Path) -> tuple[str, list[dict[str, str]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return document["cycle_date"], list(document["routes"])


def select_routes(
    routes: list[dict[str, str]], *, seed: int, sample_size: int | None
) -> list[dict[str, str]]:
    if sample_size is None or sample_size >= len(routes):
        return routes
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative")
    indexes = random.Random(seed).sample(range(len(routes)), sample_size)
    return [routes[index] for index in indexes]


def _category(error: Exception) -> str:
    name = type(error).__name__
    if name == "AmbiguousRecordError":
        return "waypoint ambiguity"
    if name in {"RecordNotFoundError", "TableNotFoundError"}:
        return "missing NASR data"
    if name == "ValueError" and "must have waypoints" in str(error):
        return "malformed input"
    if name == "ValueError":
        return "parser error"
    return name


def validate(
    tables, routes: list[dict[str, str]], *, cycle: str
) -> dict[str, object]:
    resolver = RouteResolver(tables)
    results = []
    for entry in routes:
        route = entry["route"]
        try:
            path = resolver.path(route)
        except Exception as error:  # batch validation records, rather than stops
            results.append(
                {
                    "id": entry.get("id"),
                    "route": route,
                    "expected_category": entry.get("category"),
                    "category": _category(error),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "cycle": cycle,
                }
            )
        else:
            results.append(
                {
                    "id": entry.get("id"),
                    "route": route,
                    "expected_category": entry.get("category"),
                    "category": "success",
                    "coordinates": path,
                    "cycle": cycle,
                }
            )
    counts = Counter(result["category"] for result in results)
    mismatches = sum(
        result.get("expected_category") is not None
        and result["expected_category"] != result["category"]
        for result in results
    )
    return {
        "cycle": cycle,
        "total": len(results),
        "successes": counts.get("success", 0),
        "failures": len(results) - counts.get("success", 0),
        "categories": dict(sorted(counts.items())),
        "category_mismatches": mismatches,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--full-file", type=Path)
    parser.add_argument("--cycle")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--storage", choices=("csv", "duckdb"), default="csv")
    parser.add_argument("--seed", type=int, default=20260514)
    parser.add_argument("--sample-size", type=int)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    if arguments.full_file is not None:
        cycle = arguments.cycle
        if not cycle:
            parser.error("--cycle is required with --full-file")
        routes = [
            {"id": f"row_{index}", "route": line.strip()}
            for index, line in enumerate(
                arguments.full_file.read_text(encoding="utf-8").splitlines()
            )
            if line.strip()
        ]
    else:
        fixture_cycle, routes = load_routes(arguments.fixture)
        cycle = arguments.cycle or fixture_cycle
    routes = select_routes(
        routes, seed=arguments.seed, sample_size=arguments.sample_size
    )
    nasr = NASR(cycle=cycle, cache_dir=arguments.cache_dir, storage=arguments.storage)
    tables = {name: nasr[name] for name in nasr}
    report = validate(tables, routes, cycle=cycle)
    serialized = json.dumps(report, indent=2, sort_keys=True, default=str)
    if arguments.output:
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
