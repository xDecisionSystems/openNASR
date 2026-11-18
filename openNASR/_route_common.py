"""Shared constants, small helpers and the context variables of route resolution.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field

from pandas import DataFrame

from .routeresult import RouteDiagnostic

# Airports named at the two ends of the route being resolved. A procedure
# name shared by several airports' records (``VIEWS.DEHAN3``) is narrowed to
# the records that serve one of them.
_ROUTE_AIRPORTS: ContextVar[frozenset[str]] = ContextVar(
    "route_airports", default=frozenset()
)


# Collects diagnostics for partial resolutions while a route is resolved.
_DIAGNOSTICS: ContextVar[list[RouteDiagnostic] | None] = ContextVar(
    "route_diagnostics", default=None
)


_DIRECT = "DCT"


_AIRWAY = re.compile(r"(?P<designation>[A-Z]+)(?P<identifier>[0-9][A-Z0-9]*)$")


_OCEANIC_COORDINATE = re.compile(r"\d{4}[NS]/\d{5}[EW]")


_LATLON_WAYPOINT = re.compile(
    r"(?P<lat>\d{2})(?P<lat_min>\d{2})?(?P<ns>[NS])"
    r"(?P<lon>\d{3})(?P<lon_min>\d{2})?(?P<ew>[EW])$"
)


_SPEED_LEVEL = re.compile(r"[NKM]\d{3,4}(?:[FSAM]\d{3,4}|VFR)$")


_EXTERNAL_AIRWAY = re.compile(r"(?:U[A-Z]?\d+[A-Z0-9]*|RTE\d+)$")


_RADIAL_DISTANCE = re.compile(r"[A-Z]{3}\d{6}$")


_FOREIGN_ICAO_PREFIX = re.compile(r"(?:C[FGKLMNPSY]|E[A-Z]|MM|TJ)[A-Z]{2}$")


@dataclass(frozen=True)
class _Waypoint:
    identifier: str
    latitude: float
    longitude: float
    # Provenance only: two records at one place are the same waypoint.
    kind: str = field(default="", compare=False)


@dataclass(frozen=True)
class _RouteToken:
    """One normalized route token with its offset in the filed route text."""

    value: str
    position: int


@dataclass(frozen=True)
class _ProcedureAirwayJoin:
    """One source-backed DP prefix and its adjacent airway join."""

    prefix: tuple[_Waypoint, ...]
    identifier: str


def _text(value: object) -> str:
    return str(value).strip().upper()


def _row_records(rows: DataFrame) -> list[dict[str, object]]:
    """Convert a (typically small, index-filtered) DataFrame to row dicts.

    Equivalent to ``rows.to_dict(orient="records")`` but several times
    faster: pandas' ``to_dict`` re-boxes every cell through per-column dtype
    machinery, which dominates cost even for a handful of rows, whereas a
    plain object-array pull avoids that per-cell overhead.
    """

    columns = tuple(rows.columns)
    return [dict(zip(columns, values)) for values in rows.to_numpy(dtype=object)]


def _coordinates(row: Mapping[str, object]) -> tuple[float, float] | None:
    latitude = row.get("LAT_DECIMAL")
    longitude = row.get("LONG_DECIMAL")
    if latitude is None or longitude is None:
        return None
    try:
        return float(str(latitude)), float(str(longitude))
    except ValueError:
        return None


_KIND_BY_TABLE = {"APT_BASE": "airport", "FIX_BASE": "fix", "NAV_BASE": "navaid"}


_WAYPOINT_TABLES = (
    ("APT_BASE", ("ARPT_ID", "ICAO_ID")),
    ("FIX_BASE", ("FIX_ID",)),
    ("NAV_BASE", ("NAV_ID",)),
)
