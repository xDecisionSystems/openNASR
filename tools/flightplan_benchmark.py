"""Manual relative microbenchmark for flight-plan waypoint indexing.

Run with ``python -m tools.flightplan_benchmark``. This utility generates
synthetic waypoint tables locally and reports a ratio against the previous
record-materializing walk; it deliberately sets no machine-dependent pass/fail
timing threshold.
"""

from __future__ import annotations

import argparse
import statistics
import time

import pandas as pd

from openNASR.flightplan import _WAYPOINT_TABLES, _Waypoint, _WaypointResolver


def _legacy_build(tables: dict[str, pd.DataFrame]) -> None:
    """Reference the pre-T4.1 per-record construction strategy."""

    candidates_by_table: dict[str, dict[str, list[_Waypoint]]] = {}
    for table, columns in _WAYPOINT_TABLES:
        frame = tables[table]
        candidates: dict[str, list[_Waypoint]] = {}
        for row in frame.to_dict(orient="records"):
            for column in columns:
                identifier = str(row.get(column, "")).strip().upper()
                if not identifier:
                    continue
                try:
                    point = _Waypoint(
                        identifier,
                        float(str(row["LAT_DECIMAL"])),
                        float(str(row["LONG_DECIMAL"])),
                    )
                except ValueError:
                    continue
                candidates.setdefault(identifier, []).append(point)
        candidates_by_table[table] = candidates


def _samples(function: object, repetitions: int) -> list[float]:
    values: list[float] = []
    for _ in range(repetitions):
        started = time.perf_counter()
        assert callable(function)
        function()
        values.append(time.perf_counter() - started)
    return values


def _tables(rows: int) -> dict[str, pd.DataFrame]:
    points = pd.DataFrame(
        {
            "FIX_ID": [f"FIX{index}" for index in range(rows)],
            "LAT_DECIMAL": [str(30 + index / 100_000) for index in range(rows)],
            "LONG_DECIMAL": [str(-80 - index / 100_000) for index in range(rows)],
        }
    )
    return {
        "APT_BASE": pd.DataFrame(
            columns=["ARPT_ID", "ICAO_ID", "LAT_DECIMAL", "LONG_DECIMAL"]
        ),
        "FIX_BASE": points,
        "NAV_BASE": pd.DataFrame(columns=["NAV_ID", "LAT_DECIMAL", "LONG_DECIMAL"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--repetitions", type=int, default=5)
    arguments = parser.parse_args()
    tables = _tables(arguments.rows)
    legacy = _samples(lambda: _legacy_build(tables), arguments.repetitions)
    vectorized = _samples(lambda: _WaypointResolver(tables), arguments.repetitions)
    legacy_median = statistics.median(legacy)
    vectorized_median = statistics.median(vectorized)
    print(
        {
            "rows": arguments.rows,
            "repetitions": arguments.repetitions,
            "legacy_median_seconds": legacy_median,
            "vectorized_median_seconds": vectorized_median,
            "speedup_ratio": legacy_median / vectorized_median,
        }
    )


if __name__ == "__main__":
    main()
