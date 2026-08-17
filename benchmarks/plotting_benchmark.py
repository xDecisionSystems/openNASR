"""Headless benchmark for the public plotting workflows.

Run with ``python -m benchmarks.plotting_benchmark --cycle YYYY-MM-DD``.
Figures are constructed with Matplotlib's ``Agg`` backend and immediately
closed; no PNGs are written.  Table loading, plotting-index construction,
and cold/repeated call timings are reported separately for CSV or DuckDB
storage. Each case owns one fresh index reused by its cold and repeated
measurements (and by all ten airports in the batch case). ``cold`` is the
first plot after that case's index shell is constructed; lazy component builds
are included in the cold timing. ``index_seconds`` captures shell creation.
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
from openNASR.plotting import (
    PlottingIndex,
    plot_airport_procedures,
    plot_airspace,
    plot_flight_plan,
)


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
        manager.latest().effective_date if cycle is None else date.fromisoformat(cycle)
    )
    started = time.perf_counter()
    nasr = NASR(
        cycle=selected.isoformat(), cache_dir=manager.cache_dir, storage=storage
    )
    for table in nasr:
        nasr[table]
    load_seconds = time.perf_counter() - started
    # Build one snapshot for the complete benchmark.  In particular, the
    # repeated airport case must measure reuse of the plotting lookup index,
    # rather than rebuilding all procedure/navigation indexes ten times.
    index_seconds = 0.0

    def new_plotting_index() -> PlottingIndex:
        """Create one lazy index owned by one benchmark case."""

        nonlocal index_seconds
        index_started = time.perf_counter()
        plotting_index = PlottingIndex(nasr)
        index_seconds += time.perf_counter() - index_started
        return plotting_index

    cases = {}
    try:
        artcc = nasr.artccs.get("ZOB")
        boundaries = tuple(
            boundary.getShape
            for boundary in (artcc.high, artcc.low)
            if boundary is not None
        )
        shape = unary_union(boundaries)
        plotting_index = new_plotting_index()
        cases["airspace_zob"] = lambda plotting_index=plotting_index: plot_airspace(
            nasr,
            shape,
            plot_high_airways=True,
            plot_low_airways=True,
            index=plotting_index,
        )
    except Exception as raised:
        airspace_error = raised
        cases["airspace_zob"] = lambda: _raise(airspace_error)
    plotting_index = new_plotting_index()
    cases["airport_atl"] = lambda plotting_index=plotting_index: (
        plot_airport_procedures(nasr, "ATL", index=plotting_index)
    )
    plotting_index = new_plotting_index()
    cases["flightplan_direct"] = lambda plotting_index=plotting_index: plot_flight_plan(
        nasr, "KBWI KDCA", index=plotting_index
    )
    plotting_index = new_plotting_index()
    cases["flightplan_procedure"] = lambda plotting_index=plotting_index: (
        plot_flight_plan(
            nasr,
            "KATL.HAALO3.SARGE..DARED..CORKY..KVPS/0048",
            index=plotting_index,
        )
    )
    airport_ids = ("ATL", "BWI", "DCA", "ORD", "JFK", "LAX", "MIA", "SEA", "SFO", "DEN")
    plotting_index = new_plotting_index()
    cases["airport_procedures_repeated"] = lambda plotting_index=plotting_index: (
        _plot_airports(nasr, airport_ids, plotting_index)
    )

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
        "index_seconds": index_seconds,
        "cold_definition": (
            "first plot after a fresh per-case index shell; lazy component "
            "builds are included"
        ),
        "cases": results,
    }


def _plot_airports(nasr, airport_ids, index):
    figure = None
    axes = None
    for airport_id in airport_ids:
        figure, axes = plot_airport_procedures(nasr, airport_id, axes=axes, index=index)
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
