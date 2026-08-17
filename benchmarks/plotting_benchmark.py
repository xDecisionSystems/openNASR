"""Headless benchmark for the public plotting workflows.

Run with ``python -m benchmarks.plotting_benchmark --cycle YYYY-MM-DD``.
Figures are constructed with Matplotlib's ``Agg`` backend and immediately
closed; no PNGs are written.  Table loading and cold/repeated call timings
are reported separately for CSV or DuckDB storage.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import statistics
import time

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from shapely.ops import unary_union

from openNASR.cycles import CycleManager
from openNASR.nasr import NASR
from openNASR.plotting import plot_airport_procedures, plot_airspace, plot_flight_plan


def _summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": ordered[min(len(ordered) - 1, int(len(values) * 0.95))],
    }


def _timed(function, repeats: int = 1) -> tuple[dict[str, float], str | None]:
    values = []
    error = None
    for _ in range(repeats):
        started = time.perf_counter()
        try:
            figure, _axes = function()
            plt.close(figure)
        except Exception as raised:
            error = f"{type(raised).__name__}: {raised}"
        values.append(time.perf_counter() - started)
    return _summary(values), error


def run(
    *, cycle: str | None, cache_dir: Path | None, storage: str
) -> dict[str, object]:
    manager = CycleManager(cache_dir)
    selected = (
        manager.latest().effective_date
        if cycle is None
        else date.fromisoformat(cycle)
    )
    started = time.perf_counter()
    nasr = NASR(
        cycle=selected.isoformat(), cache_dir=manager.cache_dir, storage=storage
    )
    for table in nasr:
        nasr[table]
    load_seconds = time.perf_counter() - started

    cases = {}
    try:
        artcc = nasr.artccs.get("ZOB")
        boundaries = tuple(
            boundary.getShape
            for boundary in (artcc.high, artcc.low)
            if boundary is not None
        )
        shape = unary_union(boundaries)
        cases["airspace_zob"] = lambda: plot_airspace(
            nasr, shape, plot_high_airways=True, plot_low_airways=True
        )
    except Exception as raised:
        cases["airspace_zob"] = lambda: (_raise(raised))
    cases["airport_atl"] = lambda: plot_airport_procedures(nasr, "ATL")
    cases["flightplan_direct"] = lambda: plot_flight_plan(nasr, "KBWI KDCA")
    cases["flightplan_procedure"] = lambda: plot_flight_plan(
        nasr, "KATL.HAALO3.SARGE..DARED..CORKY..KVPS/0048"
    )
    airport_ids = (
        "ATL", "BWI", "DCA", "ORD", "JFK", "LAX", "MIA", "SEA", "SFO", "DEN"
    )
    cases["airport_procedures_repeated"] = lambda: _plot_airports(nasr, airport_ids)

    results = {}
    for name, function in cases.items():
        cold, cold_error = _timed(function)
        repeated, repeated_error = _timed(function, repeats=10)
        results[name] = {
            "cold": cold,
            "repeated": repeated,
            "cold_error": cold_error,
            "repeated_error": repeated_error,
        }
    return {
        "cycle": selected.isoformat(),
        "storage": storage,
        "load_seconds": load_seconds,
        "cases": results,
    }


def _plot_airports(nasr, airport_ids):
    figure = None
    axes = None
    for airport_id in airport_ids:
        figure, axes = plot_airport_procedures(nasr, airport_id, axes=axes)
    return figure, axes


def _raise(error):
    raise error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--storage", choices=("csv", "duckdb"), default="csv")
    arguments = parser.parse_args()
    print(
        run(
            cycle=arguments.cycle,
            cache_dir=arguments.cache_dir,
            storage=arguments.storage,
        )
    )


if __name__ == "__main__":
    main()
