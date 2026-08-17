"""Resolve FAA route-field text into geographic paths.

This module resolves the navigation portion of a filed domestic FAA flight
plan against one loaded NASR cycle. It deliberately does not validate a
flight plan for operational use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError


_DIRECT = "DCT"
_AIRWAY = re.compile(r"(?P<designation>[A-Z]+)(?P<identifier>[0-9][A-Z0-9]*)$")


@dataclass(frozen=True)
class _Waypoint:
    identifier: str
    latitude: float
    longitude: float


def _text(value: object) -> str:
    return str(value).strip().upper()


def _coordinates(row: Mapping[str, object]) -> tuple[float, float] | None:
    latitude = row.get("LAT_DECIMAL")
    longitude = row.get("LONG_DECIMAL")
    if latitude is None or longitude is None:
        return None
    try:
        return float(str(latitude)), float(str(longitude))
    except ValueError:
        return None


_WAYPOINT_TABLES = (
    ("APT_BASE", ("ARPT_ID", "ICAO_ID")),
    ("FIX_BASE", ("FIX_ID",)),
    ("NAV_BASE", ("NAV_ID",)),
)


def _waypoint(
    tables: Mapping[str, DataFrame],
    identifier: str,
    *,
    preferred_tables: tuple[str, ...] = (),
) -> _Waypoint:
    """Resolve one waypoint, applying filed-route position context first."""

    candidates_by_table: dict[str, list[_Waypoint]] = {}
    for table, columns in _WAYPOINT_TABLES:
        frame = tables.get(table)
        if frame is None:
            continue
        candidates: list[_Waypoint] = []
        for row in frame.to_dict(orient="records"):
            if not any(_text(row.get(column, "")) == identifier for column in columns):
                continue
            coordinates = _coordinates(row)
            if coordinates is not None:
                candidates.append(_Waypoint(identifier, *coordinates))

        if candidates:
            candidates_by_table[table] = candidates

    for table in preferred_tables:
        preferred = tuple(dict.fromkeys(candidates_by_table.get(table, ())))
        if len(preferred) == 1:
            return preferred[0]
        if len(preferred) > 1:
            raise AmbiguousRecordError(
                entity_type="Flight-plan waypoint",
                identifier=identifier,
                candidates=preferred,
            )

    unique = tuple(
        dict.fromkeys(
            candidate
            for candidates in candidates_by_table.values()
            for candidate in candidates
        )
    )
    if not unique:
        raise RecordNotFoundError(
            entity_type="Flight-plan waypoint", identifier=identifier
        )
    if len(unique) > 1:
        raise AmbiguousRecordError(
            entity_type="Flight-plan waypoint", identifier=identifier, candidates=unique
        )
    return unique[0]


def _airway_vertices(
    tables: Mapping[str, DataFrame], airway: str, start: str, end: str
) -> tuple[str, ...]:
    match = _AIRWAY.fullmatch(airway)
    if match is None:
        raise ValueError(f"Invalid airway token: {airway!r}")
    base = tables.get("AWY_BASE")
    segments = tables.get("AWY_SEG_ALT")
    if base is None or segments is None:
        raise RecordNotFoundError(entity_type="Airway", identifier=airway)

    matches: list[tuple[str, ...]] = []
    for record in base.to_dict(orient="records"):
        if (
            _text(record.get("AWY_DESIGNATION", "")) != match["designation"]
            or _text(record.get("AWY_ID", "")) != match["identifier"]
        ):
            continue
        key = tuple(
            record.get(column) for column in ("REGULATORY", "AWY_LOCATION", "AWY_ID")
        )
        rows = segments
        for column, value in zip(("REGULATORY", "AWY_LOCATION", "AWY_ID"), key):
            rows = rows[rows[column].map(_text).eq(_text(value))]
        ordered = sorted(
            rows.to_dict(orient="records"), key=lambda row: int(str(row["POINT_SEQ"]))
        )
        vertices: list[str] = []
        for segment in ordered:
            source, destination = (
                _text(segment["FROM_POINT"]),
                _text(segment["TO_POINT"]),
            )
            if not vertices or vertices[-1] != source:
                vertices.append(source)
            vertices.append(destination)
        try:
            start_index = vertices.index(start)
            end_index = vertices.index(end)
        except ValueError:
            continue
        path = vertices[start_index : end_index + 1]
        if start_index > end_index:
            path = list(reversed(vertices[end_index : start_index + 1]))
        matches.append(tuple(path))

    if not matches:
        raise RecordNotFoundError(
            entity_type="Airway path",
            identifier=airway,
            filters={"from": start, "to": end},
        )
    unique = tuple(dict.fromkeys(matches))
    if len(unique) > 1:
        raise AmbiguousRecordError(
            entity_type="Airway path", identifier=airway, candidates=unique
        )
    return unique[0]


def flight_plan_path(
    nasr: Mapping[str, DataFrame], flight_plan: str
) -> tuple[tuple[float, float], ...]:
    """Return the ``(latitude, longitude)`` path for FAA route-field text.

    ``flight_plan`` is the space-separated route field submitted to the FAA,
    for example ``"KBWI DCT AABEE V1 CHARLIE KDCA"``. Airport identifiers,
    fixes, navaids, the ``DCT`` connector, and published airways are resolved
    from ``nasr``. An airway is expanded only between its explicitly filed
    preceding and following waypoints; ambiguous or unknown identifiers raise
    the corresponding public lookup error.

    The returned coordinates are source data, not an operationally validated
    route, and do not account for procedure transitions, altitude restrictions,
    or ATC clearances.
    """

    if not isinstance(flight_plan, str) or not flight_plan.strip():
        raise ValueError("flight_plan must be non-empty FAA route-field text")
    tokens = tuple(_text(token.split("/", 1)[0]) for token in flight_plan.split())
    if not tokens or any(not token for token in tokens):
        raise ValueError("flight_plan must contain route tokens")

    output: list[tuple[float, float]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == _DIRECT:
            index += 1
            continue
        airway = _AIRWAY.fullmatch(token)
        if airway is not None and "AWY_BASE" in nasr:
            if not output or index + 1 >= len(tokens) or tokens[index + 1] == _DIRECT:
                raise ValueError(f"Airway {token!r} must have waypoints on both sides")
            previous = tokens[index - 1]
            following = tokens[index + 1]
            vertices = _airway_vertices(nasr, token, previous, following)
            for identifier in vertices[1:]:
                point = _waypoint(
                    nasr,
                    identifier,
                    preferred_tables=("FIX_BASE", "NAV_BASE", "APT_BASE"),
                )
                output.append((point.latitude, point.longitude))
            index += 2
            continue
        preferred_tables = (
            ("APT_BASE", "FIX_BASE", "NAV_BASE")
            if index in {0, len(tokens) - 1}
            else ("FIX_BASE", "NAV_BASE", "APT_BASE")
        )
        point = _waypoint(nasr, token, preferred_tables=preferred_tables)
        coordinate = point.latitude, point.longitude
        if not output or output[-1] != coordinate:
            output.append(coordinate)
        index += 1
    return tuple(output)


__all__ = ["flight_plan_path"]
