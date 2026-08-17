"""Benchmark legacy and modern repository lookups on one loaded NASR cycle."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import random
import statistics
import time

from openNASR.airport import Airport
from openNASR.cycles import CycleManager
from openNASR.fix import FIX
from openNASR.nasr import NASR
from openNASR.nav import NAVAID


def _summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": ordered[min(len(ordered) - 1, int(len(values) * 0.95))],
    }


def _ids(frame, column: str, *, seed: int, count: int) -> list[str]:
    values = [
        str(value).strip() for value in frame[column].tolist() if str(value).strip()
    ]
    unique = list(dict.fromkeys(values))
    return random.Random(seed).sample(unique, min(count, len(unique)))


def _keys(
    frame, columns: tuple[str, ...], *, seed: int, count: int
) -> list[tuple[str, ...]]:
    rows = frame[list(columns)].fillna("").astype(str)
    keys = list(
        dict.fromkeys(tuple(row) for row in rows.itertuples(index=False, name=None))
    )
    complete = [key for key in keys if all(value.strip() for value in key)]
    return random.Random(seed).sample(complete, min(count, len(complete)))


def _measure(function, identifiers: list[str]) -> dict[str, object]:
    cold = []
    warm = []
    for identifier in identifiers:
        started = time.perf_counter()
        try:
            function(identifier)
        except Exception:
            pass
        cold.append(time.perf_counter() - started)
        started = time.perf_counter()
        try:
            function(identifier)
        except Exception:
            pass
        warm.append(time.perf_counter() - started)
    return {
        "count": len(identifiers),
        "cold": _summary(cold),
        "warm": _summary(warm),
    }


def run(
    *, cycle: str | None, cache_dir: Path | None, storage: str, seed: int, count: int
):
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
    fixes = _ids(nasr["FIX_BASE"], "FIX_ID", seed=seed, count=count)
    airports = _ids(nasr["APT_BASE"], "ARPT_ID", seed=seed + 1, count=count)
    navaids = _ids(nasr["NAV_BASE"], "NAV_ID", seed=seed + 2, count=count)
    coded = _ids(nasr["CDR"], "RCode", seed=seed + 3, count=count)
    composite = {
        "location_identifiers_get": (
            nasr.location_identifiers.get,
            _keys(
                nasr["LID"],
                (
                    "COUNTRY_CODE",
                    "LOC_ID",
                    "REGION_CODE",
                    "STATE",
                    "CITY",
                    "LID_GROUP",
                    "FAC_TYPE",
                ),
                seed=seed + 4,
                count=count,
            ),
        ),
        "frequencies_get": (
            nasr.frequencies.get,
            _keys(
                nasr["FRQ"],
                (
                    "FACILITY",
                    "SERVICED_FACILITY",
                    "SERVICED_SITE_TYPE",
                    "SERVICED_STATE",
                    "SERVICED_COUNTRY",
                    "FREQ",
                    "SECTORIZATION",
                    "FREQ_USE",
                ),
                seed=seed + 5,
                count=count,
            ),
        ),
        "preferred_routes_get": (
            nasr.preferred_routes.get,
            _keys(
                nasr["PFR_BASE"],
                ("ORIGIN_ID", "DSTN_ID", "PFR_TYPE_CODE", "ROUTE_NO"),
                seed=seed + 6,
                count=count,
            ),
        ),
        "airways_get": (
            nasr.airways.get,
            _keys(
                nasr["AWY_BASE"],
                ("REGULATORY", "AWY_LOCATION", "AWY_ID"),
                seed=seed + 7,
                count=count,
            ),
        ),
        "holding_patterns_get": (
            nasr.holding_patterns.get,
            _keys(
                nasr["HPF_BASE"],
                ("HP_NAME", "HP_NO", "STATE_CODE", "COUNTRY_CODE"),
                seed=seed + 8,
                count=count,
            ),
        ),
        "military_training_routes_get": (
            nasr.military_training_routes.get,
            _keys(
                nasr["MTR_BASE"],
                ("ROUTE_TYPE_CODE", "ROUTE_ID"),
                seed=seed + 9,
                count=count,
            ),
        ),
        "atc_facilities_get": (
            nasr.atc_facilities.get,
            _keys(
                nasr["ATC_BASE"],
                (
                    "SITE_NO",
                    "SITE_TYPE_CODE",
                    "FACILITY_TYPE",
                    "STATE_CODE",
                    "FACILITY_ID",
                    "CITY",
                    "COUNTRY_CODE",
                ),
                seed=seed + 10,
                count=count,
            ),
        ),
    }
    return {
        "cycle": selected.isoformat(),
        "storage": storage,
        "load_seconds": load_seconds,
        "identifiers": {
            "fix": fixes,
            "airport": airports,
            "navaid": navaids,
            "coded_route": coded,
        },
        "benchmarks": {
            "legacy_FIX": _measure(lambda identifier: FIX(identifier, nasr), fixes),
            "legacy_Airport": _measure(
                lambda identifier: Airport(identifier, nasr), airports
            ),
            "legacy_NAVAID": _measure(
                lambda identifier: NAVAID(identifier, nasr), navaids
            ),
            "nasr_isFix": _measure(nasr.isFix, fixes),
            "nasr_isAirport": _measure(nasr.isAirport, airports),
            "nasr_isNavaid": _measure(nasr.isNavaid, navaids),
            "modern_fixes_get": _measure(nasr.fixes.get, fixes),
            "modern_airport_get": _measure(nasr.airport, airports),
            "modern_navaids_get": _measure(nasr.navaids.get, navaids),
            "coded_departure_find": _measure(nasr.coded_departure_routes.find, coded),
            **{
                name: _measure(function, identifiers)
                for name, (function, identifiers) in composite.items()
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--storage", choices=("csv", "duckdb"), default="csv")
    parser.add_argument("--seed", type=int, default=20260514)
    parser.add_argument("--count", type=int, default=10)
    arguments = parser.parse_args()
    report = run(
        cycle=arguments.cycle,
        cache_dir=arguments.cache_dir,
        storage=arguments.storage,
        seed=arguments.seed,
        count=arguments.count,
    )
    for name, values in report["benchmarks"].items():
        print(name, "cold", values["cold"], "warm", values["warm"])


if __name__ == "__main__":
    main()
