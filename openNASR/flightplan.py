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


class _WaypointResolver:
    """Build one lossless lookup across the waypoint tables for a route."""

    def __init__(self, tables: Mapping[str, DataFrame]) -> None:
        self._candidates: dict[str, dict[str, list[_Waypoint]]] = {}
        for table, columns in _WAYPOINT_TABLES:
            frame = tables.get(table)
            if frame is None:
                continue
            candidates: dict[str, list[_Waypoint]] = {}
            for row in frame.to_dict(orient="records"):
                coordinates = _coordinates(row)
                if coordinates is None:
                    continue
                for column in columns:
                    identifier = _text(row.get(column, ""))
                    if identifier:
                        candidates.setdefault(identifier, []).append(
                            _Waypoint(identifier, *coordinates)
                        )
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
        if _text(record.get("AWY_DESIGNATION", "")) != match["designation"] or _text(
            record.get("AWY_ID", "")
        ) not in {
            match["identifier"],
            f"{match['designation']}{match['identifier']}",
        }:
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


def _procedure_path(
    tables: Mapping[str, DataFrame],
    token: str,
    *,
    resolver: _WaypointResolver | None = None,
) -> tuple[_Waypoint, ...] | None:
    """Expand one FAA departure or arrival procedure/transition token.

    Departure computer codes (for example ``ORCO8.TRM``) identify a
    ``DP_BASE`` record directly. Arrival route strings normally carry a STAR
    transition computer code (for example ``IOW.LLROY3``), which identifies a
    branch in ``STAR_RTE``. STAR rows are recorded outbound from the terminal
    route's end, so they are traversed in reverse for an inbound flight plan.
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

    matches = bool(departure_matches) + bool(transition_matches or base_matches)
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
        return _route_rows_points(tables, rows, resolver=resolver)
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
        return _route_rows_points(
            tables, transition, resolver=resolver, reverse=True
        ) + _route_rows_points(tables, body, resolver=resolver, reverse=True)
    return None


def _tokenize_flight_plan(
    tables: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    resolver: _WaypointResolver,
) -> tuple[str, ...]:
    """Normalize space- or dot-delimited FAA route text into route tokens.

    FAA route strings use a single dot as a component separator and ``..``
    for direct routing. A procedure/transition itself also contains one dot,
    so adjacent components are greedily retained as one token only when they
    identify a procedure in the selected NASR cycle. A trailing ``/`` field
    (for example ``KMSP/0354``) is speed/altitude information, not geometry.
    """

    normalized: list[str] = []
    for field in flight_plan.upper().split():
        field = field.split("/", 1)[0]
        if not field:
            continue
        components = field.split(".")
        index = 0
        while index < len(components):
            component = _text(components[index])
            if not component:
                if not normalized or normalized[-1] != _DIRECT:
                    normalized.append(_DIRECT)
                index += 1
                continue
            combined = (
                f"{component}.{_text(components[index + 1])}"
                if index + 1 < len(components) and components[index + 1]
                else None
            )
            if (
                combined is not None
                and _procedure_path(tables, combined, resolver=resolver) is not None
            ):
                normalized.append(combined)
                index += 2
            else:
                normalized.append(component)
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
        # A bare procedure computer code (for example ``GNDLF3``) can also
        # satisfy the airway lexical pattern.  Resolve procedures first so a
        # published DP/STAR is not incorrectly sent to AWY_BASE lookup.
        procedure = (
            _procedure_path(nasr, token, resolver=resolver)
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
        if airway is not None and "AWY_BASE" in nasr:
            if not output or index + 1 >= len(tokens) or tokens[index + 1] == _DIRECT:
                raise ValueError(f"Airway {token!r} must have waypoints on both sides")
            previous_procedure = (
                _procedure_path(nasr, tokens[index - 1], resolver=resolver)
                if "." in tokens[index - 1]
                else None
            )
            following_procedure = (
                _procedure_path(nasr, tokens[index + 1], resolver=resolver)
                if "." in tokens[index + 1]
                else None
            )
            previous = (
                previous_procedure[-1].identifier
                if previous_procedure is not None
                else tokens[index - 1]
            )
            following = (
                following_procedure[0].identifier
                if following_procedure is not None
                else tokens[index + 1]
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
