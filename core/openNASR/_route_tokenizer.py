"""Turn FAA route text into route tokens and spot unsupported content.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from pandas import DataFrame

from ._route_common import (
    _DIAGNOSTICS,
    _DIRECT,
    _EXTERNAL_AIRWAY,
    _FOREIGN_ICAO_PREFIX,
    _OCEANIC_COORDINATE,
    _SPEED_LEVEL,
    _RouteToken,
    _normalize_nas_route,
    _text,
)
from ._route_procedure_index import _ProcedureIndex
from ._route_procedures import (
    _is_published_dotted_procedure,
    _procedure_path,
)
from ._route_waypoints import _WaypointResolver
from .exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
)
from .routeresult import RouteDiagnostic


def _recognized_unsupported_content(
    flight_plan: str, resolver: _WaypointResolver
) -> tuple[str, int, str] | None:
    """Return the first recognized non-domestic component, without parsing it."""

    candidates: list[tuple[int, str, str]] = []
    flight_plan = _normalize_nas_route(flight_plan.upper())
    # Slashed lat/lon points are normalized above; anything left in that
    # shape is not a valid coordinate.
    for match in _OCEANIC_COORDINATE.finditer(flight_plan):
        candidates.append((match.start(), match.group(), "oceanic_coordinate"))
    for match in re.finditer(r"[A-Z0-9]+", flight_plan):
        token = match.group()
        if _EXTERNAL_AIRWAY.fullmatch(token):
            candidates.append((match.start(), token, "external_route"))
        elif _FOREIGN_ICAO_PREFIX.fullmatch(token):
            try:
                resolver.resolve(token)
            except RecordNotFoundError:
                candidates.append((match.start(), token, "foreign_airport"))
            except AmbiguousRecordError:
                # A domestic NASR match is not foreign merely because its
                # spelling also resembles an ICAO airport identifier.
                pass
    if not candidates:
        return None
    position, token, content_type = min(candidates)
    return token, position, content_type


def _note_ignored(position: int, group: str, *, after: str | None = None) -> None:
    """Report speed/level and time groups the resolver skips (not geometry)."""

    diagnostics = _DIAGNOSTICS.get()
    if diagnostics is None:
        return
    diagnostics.append(
        RouteDiagnostic(
            code="ignored_speed_level",
            message=f"{group!r} is a speed, level or time group; it is ignored.",
            token=group,
            position=position,
            detail={"after": after} if after else {},
            severity="info",
        )
    )


# ERAM writes XXX for a part of the route it does not know.
_UNKNOWN_PORTION = "XXX"
# Written by the resolver in place of an identifier it skipped (not found in
# the cycle); read as a direct connection, without a diagnostic of its own.
_SKIPPED_IDENTIFIER = "~"


def _note_unknown_portion(position: int) -> None:
    """Report an ERAM unknown route portion; the route stops before it."""

    diagnostics = _DIAGNOSTICS.get()
    if diagnostics is None:
        return
    diagnostics.append(
        RouteDiagnostic(
            code="unknown_route_portion",
            message=(
                "XXX marks a part of the route that is not known (ERAM); "
                "the route is shown up to the last point before it."
            ),
            token=_UNKNOWN_PORTION,
            position=position,
            severity="warning",
        )
    )


def _tokenize_flight_plan(
    tables: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    resolver: _WaypointResolver,
    procedure_index: _ProcedureIndex | None = None,
) -> tuple[_RouteToken, ...]:
    """Normalize space- or dot-delimited FAA route text into route tokens.

    FAA route strings use a single dot as a component separator and ``..``
    for direct routing. A procedure/transition itself also contains one dot,
    so adjacent components are retained as one token only when they identify
    a published procedure transition or exact DP computer code in the
    selected NASR cycle. A trailing ``/`` field (for example ``KMSP/0354``)
    is speed/altitude information, not geometry. ERAM route text from FAA
    SWIM (``KORD./.OBK131026..FWA..KSDF/2218``, ``2706N/09216W``) is
    normalized first (see :func:`_normalize_nas_route`).
    """

    procedure_index = procedure_index or _ProcedureIndex(tables)
    normalized: list[_RouteToken] = []
    for field_match in re.finditer(r"\S+", _normalize_nas_route(flight_plan.upper())):
        group = field_match.group()
        field, slash, suffix = group.partition("/")
        if slash and suffix:
            _note_ignored(field_match.start() + len(field) + 1, suffix, after=field)
        if _SPEED_LEVEL.match(field):
            _note_ignored(field_match.start(), field)
            continue
        if not field:
            continue
        components = field.split(".")
        index = 0
        component_offset = 0
        while index < len(components):
            component = _text(components[index])
            position = field_match.start() + component_offset
            if component == _UNKNOWN_PORTION:
                # Nothing after an unknown portion is placed: where the
                # flight rejoins the filed route is not known.
                _note_unknown_portion(position)
                while normalized and normalized[-1].value == _DIRECT:
                    normalized.pop()
                return tuple(normalized)
            if not component or component == _SKIPPED_IDENTIFIER:
                if not normalized or normalized[-1].value != _DIRECT:
                    normalized.append(_RouteToken(_DIRECT, position))
                component_offset += len(component) + 1
                index += 1
                continue
            combined = (
                f"{component}.{_text(components[index + 1])}"
                if index + 1 < len(components) and components[index + 1]
                else None
            )
            if (
                combined is not None
                and _is_published_dotted_procedure(
                    tables, combined, procedure_index=procedure_index
                )
                and _procedure_path(
                    tables,
                    combined,
                    resolver=resolver,
                    procedure_index=procedure_index,
                )
                is not None
            ):
                normalized.append(_RouteToken(combined, position))
                component_offset += len(component) + 1 + len(components[index + 1])
                index += 2
            else:
                normalized.append(_RouteToken(component, position))
                component_offset += len(component) + 1
                index += 1
    return tuple(normalized)
