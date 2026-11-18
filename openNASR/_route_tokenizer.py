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
    _RADIAL_DISTANCE,
    _SPEED_LEVEL,
    _RouteToken,
    _text,
)
from ._route_procedures import (
    _is_published_dotted_procedure,
    _procedure_path,
    _ProcedureIndex,
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
    for match in _OCEANIC_COORDINATE.finditer(flight_plan.upper()):
        candidates.append((match.start(), match.group(), "oceanic_coordinate"))
    for match in re.finditer(r"[A-Z0-9]+", flight_plan.upper()):
        token = match.group()
        if _EXTERNAL_AIRWAY.fullmatch(token):
            candidates.append((match.start(), token, "external_route"))
        elif _RADIAL_DISTANCE.fullmatch(token):
            candidates.append((match.start(), token, "radial_distance"))
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
    is speed/altitude information, not geometry.
    """

    procedure_index = procedure_index or _ProcedureIndex(tables)
    normalized: list[_RouteToken] = []
    for field_match in re.finditer(r"\S+", flight_plan.upper()):
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
            if not component:
                if not normalized or normalized[-1].value != _DIRECT:
                    normalized.append(_RouteToken(_DIRECT, position))
                component_offset += 1
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
