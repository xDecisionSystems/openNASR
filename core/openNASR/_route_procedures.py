"""DP and STAR lookup, body selection and expansion.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from pandas import DataFrame

from ._route_airways import _airway_vertices, _AirwayIndex, _is_published_airway
from ._route_common import (
    _AIRWAY,
    _DIAGNOSTICS,
    _DIRECT,
    _ProcedureAirwayJoin,
    _RouteToken,
    _row_records,
    _text,
    _Waypoint,
)
from ._route_procedure_index import _ProcedureIndex
from ._route_waypoints import _waypoint, _WaypointResolver
from .exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
    RouteConnectivityError,
)
from .routeresult import RouteDiagnostic


def _route_end_airports(flight_plan: str) -> frozenset[str]:
    tokens = re.findall(r"[A-Z0-9]+", re.sub(r"/\S*", "", flight_plan.upper()))
    ends: set[str] = set()
    for token in (tokens[0], tokens[-1]) if tokens else ():
        ends.add(token)
        if len(token) == 4 and token[0] in "KP":
            ends.add(token[1:])
    return frozenset(ends)


def _route_rows_points(
    tables: Mapping[str, DataFrame],
    rows: DataFrame,
    *,
    resolver: _WaypointResolver | None = None,
    reverse: bool = False,
) -> tuple[_Waypoint, ...]:
    """Resolve ordered FAA procedure-route rows into coordinate waypoints."""

    body_seq = (
        rows["BODY_SEQ"].to_numpy(copy=False)
        if "BODY_SEQ" in rows
        else (0,) * len(rows)
    )
    point_seq = (
        rows["POINT_SEQ"].to_numpy(copy=False)
        if "POINT_SEQ" in rows
        else (0,) * len(rows)
    )
    points_column = rows["POINT"].to_numpy(copy=False)
    records = sorted(
        zip(body_seq, point_seq, points_column),
        key=lambda row: (
            int(str(row[0] or "0")),
            int(str(row[1] or "0")),
        ),
    )
    if reverse:
        records.reverse()
    points: list[_Waypoint] = []
    for _, _, raw_point in records:
        identifier = _text(raw_point)
        if not identifier:
            continue
        point = _waypoint(
            tables,
            identifier,
            preferred_tables=("FIX_BASE", "NAV_BASE", "APT_BASE"),
            resolver=resolver,
        )
        if not points or points[-1] != point:
            points.append(point)
    return tuple(points)


def _select_procedure_body(
    tables: Mapping[str, DataFrame],
    rows: DataFrame,
    *,
    connection_token: str | None,
    reverse: bool,
    connection_at_start: bool,
    common_at_start: bool,
    resolver: _WaypointResolver | None,
    entity_type: str,
    identifier: str,
    procedure_index: _ProcedureIndex | None = None,
) -> tuple[_Waypoint, ...]:
    """Select a published procedure body using its filed route connection."""

    if "ROUTE_NAME" not in rows:
        return _route_rows_points(tables, rows, resolver=resolver, reverse=reverse)
    names = tuple(dict.fromkeys(rows["ROUTE_NAME"].map(_text)))
    if procedure_index is not None and len(names) > 1:
        names = procedure_index.narrow_bodies(entity_type, rows, names)
    candidates = tuple(
        _route_rows_points(
            tables,
            rows[rows["ROUTE_NAME"].map(_text).eq(name)],
            resolver=resolver,
            reverse=reverse,
        )
        for name in names
    )
    if not candidates:
        # A published procedure may have transitions but no body points
        # (radar-vector departures); there is simply no body geometry.
        return ()
    if len(candidates) == 1:
        return candidates[0]
    if connection_token is not None:
        matches = tuple(
            candidate
            for candidate in candidates
            if candidate
            and (
                candidate[0].identifier
                if connection_at_start
                else candidate[-1].identifier
            )
            == connection_token
        )
        if len(matches) == 1:
            return matches[0]
        if matches:
            candidates = matches
    common: list[_Waypoint] = []
    ordered_candidates = (
        candidates
        if common_at_start
        else tuple(tuple(reversed(path)) for path in candidates)
    )
    for points in zip(*ordered_candidates):
        if len(set(points)) != 1:
            break
        common.append(points[0])
    diagnostics = _DIAGNOSTICS.get()
    if common or diagnostics is not None:
        if diagnostics is not None:
            shared = len(common)
            branches = sorted(
                {
                    tuple(
                        point.identifier
                        for point in (
                            path[shared:]
                            if common_at_start
                            else path[: len(path) - shared]
                        )
                    )
                    for path in candidates
                }
            )
            split_after = (
                (common[-1] if common_at_start else common[0]).identifier
                if common
                else None
            )
            diagnostics.append(
                RouteDiagnostic(
                    code="procedure_branches",
                    message=(
                        f"{identifier} has {len(candidates)} published branches "
                        "that depend on runway or airport configuration; only "
                        "the portion common to all of them is included."
                    ),
                    token=identifier,
                    detail={
                        "split_after": split_after,
                        "branches": [list(branch) for branch in branches],
                    },
                )
            )
        return tuple(common) if common_at_start else tuple(reversed(common))
    raise AmbiguousRecordError(
        entity_type=entity_type,
        identifier=identifier,
        candidates=tuple(
            tuple(point.identifier for point in path) for path in candidates
        ),
    )


@dataclass(frozen=True)
class _ProcedureTokenMatches:
    """The four independent match categories one procedure token can hit."""

    departure_matches: list[dict[str, object]]
    departure_transition_matches: list[dict[str, object]]
    transition_matches: list[dict[str, object]]
    base_matches: list[dict[str, object]]


def _classify_procedure_token(
    tables: Mapping[str, DataFrame], token: str, procedure_index: _ProcedureIndex
) -> _ProcedureTokenMatches:
    """Return every departure/STAR match category for one procedure token.

    Raises :class:`AmbiguousRecordError` when more than one category
    matches. Each branch preserves the legacy direct-filter ``KeyError`` for
    incomplete synthetic tables by indexing the same missing column the old
    unindexed filter would have touched.
    """

    departures = tables.get("DP_BASE")
    departure_routes = tables.get("DP_RTE")
    stars = tables.get("STAR_BASE")
    star_routes = tables.get("STAR_RTE")
    departure_rows = procedure_index.departure_base(token)
    if departures is not None and departure_routes is not None:
        if departure_rows is None:
            # Retain the old direct-filter KeyError for incomplete synthetic tables.
            departures["DP_COMPUTER_CODE"]
        assert departure_rows is not None
        departure_matches = _row_records(departure_rows)
    else:
        departure_matches = []
    departure_transition_rows = procedure_index.departure_transition(token)
    departure_transition_matches = (
        _row_records(departure_transition_rows)
        if departure_transition_rows is not None
        else []
    )
    transition_rows = procedure_index.star_transition(token)
    transition_matches = (
        _row_records(transition_rows) if transition_rows is not None else []
    )
    if star_routes is not None and transition_rows is None:
        # Retain the old direct-filter KeyError for incomplete synthetic tables.
        star_routes["TRANSITION_COMPUTER_CODE"]
    star_rows = procedure_index.star_base(token)
    if stars is not None and star_routes is not None:
        if star_rows is None:
            # Retain the old direct-filter KeyError for incomplete synthetic tables.
            stars["STAR_COMPUTER_CODE"]
        assert star_rows is not None
        base_matches = _row_records(star_rows)
    else:
        base_matches = []

    matches = (
        bool(departure_matches)
        + bool(departure_transition_matches)
        + bool(transition_matches or base_matches)
    )
    if matches > 1:
        raise AmbiguousRecordError(
            entity_type="Flight-plan procedure", identifier=token
        )
    return _ProcedureTokenMatches(
        departure_matches=departure_matches,
        departure_transition_matches=departure_transition_matches,
        transition_matches=transition_matches,
        base_matches=base_matches,
    )


def _departure_key(row: Mapping[str, object]) -> tuple[str, ...]:
    return (_text(row["DP_NAME"]), _text(row["ARTCC"]), _text(row["DP_COMPUTER_CODE"]))


def _unpublished_departure_exit(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    resolver: _WaypointResolver | None,
) -> tuple[_Waypoint, ...]:
    """Terminal fix of a departure that publishes no body geometry.

    FAA DP computer codes read ``NAME#.FIX``; across a full cycle ``FIX`` is the
    end of the DP's body (or the start of its transitions) for about 90% of the
    DPs that publish geometry, and the DP's airways attach there. A radar-vector
    departure publishes no points at all, so the code's own suffix is the only
    source for where it ends.
    """

    suffix = token.split(".", 1)[1] if "." in token else ""
    if not suffix:
        return ()
    try:
        exit_fix = _waypoint(
            tables,
            _text(suffix),
            preferred_tables=("FIX_BASE", "NAV_BASE", "APT_BASE"),
            resolver=resolver,
        )
    except (RecordNotFoundError, AmbiguousRecordError):
        return ()
    diagnostics = _DIAGNOSTICS.get()
    if diagnostics is not None:
        diagnostics.append(
            RouteDiagnostic(
                code="procedure_geometry_unpublished",
                message=(
                    f"{token} publishes no route points; its terminal fix "
                    f"{exit_fix.identifier} comes from the procedure's code."
                ),
                token=token,
                detail={"terminal_fix": exit_fix.identifier},
                severity="info",
            )
        )
    return (exit_fix,)


def _procedure_path(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    resolver: _WaypointResolver | None = None,
    procedure_index: _ProcedureIndex | None = None,
    preceding_token: str | None = None,
    following_token: str | None = None,
) -> tuple[_Waypoint, ...] | None:
    """Expand one FAA departure or arrival procedure/transition token.

    Departure route strings may identify a ``DP_BASE`` record directly or a
    ``DP_RTE`` transition code (for example ``ORCO8.TRM``). Arrival route
    strings normally carry a STAR transition computer code (for example
    ``IOW.LLROY3``), which identifies a branch in ``STAR_RTE``. FAA
    ``DP_RTE`` and ``STAR_RTE`` rows are recorded in flight order (a DP from
    the runway toward its exit, a STAR from its entry fix toward the
    runway), so they are traversed as stored. A departure's body precedes
    its transition; an arrival's transition precedes its body. This was
    checked against a full cycle: the served airport lies at the first
    point of 1,021 of 1,026 DP bodies and at the last point of 1,179 of
    1,186 STAR bodies.
    """

    departure_routes = tables.get("DP_RTE")
    star_routes = tables.get("STAR_RTE")
    procedure_index = procedure_index or _ProcedureIndex(tables)
    matches = _classify_procedure_token(tables, token, procedure_index)
    departure_matches = matches.departure_matches
    departure_transition_matches = matches.departure_transition_matches
    transition_matches = matches.transition_matches
    base_matches = matches.base_matches
    if departure_matches:
        assert departure_routes is not None
        # Full FAA DP_RTE rows include NEXT_POINT and are sequenced from the
        # terminal exit back toward the airport. Retain historical behavior
        # for sparse, legacy caller-supplied tables that omit that column.
        full_departure_rows = "NEXT_POINT" in departure_routes
        if len(departure_matches) > 1:
            narrowed = procedure_index.narrow_departures(
                {_departure_key(row) for row in departure_matches}
            )
            departure_matches = list(
                row for row in departure_matches if _departure_key(row) in narrowed
            )
        if len(departure_matches) != 1:
            raise AmbiguousRecordError(
                entity_type="DepartureProcedure",
                identifier=token,
                candidates=departure_matches,
            )
        record = departure_matches[0]
        name, artcc, code = (
            record["DP_NAME"],
            record["ARTCC"],
            record["DP_COMPUTER_CODE"],
        )
        rows = procedure_index.departure_route(name, artcc, code)
        if rows is None:
            for column in ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE"):
                departure_routes[column]
        assert rows is not None
        body = (
            procedure_index.departure_body(name, artcc, code)
            if "ROUTE_PORTION_TYPE" in departure_routes
            else rows
        )
        assert body is not None
        body_points = _select_procedure_body(
            tables,
            body,
            connection_token=following_token,
            reverse=False,
            connection_at_start=False,
            common_at_start=False,
            resolver=resolver,
            entity_type="DepartureProcedure",
            identifier=token,
            procedure_index=procedure_index,
        )
        return body_points or _unpublished_departure_exit(
            tables, token, resolver=resolver
        )
    if departure_transition_matches:
        assert departure_routes is not None
        full_departure_rows = "NEXT_POINT" in departure_routes
        departure_keys = procedure_index.narrow_departures(
            {_departure_key(row) for row in departure_transition_matches}
        )
        if len(departure_keys) != 1:
            raise AmbiguousRecordError(
                entity_type="DepartureProcedure",
                identifier=token,
                candidates=tuple(departure_keys),
            )
        name, artcc, code = next(iter(departure_keys))
        body = procedure_index.departure_body(name, artcc, code)
        transition = procedure_index.departure_route_transition(
            name, artcc, code, token
        )
        if body is None or transition is None:
            for column in (
                "DP_NAME",
                "ARTCC",
                "DP_COMPUTER_CODE",
                "ROUTE_PORTION_TYPE",
                "TRANSITION_COMPUTER_CODE",
            ):
                departure_routes[column]
        assert body is not None
        assert transition is not None
        transition_points = _route_rows_points(
            tables, transition, resolver=resolver, reverse=False
        )
        body_points = _select_procedure_body(
            tables,
            body,
            connection_token=(
                transition_points[0].identifier
                if full_departure_rows and transition_points
                else following_token
            ),
            reverse=False,
            connection_at_start=False,
            common_at_start=False,
            resolver=resolver,
            entity_type="DepartureProcedure",
            identifier=token,
            procedure_index=procedure_index,
        )
        return (
            body_points + transition_points
            if full_departure_rows
            else transition_points + body_points
        )
    if transition_matches or base_matches:
        assert star_routes is not None
        if transition_matches:
            keys: set[tuple[str, ...]] = {
                (_text(row["STAR_COMPUTER_CODE"]), _text(row["ARTCC"]))
                for row in transition_matches
            }
        else:
            keys = {
                (_text(row["STAR_COMPUTER_CODE"]), _text(row["ARTCC"]))
                for row in base_matches
            }
        keys = procedure_index.narrow_stars(set(keys))
        if len(keys) != 1:
            raise AmbiguousRecordError(
                entity_type="StarProcedure", identifier=token, candidates=tuple(keys)
            )
        code, artcc = next(iter(keys))
        body = procedure_index.star_body(code, artcc)
        if body is None:
            for column in ("STAR_COMPUTER_CODE", "ARTCC", "ROUTE_PORTION_TYPE"):
                star_routes[column]
        assert body is not None
        transition = (
            procedure_index.star_route_transition(code, artcc, token)
            if transition_matches
            else star_routes.iloc[0:0]
        )
        if transition is None:
            for column in ("STAR_COMPUTER_CODE", "ARTCC", "TRANSITION_COMPUTER_CODE"):
                star_routes[column]
        assert transition is not None
        transition_points = _route_rows_points(
            tables, transition, resolver=resolver, reverse=False
        )
        body_points = _select_procedure_body(
            tables,
            body,
            connection_token=preceding_token,
            reverse=False,
            connection_at_start=True,
            common_at_start=True,
            resolver=resolver,
            entity_type="StarProcedure",
            identifier=token,
            procedure_index=procedure_index,
        )
        return transition_points + body_points
    if "." in token:
        return _star_mid_join(
            tables, token, resolver=resolver, procedure_index=procedure_index
        )
    return _star_by_short_name(
        tables,
        token,
        resolver=resolver,
        procedure_index=procedure_index,
        preceding_token=preceding_token,
    )


def _star_by_short_name(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    resolver: _WaypointResolver | None,
    procedure_index: _ProcedureIndex,
    preceding_token: str | None,
) -> tuple[_Waypoint, ...] | None:
    """Expand a STAR filed by its short name when its code is ``ENTRY.NAME``.

    ERAM amended routes (FAA SWIM SFDPS) may file ``..ROKNN4.CGF`` for the
    STAR whose computer code is ``ROKNN.ROKNN4``, often after an unknown
    portion (``XXX``). If the preceding point lies on the STAR, the STAR is
    joined there (as ``FIX.NAME``); otherwise it is flown from its body.
    """

    keys = procedure_index.narrow_stars(procedure_index.stars_named(token))
    if not keys:
        return None
    if len(keys) != 1:
        raise AmbiguousRecordError(
            entity_type="StarProcedure", identifier=token, candidates=tuple(keys)
        )
    code, artcc = next(iter(keys))
    if preceding_token and procedure_index.stars_joined_at(preceding_token, token):
        joined = _star_mid_join(
            tables,
            f"{preceding_token}.{token}",
            resolver=resolver,
            procedure_index=procedure_index,
        )
        if joined:
            return (
                joined[1:] if joined[0].identifier == _text(preceding_token) else joined
            )
    body = procedure_index.star_body(code, artcc)
    if body is None or body.empty:
        return None
    return _select_procedure_body(
        tables,
        body,
        connection_token=None,
        reverse=False,
        connection_at_start=True,
        common_at_start=True,
        resolver=resolver,
        entity_type="StarProcedure",
        identifier=token,
        procedure_index=procedure_index,
    )


def _star_mid_join(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    resolver: _WaypointResolver | None,
    procedure_index: _ProcedureIndex,
) -> tuple[_Waypoint, ...] | None:
    """Expand ``FIX.STAR`` where FIX lies inside a STAR transition or body.

    ERAM amended routes (FAA SWIM SFDPS) join an arrival at the fix the
    aircraft was cleared to, which is often not the first fix of a published
    transition (``SCHUL.OZZZI2``: SCHUL is the third fix of the FLASK
    transition). The path is that transition from the fix onward, then the
    body; a fix on the body itself starts the body there. Several STARs or
    transitions with different remaining paths are ambiguous.
    """

    point, _, name = token.partition(".")
    if not point or not name or "." in name:
        return None
    keys = procedure_index.narrow_stars(
        set(procedure_index.stars_joined_at(point, name))
    )
    if not keys:
        return None
    if len(keys) != 1:
        raise AmbiguousRecordError(
            entity_type="StarProcedure", identifier=token, candidates=tuple(keys)
        )
    code, artcc = next(iter(keys))
    point = _text(point)
    paths: list[tuple[_Waypoint, ...]] = []
    transitions = procedure_index.star_transitions(code, artcc)
    body = procedure_index.star_body(code, artcc)
    if transitions is not None and not transitions.empty:
        column = (
            "TRANSITION_COMPUTER_CODE"
            if "TRANSITION_COMPUTER_CODE" in transitions
            else "ROUTE_NAME"
        )
        for _, rows in transitions.groupby(transitions[column].map(_text), sort=False):
            points = _route_rows_points(tables, rows, resolver=resolver)
            ids = [p.identifier for p in points]
            if point not in ids:
                continue
            remaining = points[ids.index(point) :]
            body_points = (
                _select_procedure_body(
                    tables,
                    body,
                    connection_token=points[-1].identifier,
                    reverse=False,
                    connection_at_start=True,
                    common_at_start=True,
                    resolver=resolver,
                    entity_type="StarProcedure",
                    identifier=token,
                    procedure_index=procedure_index,
                )
                if body is not None and not body.empty
                else ()
            )
            path = remaining + tuple(
                p for i, p in enumerate(body_points) if i or p != remaining[-1]
            )
            if path not in paths:
                paths.append(path)
    if not paths and body is not None and not body.empty:
        body_points = _select_procedure_body(
            tables,
            body,
            connection_token=point,
            reverse=False,
            connection_at_start=True,
            common_at_start=True,
            resolver=resolver,
            entity_type="StarProcedure",
            identifier=token,
            procedure_index=procedure_index,
        )
        ids = [p.identifier for p in body_points]
        if point in ids:
            paths.append(body_points[ids.index(point) :])
    if not paths:
        return None
    if len(paths) > 1:
        raise AmbiguousRecordError(
            entity_type="StarProcedure",
            identifier=token,
            candidates=tuple(tuple(p.identifier for p in path) for path in paths),
        )
    return paths[0]


def _is_departure_procedure(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    procedure_index: _ProcedureIndex | None = None,
) -> bool:
    """Whether ``token`` selects a departure record or transition."""

    procedure_index = procedure_index or _ProcedureIndex(tables)
    departure_matches = procedure_index.departure_base(token)
    transition_matches = procedure_index.departure_transition(token)
    return bool(
        (departure_matches is not None and not departure_matches.empty)
        or (transition_matches is not None and not transition_matches.empty)
    )


def _next_route_token_index(tokens: tuple[_RouteToken, ...], index: int) -> int | None:
    """Return the next non-direct token index after ``index``."""

    for candidate_index in range(index + 1, len(tokens)):
        if tokens[candidate_index].value != _DIRECT:
            return candidate_index
    return None


def _previous_route_token_index(
    tokens: tuple[_RouteToken, ...], index: int
) -> int | None:
    """Return the previous non-direct token index before ``index``."""

    for candidate_index in range(index - 1, -1, -1):
        if tokens[candidate_index].value != _DIRECT:
            return candidate_index
    return None


def _departure_airway_join(
    tables: Mapping[str, DataFrame],
    tokens: tuple[_RouteToken, ...],
    procedure_token_index: int,
    procedure: tuple[_Waypoint, ...],
    *,
    resolver: _WaypointResolver,
    airway_index: _AirwayIndex | None,
    procedure_index: _ProcedureIndex | None = None,
) -> _ProcedureAirwayJoin | None:
    """Find the one explicitly filed join from a DP to its next airway.

    This deliberately considers only an immediately following (allowing DCT)
    published airway and its next filed endpoint. It never uses coordinate
    proximity or later route text to make a connection.
    """

    if not procedure:
        return None  # a procedure with no geometry cannot be joined to an airway
    procedure_token = tokens[procedure_token_index].value
    airway_index_in_route = _next_route_token_index(tokens, procedure_token_index)
    if airway_index_in_route is None or not _is_departure_procedure(
        tables, procedure_token, procedure_index=procedure_index
    ):
        return None
    airway_token = tokens[airway_index_in_route].value
    if not _is_published_airway(tables, airway_token, airway_index=airway_index):
        return None
    endpoint_index = _next_route_token_index(tokens, airway_index_in_route)
    if endpoint_index is None:
        return None
    following_token = tokens[endpoint_index].value
    if _AIRWAY.fullmatch(following_token) is not None:
        return None
    if (
        _procedure_path(
            tables,
            following_token,
            resolver=resolver,
            procedure_index=procedure_index,
        )
        is not None
    ):
        return None

    # Confirm this is a real filed endpoint before classifying failed joins as
    # connectivity instead of a normal missing-waypoint lookup.
    _waypoint(
        tables,
        following_token,
        preferred_tables=("FIX_BASE", "NAV_BASE", "APT_BASE"),
        resolver=resolver,
    )
    try:
        _airway_vertices(
            tables,
            airway_token,
            procedure[-1].identifier,
            following_token,
            airway_index=airway_index,
        )
    except RecordNotFoundError:
        pass
    else:
        # A complete DP already forms a faithful published join; truncation is
        # solely the narrow remedy for an otherwise incompatible suffix.
        return None
    explicitly_named = set(procedure_token.split("."))
    named_points = tuple(
        point for point in procedure if point.identifier in explicitly_named
    )
    if not named_points:
        return None
    joins: dict[str, _ProcedureAirwayJoin] = {}
    for point_index, point in enumerate(procedure):
        if point not in named_points:
            continue
        try:
            _airway_vertices(
                tables,
                airway_token,
                point.identifier,
                following_token,
                airway_index=airway_index,
            )
        except RecordNotFoundError:
            continue
        joins.setdefault(
            point.identifier,
            _ProcedureAirwayJoin(procedure[: point_index + 1], point.identifier),
        )
    if len(joins) == 1:
        return next(iter(joins.values()))
    candidate_joins = tuple(joins)
    if len(candidate_joins) > 1:
        raise AmbiguousRecordError(
            entity_type="Procedure-airway join",
            identifier=f"{procedure_token} -> {airway_token}",
            candidates=candidate_joins,
        )
    named_identifiers = tuple(dict.fromkeys(point.identifier for point in named_points))
    raise RouteConnectivityError(
        entity_type="Procedure-airway join",
        identifier=f"{procedure_token} -> {airway_token}",
        from_identifier=procedure[-1].identifier if procedure else None,
        to_identifier=following_token,
        cycle=None,
        procedure_identifier=procedure_token,
        airway_identifier=airway_token,
        filed_join_identifier=(
            named_identifiers[0] if len(named_identifiers) == 1 else None
        ),
        following_identifier=following_token,
        candidate_joins=named_identifiers,
    )


def _is_published_dotted_procedure(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    procedure_index: _ProcedureIndex | None = None,
) -> bool:
    """Whether a dotted token is a published procedure token.

    A dotted DP computer code is retained as a unit only when its first
    component is not also a complete DP code on its own. This keeps a filed
    bare DP plus a following fix (for example ``MCRAY2.MCRAY.Q178``, where
    ``MCRAY2`` alone is a published DP) from being swallowed by a
    coincidentally matching composite code. Unlike that ambiguous case, an
    exact composite ``DP_COMPUTER_CODE`` (for example a real
    ``MCRAY2.MCRAY`` DP with no standalone ``MCRAY2`` code) must merge
    regardless of what else follows it in the same unspaced field, since FAA
    route text routinely dot-chains a DP directly into a following airway or
    fix with no separating space (for example
    ``MCRAY2.MCRAY.Q178.LEJOY.DEMME5``).
    """

    procedure_index = procedure_index or _ProcedureIndex(tables)
    for matches in (
        procedure_index.departure_transition(token),
        procedure_index.star_transition(token),
    ):
        if matches is not None and not matches.empty:
            return True
    point, _, name = token.partition(".")
    if point and name and procedure_index.stars_joined_at(point, name):
        # FIX.STAR joining an arrival inside a transition (ERAM routes).
        return True
    first_component = token.split(".", 1)[0]
    star_matches = procedure_index.star_base(token)
    if star_matches is not None and not star_matches.empty:
        first_star = procedure_index.star_base(first_component)
        if first_star is None or first_star.empty:
            return True
    departure_matches = procedure_index.departure_base(token)
    if departure_matches is None:
        return False
    first_component_matches = procedure_index.departure_base(first_component)
    assert first_component_matches is not None
    return not departure_matches.empty and first_component_matches.empty
