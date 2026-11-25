"""Assemble the points of a route and the public RouteResolver.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from pandas import DataFrame

from ._route_airways import _airway_vertices, _AirwayIndex, _is_published_airway
from ._route_common import (
    _AIRWAY,
    _DIAGNOSTICS,
    _DIRECT,
    _ROUTE_AIRPORTS,
    _RouteToken,
    _Waypoint,
)
from ._route_procedure_index import _ProcedureIndex
from ._route_procedures import (
    _departure_airway_join,
    _is_departure_procedure,
    _next_route_token_index,
    _previous_route_token_index,
    _procedure_path,
    _route_end_airports,
)
from ._route_tokenizer import (
    _SKIPPED_IDENTIFIER,
    _recognized_unsupported_content,
    _tokenize_flight_plan,
)
from ._route_waypoints import _waypoint, _WaypointResolver
from .exceptions import (
    AmbiguousRecordError,
    ConfigurationError,
    OpenNASRError,
    RecordNotFoundError,
    UnsupportedRouteContentError,
)
from .icaomessage import IcaoFlightPlan, parse_icao_flight_plan
from .routeresult import RouteDiagnostic, RoutePoint, RouteResult


def _attach_route_diagnostic(
    error: OpenNASRError,
    *,
    flight_plan: str,
    cycle: object | None,
) -> None:
    """Attach stable, compact route context without changing legacy messages."""

    identifier = getattr(error, "identifier", None)
    token = getattr(error, "token", None)
    if token is None and identifier is not None:
        token = str(identifier)
    if token is not None and not hasattr(error, "position"):
        match = re.search(re.escape(token), flight_plan, flags=re.IGNORECASE)
        error.position = match.start() if match is not None else None
    error.token = token
    error.cycle = cycle
    error.route = flight_plan
    error.route_text = flight_plan
    error.failure_type = type(error).__name__


def _procedure_step_coordinates(
    nasr: Mapping[str, DataFrame],
    tokens: tuple[_RouteToken, ...],
    index: int,
    token: str,
    *,
    resolver: _WaypointResolver,
    airway_index: _AirwayIndex | None,
    procedure_index: _ProcedureIndex,
) -> tuple[_Waypoint, ...] | None:
    """Return one procedure token's waypoints, or ``None`` if it is not one.

    A bare procedure computer code (for example ``GNDLF3``) can also satisfy
    the airway lexical pattern.  Callers must try this before falling back to
    airway lookup so a published DP/STAR is not incorrectly sent to
    ``AWY_BASE``.
    """

    airway = _AIRWAY.fullmatch(token)
    if "." not in token and airway is None:
        return None
    preceding_token = next(
        (
            candidate.value
            for candidate in reversed(tokens[:index])
            if candidate.value != _DIRECT
        ),
        None,
    )
    following_token = next(
        (
            candidate.value
            for candidate in tokens[index + 1 :]
            if candidate.value != _DIRECT
        ),
        None,
    )
    procedure = _procedure_path(
        nasr,
        token,
        resolver=resolver,
        procedure_index=procedure_index,
        preceding_token=preceding_token,
        following_token=following_token,
    )
    if procedure is None:
        return None
    join = _departure_airway_join(
        nasr,
        tokens,
        index,
        procedure,
        resolver=resolver,
        airway_index=airway_index,
        procedure_index=procedure_index,
    )
    return tuple(join.prefix if join is not None else procedure)


def _flight_plan_path(
    nasr: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    resolver: _WaypointResolver,
    airway_index: _AirwayIndex | None = None,
    procedure_index: _ProcedureIndex | None = None,
) -> tuple[RoutePoint, ...]:
    """Resolve a route with its end airports available for disambiguation."""

    reset = _ROUTE_AIRPORTS.set(_route_end_airports(flight_plan))
    try:
        return _resolve_route_path(
            nasr,
            flight_plan,
            resolver=resolver,
            airway_index=airway_index,
            procedure_index=procedure_index,
        )
    finally:
        _ROUTE_AIRPORTS.reset(reset)


def _route_point(waypoint: _Waypoint, *, via: str | None, segment: str) -> RoutePoint:
    return RoutePoint(
        lat=waypoint.latitude,
        lon=waypoint.longitude,
        name=waypoint.identifier,
        kind=waypoint.kind,
        via=via,
        segment=segment,
    )


def _append_point(
    output: list[RoutePoint], waypoint: _Waypoint, *, via: str | None, segment: str
) -> None:
    """Append a point unless it repeats the previous coordinate."""

    if output and (output[-1].lat, output[-1].lon) == (
        waypoint.latitude,
        waypoint.longitude,
    ):
        return
    output.append(_route_point(waypoint, via=via, segment=segment))


def _resolve_route_path(
    nasr: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    resolver: _WaypointResolver,
    airway_index: _AirwayIndex | None = None,
    procedure_index: _ProcedureIndex | None = None,
) -> tuple[RoutePoint, ...]:
    """Return the resolved points for FAA route-field text.

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
    procedure_index = procedure_index or _ProcedureIndex(nasr)
    tokens = _tokenize_flight_plan(
        nasr,
        flight_plan,
        resolver=resolver,
        procedure_index=procedure_index,
    )
    if not tokens or any(not token.value for token in tokens):
        raise ValueError("flight_plan must contain route tokens")

    output: list[RoutePoint] = []
    index = 0
    while index < len(tokens):
        token = tokens[index].value
        if token == _DIRECT:
            index += 1
            continue
        procedure_waypoints = _procedure_step_coordinates(
            nasr,
            tokens,
            index,
            token,
            resolver=resolver,
            airway_index=airway_index,
            procedure_index=procedure_index,
        )
        if procedure_waypoints is not None:
            segment = (
                "departure"
                if _is_departure_procedure(nasr, token, procedure_index=procedure_index)
                else "arrival"
            )
            for waypoint in procedure_waypoints:
                _append_point(output, waypoint, via=token, segment=segment)
            index += 1
            continue
        airway = _AIRWAY.fullmatch(token)
        if airway is not None and _is_published_airway(
            nasr, token, airway_index=airway_index
        ):
            previous_index = _previous_route_token_index(tokens, index)
            following_index = _next_route_token_index(tokens, index)
            if not output or previous_index is None or following_index is None:
                raise ValueError(f"Airway {token!r} must have waypoints on both sides")
            previous_procedure = _procedure_path(
                nasr,
                tokens[previous_index].value,
                resolver=resolver,
                procedure_index=procedure_index,
            )
            following_procedure = _procedure_path(
                nasr,
                tokens[following_index].value,
                resolver=resolver,
                procedure_index=procedure_index,
            )
            previous_join = (
                _departure_airway_join(
                    nasr,
                    tokens,
                    previous_index,
                    previous_procedure,
                    resolver=resolver,
                    airway_index=airway_index,
                    procedure_index=procedure_index,
                )
                if previous_procedure
                else None
            )
            previous = (
                previous_join.identifier
                if previous_join is not None
                else previous_procedure[-1].identifier
                if previous_procedure
                else tokens[previous_index].value
            )
            following = (
                following_procedure[0].identifier
                if following_procedure
                else tokens[following_index].value
            )
            vertices = _airway_vertices(
                nasr,
                token,
                previous,
                following,
                airway_index=airway_index,
            )
            for identifier in vertices[1:]:
                point = _waypoint(
                    nasr,
                    identifier,
                    preferred_tables=("FIX_BASE", "NAV_BASE", "APT_BASE"),
                    resolver=resolver,
                )
                output.append(_route_point(point, via=token, segment="enroute"))
            # Process the following token too: normal waypoints are deduplicated
            # below, while a following procedure must contribute its remaining
            # ordered legs beyond the airway connection point.
            index += 1
            continue
        preferred_tables = (
            ("APT_BASE", "FIX_BASE", "NAV_BASE")
            if index in {0, len(tokens) - 1}
            else ("FIX_BASE", "NAV_BASE", "APT_BASE")
        )
        point = _waypoint(
            nasr, token, preferred_tables=preferred_tables, resolver=resolver
        )
        segment = (
            "origin"
            if index == 0
            else "destination"
            if index == len(tokens) - 1
            else "enroute"
        )
        _append_point(output, point, via=None, segment=segment)
        index += 1
    return tuple(output)


ROUTE_TABLES = (
    "APT_BASE",
    "FIX_BASE",
    "NAV_BASE",
    "AWY_BASE",
    "AWY_SEG_ALT",
    "DP_BASE",
    "DP_RTE",
    "DP_APT",
    "STAR_BASE",
    "STAR_RTE",
    "STAR_APT",
)


class _CycleTables(dict):
    """Route tables for one cycle, with what the resolver reads off a facade."""

    def __init__(self, tables, effective_date: str, procedure_order: str | None):
        super().__init__(tables)
        self.effective_date = effective_date
        self.procedure_order = procedure_order


class RouteResolver:
    """Resolve multiple routes against one indexed NASR table snapshot.

    The supplied mapping is copied at construction and waypoint indexes are
    built once. Callers that replace a table or mutate a contained DataFrame
    must construct a new resolver; automatic invalidation is intentionally
    not attempted for mutable pandas inputs.
    """

    @classmethod
    def from_nasr(cls, nasr) -> "RouteResolver":
        """Build a resolver from a ``NASR`` facade, loading only the route tables."""

        available = set(nasr)
        tables = {name: nasr[name] for name in ROUTE_TABLES if name in available}
        return cls(_CycleTables(tables, nasr.effective_date, nasr.procedure_order))

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._cycle = getattr(nasr, "effective_date", None)
        order = getattr(nasr, "procedure_order", None)
        if order not in (None, "flight_order"):
            raise ConfigurationError(
                f"Cycle {self._cycle} stores procedures as {order!r}; the route "
                "resolver only supports flight_order."
            )
        self._nasr = dict(nasr)
        self._waypoints = _WaypointResolver(self._nasr)
        self._airways = _AirwayIndex(self._nasr)
        self._procedures = _ProcedureIndex(self._nasr)

    def path(self, flight_plan: str) -> tuple[tuple[float, float], ...]:
        """Return the source-coordinate path for one FAA route field."""

        return tuple((point.lat, point.lon) for point in self._points(flight_plan))

    def procedure_waypoint(
        self, identifier: str, point_type: str
    ) -> tuple[float, float]:
        """Locate a published procedure point in this resolver's cycle."""

        identifier = identifier.strip().upper()
        point_type = point_type.strip().upper()
        is_navaid = point_type.startswith(("VOR", "NDB")) or point_type in {
            "DME",
            "TACAN",
        }
        preferred = (
            ("NAV_BASE", "FIX_BASE", "APT_BASE")
            if is_navaid
            else ("FIX_BASE", "NAV_BASE", "APT_BASE")
        )
        try:
            point = self._waypoints.resolve(identifier, preferred_tables=preferred)
        except AmbiguousRecordError as error:
            matches = [
                p for p in error.candidates if is_navaid and p.subtype == point_type
            ]
            if len(matches) != 1:
                raise
            point = matches[0]
        return point.latitude, point.longitude

    def _points(self, flight_plan: str) -> tuple[RoutePoint, ...]:

        unsupported = (
            _recognized_unsupported_content(flight_plan, self._waypoints)
            if isinstance(flight_plan, str) and flight_plan.strip()
            else None
        )
        if unsupported is not None:
            token, position, content_type = unsupported
            error = UnsupportedRouteContentError(
                token=token,
                position=position,
                content_type=content_type,
                cycle=self._cycle,
            )
            _attach_route_diagnostic(error, flight_plan=flight_plan, cycle=self._cycle)
            raise error
        try:
            return _flight_plan_path(
                self._nasr,
                flight_plan,
                resolver=self._waypoints,
                airway_index=self._airways,
                procedure_index=self._procedures,
            )
        except OpenNASRError as error:
            _attach_route_diagnostic(error, flight_plan=flight_plan, cycle=self._cycle)
            raise

    def resolve_icao_message(self, message: str) -> tuple[IcaoFlightPlan, RouteResult]:
        """Resolve the route inside an ICAO FPL message.

        Returns what was extracted alongside the result so it can be checked.
        Raises :class:`IcaoMessageError` for a message that is not a usable FPL.
        """

        extracted = parse_icao_flight_plan(message)
        return extracted, self.resolve(extracted.route)

    def resolve(self, flight_plan: str) -> RouteResult:
        """Resolve one route into points plus structured diagnostics.

        Route problems (unknown fix, ambiguity, unsupported content) are
        reported as diagnostics with ``complete`` false rather than raised.
        """

        collected: list[RouteDiagnostic] = []
        skipped: list[RouteDiagnostic] = []
        reset = _DIAGNOSTICS.set(collected)
        text = flight_plan
        try:
            while True:
                try:
                    waypoints = self._points(text)
                    break
                except RecordNotFoundError as error:
                    # An identifier this cycle does not know (a foreign navaid,
                    # a private heliport, an ERAM-only name) is skipped: the
                    # points on either side are joined directly and the route
                    # is reported incomplete, instead of losing all of it.
                    retry = _skip_unknown_identifier(text, error)
                    if retry is None or len(skipped) >= _MAX_SKIPPED_IDENTIFIERS:
                        raise
                    skipped.append(_skipped_diagnostic(error))
                    collected.clear()  # the next attempt reports again
                    text = retry
        except OpenNASRError as error:
            if isinstance(error, ConfigurationError):
                raise
            return RouteResult(
                route=flight_plan,
                cycle=self._cycle,
                points=(),
                diagnostics=(
                    *skipped,
                    *collected,
                    _error_diagnostic(error),
                ),
            )
        except ValueError as error:
            stopped = any(item.code == "unknown_route_portion" for item in collected)
            return RouteResult(
                route=flight_plan,
                cycle=self._cycle,
                points=(),
                diagnostics=(
                    *skipped,
                    *collected,
                    # Nothing before a leading XXX: the gap is the explanation.
                    *(
                        ()
                        if stopped
                        else (
                            RouteDiagnostic(code="MalformedRoute", message=str(error)),
                        )
                    ),
                ),
            )
        finally:
            _DIAGNOSTICS.reset(reset)
        collected = [*skipped, *collected]
        unique = {
            (item.code, item.token, repr(item.detail)): item for item in collected
        }
        return RouteResult(
            route=flight_plan,
            cycle=self._cycle,
            points=tuple((point.lat, point.lon) for point in waypoints),
            diagnostics=tuple(unique.values()),
            waypoints=waypoints,
        )


# Oceanic and foreign routes routinely name many points outside NASR (QFA16
# KLAX-YBBN ends with six Australian names in a row), so the limit is generous.
_MAX_SKIPPED_IDENTIFIERS = 25


def _skip_unknown_identifier(text: str, error: RecordNotFoundError) -> str | None:
    """``text`` with the unknown identifier replaced by a skip marker.

    The replacement keeps every character offset (the marker padded with
    spaces), so later diagnostics still point into the route as filed.
    """

    token = getattr(error, "token", None)
    position = getattr(error, "position", None)
    if not token or position is None:
        return None
    end = position + len(token)
    if text[position:end].upper() != token.upper():
        return None
    if (position and text[position - 1].isalnum()) or (
        end < len(text) and text[end].isalnum()
    ):
        return None  # part of a longer identifier
    replacement = _SKIPPED_IDENTIFIER.ljust(len(token))
    return text[:position] + replacement + text[position + len(token) :]


def _skipped_diagnostic(error: RecordNotFoundError) -> RouteDiagnostic:
    diagnostic = _error_diagnostic(error)
    return RouteDiagnostic(
        code=diagnostic.code,
        message=(
            f"{diagnostic.message}; it was skipped and the points on either side "
            "are joined directly"
        ),
        token=diagnostic.token,
        position=diagnostic.position,
        detail={**diagnostic.detail, "skipped": True},
    )


def _candidate(value: object) -> object:
    """A JSON-safe description of one ambiguity candidate."""

    if isinstance(value, _Waypoint):
        described: dict[str, object] = {
            "name": value.identifier,
            "kind": value.kind,
            "lat": value.latitude,
            "lon": value.longitude,
        }
        if value.subtype:
            described["type"] = value.subtype
        return described
    if isinstance(value, (tuple, list)):
        return [_candidate(item) for item in value]
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def _error_diagnostic(error: OpenNASRError) -> RouteDiagnostic:
    detail: dict[str, object] = {}
    if isinstance(error, AmbiguousRecordError):
        # Hand the caller every candidate so they can choose; the resolver does not.
        detail = {
            "entity_type": error.entity_type,
            "candidates": [_candidate(item) for item in error.candidates],
        }
    return RouteDiagnostic(
        code=type(error).__name__,
        message=str(error),
        token=getattr(error, "token", None),
        position=getattr(error, "position", None),
        detail=detail,
    )


def flight_plan_path(
    nasr: Mapping[str, DataFrame], flight_plan: str
) -> tuple[tuple[float, float], ...]:
    """Return the ``(latitude, longitude)`` path for FAA route-field text.

    For repeated calls against the same tables, prefer :class:`RouteResolver`
    so the waypoint index is built once.
    """

    return RouteResolver(nasr).path(flight_plan)
