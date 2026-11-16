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


OUTCOMES = {
    "resolved": "every part of the route resolved exactly",
    "resolved_with_branches": (
        "resolved; a procedure has runway- or configuration-dependent branches, "
        "so only the portion common to all of them is included"
    ),
    "outside_scope": "foreign airports, oceanic coordinates or external routes",
    "not_in_cycle": "a fix, airway, procedure or airport that is not in this cycle",
    "ambiguous": "an identifier names several records and the route does not decide",
    "malformed": "the route text is not a valid route",
}


def _outcome(result) -> str:
    codes = {item.code for item in result.diagnostics}
    if not codes:
        return "resolved"
    if codes == {"procedure_branches"}:
        return "resolved_with_branches"
    if "UnsupportedRouteContentError" in codes:
        return "outside_scope"
    if codes & {"RecordNotFoundError", "TableNotFoundError"}:
        return "not_in_cycle"
    if "AmbiguousRecordError" in codes:
        return "ambiguous"
    return "malformed"


def validate(tables, routes: list[dict[str, str]], *, cycle: str) -> dict[str, object]:
    resolver = RouteResolver(tables)
    results = []
    for entry in routes:
        result = resolver.resolve(entry["route"])
        results.append(
            {
                "id": entry.get("id"),
                "route": entry["route"],
                "outcome": _outcome(result),
                "complete": result.complete,
                "coordinates": result.points,
                "diagnostics": [
                    {"code": item.code, "token": item.token, "message": item.message}
                    for item in result.diagnostics
                ],
                "cycle": cycle,
            }
        )
    counts = Counter(result["outcome"] for result in results)
    usable = counts["resolved"] + counts["resolved_with_branches"]
    return {
        "cycle": cycle,
        "total": len(results),
        "usable": usable,
        "usable_rate": usable / len(results) if results else 1.0,
        "outcomes": {name: counts.get(name, 0) for name in OUTCOMES},
        "outcome_meanings": OUTCOMES,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--full-file", type=Path)
    parser.add_argument("--cycle")
    parser.add_argument("--cache-dir", type=Path)
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
    nasr = NASR(cycle=cycle, cache_dir=arguments.cache_dir)
    tables = {name: nasr[name] for name in nasr}
    report = validate(tables, routes, cycle=cycle)
    serialized = json.dumps(report, indent=2, sort_keys=True, default=str)
    if arguments.output:
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
