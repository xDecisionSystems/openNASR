"""Run a route corpus and report the resolution rate.

A corpus is a JSON document holding inline NASR tables and routes with expected
outcomes, so it runs in CI without FAA data:

    {"cycle_date": "...", "tables": {"APT_BASE": [{...}]},
     "routes": [{"id": "x", "route": "KAAA ALPHA KBBB",
                 "expect": {"status": "ok", "points": [[lat, lon], ...]}},
                {"id": "y", "route": "KAAA NOPE",
                 "expect": {"status": "error", "error": "RecordNotFoundError"}}]}

Resolution is deterministic, so each case must match its expectation exactly.
The report carries the resolution rate and every mismatch; ``--min-rate`` makes
the exit status fail when the rate of expectation-matching cases drops.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import pandas as pd

from openNASR.flightplan import RouteResolver

DEFAULT_CORPUS = (
    Path(__file__).parents[1] / "tests" / "fixtures" / "route_corpus" / "synthetic.json"
)


def load_corpus(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    for key in ("cycle_date", "tables", "routes"):
        if key not in document:
            raise ValueError(f"corpus {path} is missing {key!r}")
    ids = [entry["id"] for entry in document["routes"]]
    if len(set(ids)) != len(ids):
        raise ValueError(f"corpus {path} has duplicate route ids")
    return document


def _frames(tables: dict) -> dict[str, pd.DataFrame]:
    return {name: pd.DataFrame(rows) for name, rows in tables.items()}


def _outcome(resolver: RouteResolver, route: str) -> dict:
    try:
        points = resolver.path(route)
    except Exception as error:  # a corpus records every failure mode
        return {"status": "error", "error": type(error).__name__}
    return {"status": "ok", "points": [list(point) for point in points]}


def run_corpus(document: dict) -> dict:
    resolver = RouteResolver(_frames(document["tables"]))
    results = []
    for entry in document["routes"]:
        actual = _outcome(resolver, entry["route"])
        expected = entry["expect"]
        results.append(
            {
                "id": entry["id"],
                "route": entry["route"],
                "expected": expected,
                "actual": actual,
                "matches": actual == expected,
            }
        )
    total = len(results)
    matched = sum(result["matches"] for result in results)
    resolved = sum(result["actual"]["status"] == "ok" for result in results)
    errors = Counter(
        result["actual"]["error"]
        for result in results
        if result["actual"]["status"] == "error"
    )
    return {
        "cycle_date": document["cycle_date"],
        "total": total,
        "resolved": resolved,
        "resolution_rate": resolved / total if total else 1.0,
        "expectation_match_rate": matched / total if total else 1.0,
        "errors": dict(sorted(errors.items())),
        "mismatches": [result for result in results if not result["matches"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", nargs="?", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--min-rate", type=float, default=1.0)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)

    report = run_corpus(load_corpus(arguments.corpus))
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output:
        arguments.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if report["expectation_match_rate"] >= arguments.min_rate else 1


if __name__ == "__main__":
    raise SystemExit(main())
