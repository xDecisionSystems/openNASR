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


@dataclass(frozen=True)
class _RouteToken:
    """One normalized route token with its offset in the filed route text."""

    value: str
    position: int


class _WaypointResolver:
    """Build one lossless lookup across the waypoint tables for a route."""

    def __init__(self, tables: Mapping[str, DataFrame]) -> None:
        self._candidates: dict[str, dict[str, list[_Waypoint]]] = {}
        for table, columns in _WAYPOINT_TABLES:
            frame = tables.get(table)
            if frame is None:
                continue
            candidates: dict[str, list[_Waypoint]] = {}
            non_vot_candidates: dict[str, list[_Waypoint]] = {}
            if "LAT_DECIMAL" not in frame or "LONG_DECIMAL" not in frame:
                self._candidates[table] = candidates
                continue
            coordinate_rows = frame[
                frame["LAT_DECIMAL"].notna() & frame["LONG_DECIMAL"].notna()
            ]
            identifiers = tuple(coordinate_rows[column] for column in columns)
            nav_types = (
                coordinate_rows["NAV_TYPE"]
                if "NAV_TYPE" in coordinate_rows
                else ("",) * len(coordinate_rows)
            )
            for values in zip(
                *identifiers,
                coordinate_rows["LAT_DECIMAL"],
                coordinate_rows["LONG_DECIMAL"],
                nav_types,
            ):
                *raw_identifiers, latitude, longitude, nav_type = values
                try:
                    coordinates = float(str(latitude)), float(str(longitude))
                except ValueError:
                    continue
                for raw_identifier in raw_identifiers:
                    identifier = _text(raw_identifier)
                    if not identifier:
                        continue
                    waypoint = _Waypoint(identifier, *coordinates)
                    candidates.setdefault(identifier, []).append(waypoint)
                    if table == "NAV_BASE" and _text(nav_type) != "VOT":
                        non_vot_candidates.setdefault(identifier, []).append(waypoint)
            if table == "NAV_BASE":
                for identifier, operational in non_vot_candidates.items():
                    unique_operational = list(dict.fromkeys(operational))
                    if len(unique_operational) == 1:
                        candidates[identifier] = unique_operational
            self._candidates[table] = candidates

    def resolve(
        self, identifier: str, *, preferred_tables: tuple[str, ...] = ()
    ) -> _Waypoint:
        for table in preferred_tables:
            preferred = tuple(
                dict.fromkeys(self._candidates.get(table, {}).get(identifier, ()))
            )
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
                for candidates in self._candidates.values()
                for candidate in candidates.get(identifier, ())
            )
        )
        if not unique:
            raise RecordNotFoundError(
                entity_type="Flight-plan waypoint", identifier=identifier
            )
        if len(unique) > 1:
            raise AmbiguousRecordError(
                entity_type="Flight-plan waypoint",
                identifier=identifier,
                candidates=unique,
            )
        return unique[0]


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
    resolver: _WaypointResolver | None = None,
) -> _Waypoint:
    """Resolve one waypoint, applying filed-route position context first."""

    if resolver is not None:
        return resolver.resolve(identifier, preferred_tables=preferred_tables)

    candidates_by_table: dict[str, list[_Waypoint]] = {}
    for table, columns in _WAYPOINT_TABLES:
        frame = tables.get(table)
        if frame is None:
            continue
        candidates: list[_Waypoint] = []
        non_vot_candidates: list[_Waypoint] = []
        for row in frame.to_dict(orient="records"):
            if not any(_text(row.get(column, "")) == identifier for column in columns):
                continue
            coordinates = _coordinates(row)
            if coordinates is not None:
                waypoint = _Waypoint(identifier, *coordinates)
                candidates.append(waypoint)
                if table == "NAV_BASE" and _text(row.get("NAV_TYPE", "")) != "VOT":
                    non_vot_candidates.append(waypoint)

        if table == "NAV_BASE":
            unique_operational = list(dict.fromkeys(non_vot_candidates))
            if len(unique_operational) == 1:
                candidates = unique_operational

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
    """Return the published segment path between two filed fixes.

    FAA route tokens print the airway family as an ``AWY_ID`` prefix (for
    example ``Q1``), while ``AWY_DESIGNATION`` is a separate NASR regulatory
    classification (often ``RN`` or ``AT`` for Q/T airways).  The prefix is
    therefore matched through ``AWY_ID``; the regulatory and location fields
    below provide the remaining cycle-specific disambiguation.
    """
    match = _AIRWAY.fullmatch(airway)
    if match is None:
        raise ValueError(f"Invalid airway token: {airway!r}")
    base = tables.get("AWY_BASE")
    segments = tables.get("AWY_SEG_ALT")
    if base is None or segments is None:
        raise RecordNotFoundError(entity_type="Airway", identifier=airway)

    identifiers = {match["identifier"], f"{match['designation']}{match['identifier']}"}
    matching_base = base[base["AWY_ID"].map(_text).isin(identifiers)]
    matches: list[tuple[str, ...]] = []
    for key in matching_base[
        ["REGULATORY", "AWY_LOCATION", "AWY_ID"]
    ].itertuples(index=False, name=None):
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


def _is_published_airway(tables: Mapping[str, DataFrame], airway: str) -> bool:
    """Whether ``airway`` has a matching published airway base record."""

    match = _AIRWAY.fullmatch(airway)
    base = tables.get("AWY_BASE")
    if match is None or base is None:
        return False
    identifiers = {match["identifier"], f"{match['designation']}{match['identifier']}"}
    return base["AWY_ID"].map(_text).isin(identifiers).any()


def _route_rows_points(
    tables: Mapping[str, DataFrame],
    rows: DataFrame,
    *,
    resolver: _WaypointResolver | None = None,
    reverse: bool = False,
) -> tuple[_Waypoint, ...]:
    """Resolve ordered FAA procedure-route rows into coordinate waypoints."""

    records = rows.to_dict(orient="records")
    records.sort(
        key=lambda row: (
            int(str(row.get("BODY_SEQ", "0") or "0")),
            int(str(row.get("POINT_SEQ", "0") or "0")),
        )
    )
    if reverse:
        records.reverse()
    points: list[_Waypoint] = []
    for row in records:
        identifier = _text(row.get("POINT", ""))
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
    resolver: _WaypointResolver | None,
    entity_type: str,
    identifier: str,
) -> tuple[_Waypoint, ...]:
    """Select a published procedure body using its filed route connection."""

    if "ROUTE_NAME" not in rows:
        return _route_rows_points(tables, rows, resolver=resolver, reverse=reverse)
    names = tuple(dict.fromkeys(rows["ROUTE_NAME"].map(_text)))
    candidates = tuple(
        _route_rows_points(
            tables,
            rows[rows["ROUTE_NAME"].map(_text).eq(name)],
            resolver=resolver,
            reverse=reverse,
        )
        for name in names
    )
    if len(candidates) == 1:
        return candidates[0]
    if connection_token is not None:
        matches = tuple(
            candidate
            for candidate in candidates
            if candidate
            and (
                candidate[0].identifier if reverse else candidate[-1].identifier
            )
            == connection_token
        )
        if len(matches) == 1:
            return matches[0]
    common: list[_Waypoint] = []
    for points in zip(*candidates):
        if len(set(points)) != 1:
            break
        common.append(points[0])
    if common:
        return tuple(common)
    raise AmbiguousRecordError(
        entity_type=entity_type,
        identifier=identifier,
        candidates=tuple(
            tuple(point.identifier for point in path) for path in candidates
        ),
    )


def _procedure_path(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    resolver: _WaypointResolver | None = None,
    preceding_token: str | None = None,
    following_token: str | None = None,
) -> tuple[_Waypoint, ...] | None:
    """Expand one FAA departure or arrival procedure/transition token.

    Departure route strings may identify a ``DP_BASE`` record directly or a
    ``DP_RTE`` transition code (for example ``ORCO8.TRM``). Arrival route
    strings normally carry a STAR transition computer code (for example
    ``IOW.LLROY3``), which identifies a branch in ``STAR_RTE``. STAR rows are
    recorded outbound from the terminal route's end, so they are traversed in
    reverse for an inbound flight plan.
    """

    departures = tables.get("DP_BASE")
    departure_routes = tables.get("DP_RTE")
    stars = tables.get("STAR_BASE")
    star_routes = tables.get("STAR_RTE")
    departure_matches = (
        departures[departures["DP_COMPUTER_CODE"].map(_text).eq(token)].to_dict(
            orient="records"
        )
        if departures is not None and departure_routes is not None
        else []
    )
    departure_transition_matches = (
        departure_routes[
            departure_routes["TRANSITION_COMPUTER_CODE"].map(_text).eq(token)
        ].to_dict(orient="records")
        if departure_routes is not None
        and "TRANSITION_COMPUTER_CODE" in departure_routes
        else []
    )
    transition_matches = (
        star_routes[
            star_routes["TRANSITION_COMPUTER_CODE"].map(_text).eq(token)
        ].to_dict(orient="records")
        if star_routes is not None
        else []
    )
    base_matches = (
        stars[stars["STAR_COMPUTER_CODE"].map(_text).eq(token)].to_dict(
            orient="records"
        )
        if stars is not None and star_routes is not None
        else []
    )

    matches = (
        bool(departure_matches)
        + bool(departure_transition_matches)
        + bool(transition_matches or base_matches)
    )
    if matches > 1:
        raise AmbiguousRecordError(
            entity_type="Flight-plan procedure", identifier=token
        )
    if departure_matches:
        assert departure_routes is not None
        if len(departure_matches) != 1:
            raise AmbiguousRecordError(
                entity_type="DepartureProcedure",
                identifier=token,
                candidates=departure_matches,
            )
        record = departure_matches[0]
        rows = departure_routes[
            (departure_routes["DP_NAME"].map(_text).eq(_text(record["DP_NAME"])))
            & (departure_routes["ARTCC"].map(_text).eq(_text(record["ARTCC"])))
            & (
                departure_routes["DP_COMPUTER_CODE"]
                .map(_text)
                .eq(_text(record["DP_COMPUTER_CODE"]))
            )
        ]
        body = (
            rows[rows["ROUTE_PORTION_TYPE"].map(_text).eq("BODY")]
            if "ROUTE_PORTION_TYPE" in rows
            else rows
        )
        return _select_procedure_body(
            tables,
            body,
            connection_token=following_token,
            reverse=False,
            resolver=resolver,
            entity_type="DepartureProcedure",
            identifier=token,
        )
    if departure_transition_matches:
        assert departures is not None
        assert departure_routes is not None
        departure_keys = {
            (
                _text(row["DP_NAME"]),
                _text(row["ARTCC"]),
                _text(row["DP_COMPUTER_CODE"]),
            )
            for row in departure_transition_matches
        }
        if len(departure_keys) != 1:
            raise AmbiguousRecordError(
                entity_type="DepartureProcedure",
                identifier=token,
                candidates=tuple(departure_keys),
            )
        name, artcc, code = next(iter(departure_keys))
        body = departure_routes[
            (departure_routes["DP_NAME"].map(_text).eq(name))
            & (departure_routes["ARTCC"].map(_text).eq(artcc))
            & (departure_routes["DP_COMPUTER_CODE"].map(_text).eq(code))
            & (departure_routes["ROUTE_PORTION_TYPE"].map(_text).eq("BODY"))
        ]
        transition = departure_routes[
            (departure_routes["DP_NAME"].map(_text).eq(name))
            & (departure_routes["ARTCC"].map(_text).eq(artcc))
            & (departure_routes["DP_COMPUTER_CODE"].map(_text).eq(code))
            & (departure_routes["TRANSITION_COMPUTER_CODE"].map(_text).eq(token))
        ]
        transition_points = _route_rows_points(
            tables, transition, resolver=resolver
        )
        body_points = _select_procedure_body(
            tables,
            body,
            connection_token=following_token,
            reverse=False,
            resolver=resolver,
            entity_type="DepartureProcedure",
            identifier=token,
        )
        return transition_points + body_points
    if transition_matches or base_matches:
        assert star_routes is not None
        if transition_matches:
            keys = {
                (_text(row["STAR_COMPUTER_CODE"]), _text(row["ARTCC"]))
                for row in transition_matches
            }
        else:
            keys = {
                (_text(row["STAR_COMPUTER_CODE"]), _text(row["ARTCC"]))
                for row in base_matches
            }
        if len(keys) != 1:
            raise AmbiguousRecordError(
                entity_type="StarProcedure", identifier=token, candidates=tuple(keys)
            )
        code, artcc = next(iter(keys))
        body = star_routes[
            (star_routes["STAR_COMPUTER_CODE"].map(_text).eq(code))
            & (star_routes["ARTCC"].map(_text).eq(artcc))
            & (star_routes["ROUTE_PORTION_TYPE"].map(_text).eq("BODY"))
        ]
        transition = (
            star_routes[
                (star_routes["STAR_COMPUTER_CODE"].map(_text).eq(code))
                & (star_routes["ARTCC"].map(_text).eq(artcc))
                & (star_routes["TRANSITION_COMPUTER_CODE"].map(_text).eq(token))
            ]
            if transition_matches
            else star_routes.iloc[0:0]
        )
        transition_points = _route_rows_points(
            tables, transition, resolver=resolver, reverse=True
        )
        body_points = _select_procedure_body(
            tables,
            body,
            connection_token=preceding_token,
            reverse=True,
            resolver=resolver,
            entity_type="StarProcedure",
            identifier=token,
        )
        return transition_points + body_points
    return None


def _is_published_dotted_procedure(
    tables: Mapping[str, DataFrame], token: str, *, exact_dp_allowed: bool
) -> bool:
    """Whether a dotted token is a published procedure token.

    A dotted DP computer code is retained as a unit only when it is followed
    by a direct connector (or ends the field) and its first component is not
    also a complete DP code. This keeps a filed bare DP plus a following fix
    (for example ``MCRAY2.MCRAY.Q178``) from being swallowed by a
    coincidentally matching composite code.
    """

    for table in ("DP_RTE", "STAR_RTE"):
        routes = tables.get(table)
        if routes is None or "TRANSITION_COMPUTER_CODE" not in routes:
            continue
        if routes["TRANSITION_COMPUTER_CODE"].map(_text).eq(token).any():
            return True
    departure = tables.get("DP_BASE")
    if departure is None or "DP_COMPUTER_CODE" not in departure:
        return False
    first_component = token.split(".", 1)[0]
    computer_codes = departure["DP_COMPUTER_CODE"].map(_text)
    return (
        exact_dp_allowed
        and computer_codes.eq(token).any()
        and not computer_codes.eq(first_component).any()
    )


def _tokenize_flight_plan(
    tables: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    resolver: _WaypointResolver,
) -> tuple[_RouteToken, ...]:
    """Normalize space- or dot-delimited FAA route text into route tokens.

    FAA route strings use a single dot as a component separator and ``..``
    for direct routing. A procedure/transition itself also contains one dot,
    so adjacent components are retained as one token only when they identify
    a published procedure transition or exact DP computer code in the
    selected NASR cycle. A trailing ``/`` field (for example ``KMSP/0354``)
    is speed/altitude information, not geometry.
    """

    normalized: list[_RouteToken] = []
    for field_match in re.finditer(r"\S+", flight_plan.upper()):
        field = field_match.group().split("/", 1)[0]
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
            exact_dp_allowed = (
                index + 2 >= len(components) or not components[index + 2]
            )
            if (
                combined is not None
                and _is_published_dotted_procedure(
                    tables, combined, exact_dp_allowed=exact_dp_allowed
                )
                and _procedure_path(tables, combined, resolver=resolver) is not None
            ):
                normalized.append(_RouteToken(combined, position))
                component_offset += len(component) + 1 + len(components[index + 1])
                index += 2
            else:
                normalized.append(_RouteToken(component, position))
                component_offset += len(component) + 1
                index += 1
    return tuple(normalized)


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
    resolver = _WaypointResolver(nasr)
    tokens = _tokenize_flight_plan(nasr, flight_plan, resolver=resolver)
    if not tokens or any(not token.value for token in tokens):
        raise ValueError("flight_plan must contain route tokens")

    output: list[tuple[float, float]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index].value
        if token == _DIRECT:
            index += 1
            continue
        airway = _AIRWAY.fullmatch(token)
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
        # A bare procedure computer code (for example ``GNDLF3``) can also
        # satisfy the airway lexical pattern.  Resolve procedures first so a
        # published DP/STAR is not incorrectly sent to AWY_BASE lookup.
        procedure = (
            _procedure_path(
                nasr,
                token,
                resolver=resolver,
                preceding_token=preceding_token,
                following_token=following_token,
            )
            if "." in token or airway is not None
            else None
        )
        if procedure is not None:
            for point in procedure:
                coordinate = point.latitude, point.longitude
                if not output or output[-1] != coordinate:
                    output.append(coordinate)
            index += 1
            continue
        if airway is not None and _is_published_airway(nasr, token):
            if (
                not output
                or index + 1 >= len(tokens)
                or tokens[index + 1].value == _DIRECT
            ):
                raise ValueError(f"Airway {token!r} must have waypoints on both sides")
            previous_procedure = _procedure_path(
                nasr, tokens[index - 1].value, resolver=resolver
            )
            following_procedure = _procedure_path(
                nasr, tokens[index + 1].value, resolver=resolver
            )
            previous = (
                previous_procedure[-1].identifier
                if previous_procedure is not None
                else tokens[index - 1].value
            )
            following = (
                following_procedure[0].identifier
                if following_procedure is not None
                else tokens[index + 1].value
            )
            vertices = _airway_vertices(nasr, token, previous, following)
            for identifier in vertices[1:]:
                point = _waypoint(
                    nasr,
                    identifier,
                    preferred_tables=("FIX_BASE", "NAV_BASE", "APT_BASE"),
                    resolver=resolver,
                )
                output.append((point.latitude, point.longitude))
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
        coordinate = point.latitude, point.longitude
        if not output or output[-1] != coordinate:
            output.append(coordinate)
        index += 1
    return tuple(output)


__all__ = ["flight_plan_path"]
