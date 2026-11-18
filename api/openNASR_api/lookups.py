"""Entity lookups: the FAA's own rows for an airport, fix, navaid or airway.

Values are source text, exactly as published; empty columns are dropped to keep
responses readable. Every function takes a ``query`` callable with the shape of
``NASR.query_table`` so the logic can be tested without a database.
"""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import Any

from openNASR.query import QueryFilter

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
    return {
        "id": base[0].get("ARPT_ID"),
        "icao_id": base[0].get("ICAO_ID"),
        "position": _position(base[0]),
        "base": base[0],
        "runways": _rows(query, "APT_RWY", QueryFilter.eq("SITE_NO", site))
        if site
        else [],
        "runway_ends": _rows(query, "APT_RWY_END", QueryFilter.eq("SITE_NO", site))
        if site
        else [],
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
