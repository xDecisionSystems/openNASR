"""Entity lookups: the FAA's own rows for an airport, fix, navaid or airway.

Values are source text, exactly as published; empty columns are dropped to keep
responses readable. Every function takes a ``query`` callable with the shape of
``NASR.query_table`` so the logic can be tested without a database.
"""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

from numpy import asarray

from openNASR.arrivals import STAR_KEY
from openNASR.cfcn import xy2ll
from openNASR.departure import DEPARTURE_KEY
from openNASR.exceptions import AmbiguousRecordError, RecordNotFoundError
from openNASR.ils import localizer_true_bearing, localizer_wedge_xy
from openNASR.query import QueryFilter, QueryTableNotFoundError

MAX_ROWS = 5_000
_AIRWAY = re.compile(r"^(?P<designation>[A-Z]+)(?P<identifier>[0-9][A-Z0-9]*)$")


class NotFoundError(LookupError):
    """Raised when nothing in the cycle matches the identifier."""


def _compact(row: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in row.items() if v not in ("", None)}


def _rows(query: Callable[..., Any], table: str, *filters: QueryFilter) -> list[dict]:
    rows: list[dict] = []
    cursor = None
    while True:
        page = query(table, filters=filters, page_size=1000, cursor=cursor)
        rows.extend(_compact(dict(r)) for r in page.rows)
        cursor = page.next_cursor
        if cursor is None or len(rows) >= MAX_ROWS:
            return rows[:MAX_ROWS]


def _position(row: dict[str, str]) -> dict[str, float] | None:
    try:
        return {"lat": float(row["LAT_DECIMAL"]), "lon": float(row["LONG_DECIMAL"])}
    except (KeyError, ValueError):
        return None


def _survey_position(row: dict[str, str]) -> dict[str, float] | None:
    point = _position(row)
    if point and abs(point["lat"]) <= 90 and abs(point["lon"]) <= 180:
        return point
    return None


def _localizers(
    query: Callable[..., Any], site_filters: list[QueryFilter], ends: list[dict]
) -> list[dict]:
    try:
        rows = _rows(query, "ILS_BASE", *site_filters)
    except QueryTableNotFoundError:
        return []
    thresholds: dict[str, list[dict[str, float]]] = {}
    for end in ends:
        point = _survey_position(end)
        if point and (identifier := end.get("RWY_END_ID")):
            thresholds.setdefault(identifier, []).append(point)
    localizers = []
    for row in rows:
        runway_end = row.get("RWY_END_ID")
        position = _survey_position(row)
        candidates = thresholds.get(runway_end, []) if runway_end else []
        wedge = []
        if len(candidates) == 1:
            threshold = candidates[0]
            try:
                x, y = localizer_wedge_xy(0, 0, localizer_true_bearing(row))
            except ValueError:
                pass
            else:
                latitudes, longitudes = xy2ll(
                    asarray(x), asarray(y), llc=(threshold["lat"], threshold["lon"])
                )
                wedge = [
                    {"lat": float(lat), "lon": float((lon + 180) % 360 - 180)}
                    for lat, lon in zip(latitudes, longitudes, strict=True)
                ]
        localizers.append(
            {
                "id": row.get("ILS_LOC_ID"),
                "runway_end": runway_end,
                "position": position,
                "wedge": wedge,
            }
        )
    return localizers


def airport(query: Callable[..., Any], identifier: str) -> dict:
    ident = identifier.strip().upper()
    base = _rows(query, "APT_BASE", QueryFilter.eq("ARPT_ID", ident))
    if not base:
        base = _rows(query, "APT_BASE", QueryFilter.eq("ICAO_ID", ident))
    if not base:
        raise NotFoundError(f"airport {ident} is not in this cycle")
    if len(base) > 1:
        raise NotFoundError(f"airport {ident} matches {len(base)} records")
    site = base[0].get("SITE_NO")
    site_filters = [QueryFilter.eq("SITE_NO", site)] if site else []
    if site_type := base[0].get("SITE_TYPE_CODE"):
        site_filters.append(QueryFilter.eq("SITE_TYPE_CODE", site_type))
    ends = _rows(query, "APT_RWY_END", *site_filters) if site else []
    return {
        "id": base[0].get("ARPT_ID"),
        "icao_id": base[0].get("ICAO_ID"),
        "position": _position(base[0]),
        "base": base[0],
        "runways": _rows(query, "APT_RWY", *site_filters) if site else [],
        "runway_ends": ends,
        "localizers": _localizers(query, site_filters, ends) if site else [],
    }


def fixes(query: Callable[..., Any], identifier: str) -> list[dict]:
    ident = identifier.strip().upper()
    rows = _rows(query, "FIX_BASE", QueryFilter.eq("FIX_ID", ident))
    if not rows:
        raise NotFoundError(f"fix {ident} is not in this cycle")
    return [{"id": r.get("FIX_ID"), "position": _position(r), "base": r} for r in rows]


def navaids(query: Callable[..., Any], identifier: str) -> list[dict]:
    ident = identifier.strip().upper()
    rows = _rows(query, "NAV_BASE", QueryFilter.eq("NAV_ID", ident))
    if not rows:
        raise NotFoundError(f"navaid {ident} is not in this cycle")
    return [
        {
            "id": r.get("NAV_ID"),
            "type": r.get("NAV_TYPE"),
            "position": _position(r),
            "base": r,
        }
        for r in rows
    ]


def airways(query: Callable[..., Any], identifier: str) -> list[dict]:
    """An airway by designation, e.g. ``J74``; FAA data stores it two ways."""

    ident = identifier.strip().upper()
    match = _AIRWAY.match(ident)
    if match is None:
        raise NotFoundError(f"{ident!r} is not an airway designation")
    candidates = _rows(query, "AWY_BASE", QueryFilter.eq("AWY_ID", ident))
    candidates += [
        row
        for row in _rows(
            query, "AWY_BASE", QueryFilter.eq("AWY_ID", match["identifier"])
        )
        if row.get("AWY_DESIGNATION") == match["designation"]
    ]
    if not candidates:
        raise NotFoundError(f"airway {ident} is not in this cycle")
    result = []
    for base in candidates:
        segments = _rows(
            query,
            "AWY_SEG_ALT",
            QueryFilter.eq("AWY_ID", base["AWY_ID"]),
            QueryFilter.eq("REGULATORY", base.get("REGULATORY", "")),
            QueryFilter.eq("AWY_LOCATION", base.get("AWY_LOCATION", "")),
        )
        segments.sort(key=lambda r: int(r.get("POINT_SEQ", "0") or 0))
        result.append({"id": ident, "base": base, "segments": segments})
    return result


def _procedure_rows(query, table, *filters):
    try:
        return _rows(query, table, *filters)
    except QueryTableNotFoundError:
        return []


def _procedures(query, identifier, prefix, keys, code, name):
    ident = identifier.strip().upper()
    table = f"{prefix}_BASE"
    bases = _procedure_rows(query, table, QueryFilter.eq(code, ident))
    if not bases:
        bases = _procedure_rows(query, table, QueryFilter.eq(name, ident))
    stem = re.sub(r"\d+$", "", ident)
    if not bases and stem and stem != ident:
        bases = [
            base
            for base in _procedure_rows(query, table, QueryFilter.eq(name, stem))
            if ident in base.get(code, "").split(".")
        ]
    if not bases:
        raise NotFoundError(f"procedure {ident} is not in this cycle")

    def sequence(value):
        return int(value) if value and value.isdecimal() else 0

    result = []
    for base in bases:
        procedure_id = base.get(code) or ident
        filters = tuple(QueryFilter.eq(column, base.get(column, "")) for column in keys)
        routes = _procedure_rows(query, f"{prefix}_RTE", *filters)
        routes.sort(
            key=lambda row: (
                sequence(row.get("BODY_SEQ")),
                sequence(row.get("POINT_SEQ")),
            )
        )
        result.append(
            {
                "id": procedure_id,
                "name": base.get(name, procedure_id),
                "base": base,
                "airports": _procedure_rows(query, f"{prefix}_APT", *filters),
                "points": routes,
            }
        )
    return result


def arrivals(query: Callable[..., Any], identifier: str) -> list[dict]:
    return _procedures(
        query, identifier, "STAR", STAR_KEY, "STAR_COMPUTER_CODE", "ARRIVAL_NAME"
    )


def departures(query: Callable[..., Any], identifier: str) -> list[dict]:
    return _procedures(
        query, identifier, "DP", DEPARTURE_KEY, "DP_COMPUTER_CODE", "DP_NAME"
    )


def procedure_branches(
    rows: list[dict[str, str]],
    locate: Callable[[str, str], tuple[float, float]],
) -> list[dict]:
    """Keep each published body and transition separate, with ordered positions."""

    branches: dict[tuple[str, str, str, str], list[dict]] = {}
    for row in rows:
        key = (
            row.get("ROUTE_PORTION_TYPE", ""),
            row.get("ROUTE_NAME", ""),
            row.get("BODY_SEQ", ""),
            row.get("TRANSITION_COMPUTER_CODE", ""),
        )
        name = row.get("POINT", "").strip()
        position = None
        issue = None
        if name:
            try:
                lat, lon = locate(name, row.get("POINT_TYPE", ""))
                position = {"lat": lat, "lon": lon}
            except (AmbiguousRecordError, RecordNotFoundError) as error:
                issue = str(error)
        else:
            issue = "No waypoint identifier was published."
        branches.setdefault(key, []).append(
            {
                "name": name,
                "sequence": row.get("POINT_SEQ", ""),
                "position": position,
                "issue": issue,
            }
        )

    return [
        {
            "kind": kind,
            "name": name,
            "sequence": sequence,
            "transition": transition,
            "waypoints": waypoints,
        }
        for (kind, name, sequence, transition), waypoints in branches.items()
    ]
