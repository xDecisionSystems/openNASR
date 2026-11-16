"""Whole-cycle data checks run when a cycle is built.

The route resolver relies on FAA ``DP_RTE`` and ``STAR_RTE`` rows being stored
in flight order (a departure from its runway toward its exit, an arrival from
its entry fix toward its runway). Rather than guess the direction per route,
the builder measures it once for the whole cycle and records the verdict in
the artifact's sidecar. A cycle where the FAA changes the convention is then
flagged the day it is built, before any route is resolved against it.
"""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from pandas import DataFrame

ORDER_THRESHOLD = 0.9
"""Share of bodies that must agree for a convention to be declared."""

MIN_BODIES = 20
"""Fewer measurable bodies than this is too little evidence to judge."""

FLIGHT_ORDER = "flight_order"
REVERSED = "reversed"
UNEXPECTED = "unexpected"
INSUFFICIENT = "insufficient_data"

_PROCEDURES = (
    # table, served-airport table, key columns, expected airport end
    ("DP", "DP_RTE", "DP_APT", ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE"), "first"),
    ("STAR", "STAR_RTE", "STAR_APT", ("STAR_COMPUTER_CODE", "ARTCC"), "last"),
)


def _text(value: object) -> str:
    return str(value).strip().upper()


def _coordinates(frames: Mapping[str, DataFrame]) -> dict[str, tuple[float, float]]:
    points: dict[str, tuple[float, float]] = {}
    for table, column in (("FIX_BASE", "FIX_ID"), ("NAV_BASE", "NAV_ID")):
        frame = frames.get(table)
        if frame is None or any(
            c not in frame for c in (column, "LAT_DECIMAL", "LONG_DECIMAL")
        ):
            continue
        for identifier, lat, lon in zip(
            frame[column], frame["LAT_DECIMAL"], frame["LONG_DECIMAL"]
        ):
            try:
                points.setdefault(_text(identifier), (float(lat), float(lon)))
            except (TypeError, ValueError):
                continue
    return points


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], (a[1] - b[1]) * math.cos(math.radians(a[0])))


def _measure(
    frames: Mapping[str, DataFrame],
    points: Mapping[str, tuple[float, float]],
    airports: Mapping[str, tuple[float, float]],
    routes: str,
    served: str,
    keys: tuple[str, ...],
) -> tuple[int, int, int] | None:
    """Return ``(bodies, airport_nearer_first, airport_nearer_last)``."""

    rte, apt = frames.get(routes), frames.get(served)
    needed = (*keys, "ROUTE_PORTION_TYPE", "ROUTE_NAME", "POINT_SEQ", "POINT")
    if rte is None or apt is None:
        return None
    if any(c not in rte for c in needed):
        return None
    if any(c not in apt for c in (*keys, "BODY_NAME", "ARPT_ID")):
        return None
    airport_of: dict[tuple[str, ...], str] = {}
    for *key, body, airport in zip(*(apt[c] for c in (*keys, "BODY_NAME", "ARPT_ID"))):
        airport_of.setdefault((*(_text(k) for k in key), _text(body)), _text(airport))
    bodies: dict[tuple[str, ...], list[tuple[int, str]]] = {}
    for *key, portion, name, seq, point in zip(*(rte[c] for c in needed)):
        if _text(portion) != "BODY":
            continue
        try:
            order = int(str(seq))
        except ValueError:
            continue
        bodies.setdefault((*(_text(k) for k in key), _text(name)), []).append(
            (order, _text(point))
        )
    total = first = last = 0
    for body_key, rows in bodies.items():
        airport = airports.get(airport_of.get(body_key, ""))
        path = [points[p] for _, p in sorted(rows) if p in points]
        if airport is None or len(path) < 3:
            continue
        near_first, near_last = (
            _distance(airport, path[0]),
            _distance(airport, path[-1]),
        )
        if near_first == near_last:
            continue
        total += 1
        first += near_first < near_last
        last += near_last < near_first
    return total, first, last


def check_procedure_order(frames: Mapping[str, DataFrame]) -> dict[str, Any]:
    """Measure whether DP and STAR rows are stored in flight order."""

    points = _coordinates(frames)
    airports: dict[str, tuple[float, float]] = {}
    base = frames.get("APT_BASE")
    if base is not None and all(
        c in base for c in ("ARPT_ID", "LAT_DECIMAL", "LONG_DECIMAL")
    ):
        for identifier, lat, lon in zip(
            base["ARPT_ID"], base["LAT_DECIMAL"], base["LONG_DECIMAL"]
        ):
            try:
                airports[_text(identifier)] = (float(lat), float(lon))
            except (TypeError, ValueError):
                continue
    result: dict[str, Any] = {}
    statuses = []
    for label, routes, served, keys, expected_end in _PROCEDURES:
        measured = _measure(frames, points, airports, routes, served, keys)
        if measured is None or measured[0] < MIN_BODIES:
            result[label.lower()] = {"status": INSUFFICIENT}
            continue
        total, near_first, near_last = measured
        agree, opposite = (
            (near_first, near_last)
            if expected_end == "first"
            else (near_last, near_first)
        )
        if agree / total >= ORDER_THRESHOLD:
            status = FLIGHT_ORDER
        elif opposite / total >= ORDER_THRESHOLD:
            status = REVERSED
        else:
            status = UNEXPECTED
        statuses.append(status)
        result[label.lower()] = {
            "status": status,
            "bodies": total,
            "airport_nearer_first_point": near_first,
            "airport_nearer_last_point": near_last,
        }
    result["status"] = (
        FLIGHT_ORDER
        if statuses and all(s == FLIGHT_ORDER for s in statuses)
        else INSUFFICIENT
        if not statuses
        else next(s for s in statuses if s != FLIGHT_ORDER)
    )
    return result
