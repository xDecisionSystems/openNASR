"""Resolve FAA route-field text into geographic paths.

This module resolves the navigation portion of a filed domestic FAA flight
plan against one loaded NASR cycle. It deliberately does not validate a
flight plan for operational use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re

from numpy import ndarray
from pandas import DataFrame

from .exceptions import (
    AmbiguousRecordError,
    OpenNASRError,
    RecordNotFoundError,
    RouteConnectivityError,
    UnsupportedRouteContentError,
)


_DIRECT = "DCT"
_AIRWAY = re.compile(r"(?P<designation>[A-Z]+)(?P<identifier>[0-9][A-Z0-9]*)$")
_OCEANIC_COORDINATE = re.compile(r"\d{4}[NS]/\d{5}[EW]")
_EXTERNAL_AIRWAY = re.compile(r"(?:U[A-Z]?\d+[A-Z0-9]*|RTE\d+)$")
_RADIAL_DISTANCE = re.compile(r"[A-Z]{3}\d{6}$")
_FOREIGN_ICAO_PREFIX = re.compile(r"(?:C[FGKLMNPSY]|E[A-Z]|MM|TJ)[A-Z]{2}$")


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


@dataclass(frozen=True)
class _ProcedureAirwayJoin:
    """One source-backed DP prefix and its adjacent airway join."""

    prefix: tuple[_Waypoint, ...]
    identifier: str


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
            identifiers = tuple(
                coordinate_rows[column].to_numpy(copy=False) for column in columns
            )
            nav_types = (
                coordinate_rows["NAV_TYPE"].to_numpy(copy=False)
                if "NAV_TYPE" in coordinate_rows
                else ("",) * len(coordinate_rows)
            )
            for values in zip(
                *identifiers,
                coordinate_rows["LAT_DECIMAL"].to_numpy(copy=False),
                coordinate_rows["LONG_DECIMAL"].to_numpy(copy=False),
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


class _AirwayIndex:
    """Snapshot the normalized AWY_BASE/AWY_SEG_ALT lookups used by one route
    session.

    ``AWY_SEG_ALT`` (the largest airway table) is indexed once by the same
    ``(REGULATORY, AWY_LOCATION, AWY_ID)`` triplet ``_airway_vertices``
    filters on, so expanding an airway never re-scans the full segment table.
    """

    def __init__(self, tables: Mapping[str, DataFrame]) -> None:
        self._base = tables.get("AWY_BASE")
        self._identifiers = (
            self._base["AWY_ID"].map(_text) if self._base is not None else None
        )
        self._segments = tables.get("AWY_SEG_ALT")
        self._segment_keys = self._segment_positions(self._segments)

    @staticmethod
    def _segment_positions(
        segments: DataFrame | None,
    ) -> dict[tuple[str, str, str], ndarray] | None:
        columns = ("REGULATORY", "AWY_LOCATION", "AWY_ID")
        if segments is None or any(column not in segments for column in columns):
            return None
        normalized = [segments[column].map(_text) for column in columns]
        return segments.groupby(normalized, sort=False).indices

    def matching(self, airway: str) -> DataFrame | None:
        match = _AIRWAY.fullmatch(airway)
        if match is None or self._base is None or self._identifiers is None:
            return None
        identifiers = {
            match["identifier"],
            f"{match['designation']}{match['identifier']}",
        }
        return self._base[self._identifiers.isin(identifiers)]

    def is_published(self, airway: str) -> bool:
        matches = self.matching(airway)
        return matches is not None and not matches.empty

    def segments(self, key: tuple[object, object, object]) -> DataFrame | None:
        """Return ``AWY_SEG_ALT`` rows for one ``(REGULATORY, AWY_LOCATION,
        AWY_ID)`` key, without re-scanning the full table."""

        if self._segments is None or self._segment_keys is None:
            return None
        regulatory, location, identifier = key
        positions = self._segment_keys.get(
            (_text(regulatory), _text(location), _text(identifier))
        )
        return self._segments.iloc[positions] if positions is not None else None


class _ProcedureIndex:
    """Snapshot normalized procedure-table lookups for one route session.

    The position arrays retain each source table's ordering without eagerly
    materializing a DataFrame per procedure code.  The index is deliberately
    not threaded into procedure resolution until T4.2, so this class has no
    effect on current matching or error behavior by itself.
    """

    def __init__(self, tables: Mapping[str, DataFrame]) -> None:
        self._departures = tables.get("DP_BASE")
        self._departure_routes = tables.get("DP_RTE")
        self._stars = tables.get("STAR_BASE")
        self._star_routes = tables.get("STAR_RTE")
        self._departure_codes = self._positions(self._departures, "DP_COMPUTER_CODE")
        self._departure_transitions = self._positions(
            self._departure_routes, "TRANSITION_COMPUTER_CODE"
        )
        self._star_codes = self._positions(self._stars, "STAR_COMPUTER_CODE")
        self._star_transitions = self._positions(
            self._star_routes, "TRANSITION_COMPUTER_CODE"
        )
        self._departure_route_keys = self._composite_positions(
            self._departure_routes, ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
        )
        self._departure_bodies = self._composite_positions(
            self._departure_routes,
            ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE", "ROUTE_PORTION_TYPE"),
        )
        self._departure_route_transitions = self._composite_positions(
            self._departure_routes,
            (
                "DP_NAME",
                "ARTCC",
                "DP_COMPUTER_CODE",
                "TRANSITION_COMPUTER_CODE",
            ),
        )
        self._star_bodies = self._composite_positions(
            self._star_routes,
            ("STAR_COMPUTER_CODE", "ARTCC", "ROUTE_PORTION_TYPE"),
        )
        self._star_route_transitions = self._composite_positions(
            self._star_routes,
            ("STAR_COMPUTER_CODE", "ARTCC", "TRANSITION_COMPUTER_CODE"),
        )

    @staticmethod
    def _positions(frame: DataFrame | None, column: str) -> dict[str, ndarray] | None:
        if frame is None or column not in frame:
            return None
        return frame.groupby(frame[column].map(_text), sort=False).indices

    @staticmethod
    def _matching(
        frame: DataFrame | None,
        positions: dict[str, ndarray] | None,
        token: str,
    ) -> DataFrame | None:
        if frame is None or positions is None:
            return None
        matches = positions.get(_text(token))
        return frame.iloc[matches] if matches is not None else frame.iloc[0:0]

    @staticmethod
    def _composite_positions(
        frame: DataFrame | None, columns: tuple[str, ...]
    ) -> dict[tuple[str, ...], ndarray] | None:
        if frame is None or any(column not in frame for column in columns):
            return None
        normalized = [frame[column].map(_text) for column in columns]
        return frame.groupby(normalized, sort=False).indices

    @staticmethod
    def _matching_composite(
        frame: DataFrame | None,
        positions: dict[tuple[str, ...], ndarray] | None,
        values: tuple[object, ...],
    ) -> DataFrame | None:
        if frame is None or positions is None:
            return None
        matches = positions.get(tuple(_text(value) for value in values))
        return frame.iloc[matches] if matches is not None else frame.iloc[0:0]

    def departure_base(self, token: str) -> DataFrame | None:
        return self._matching(self._departures, self._departure_codes, token)

    def departure_transition(self, token: str) -> DataFrame | None:
        return self._matching(
            self._departure_routes, self._departure_transitions, token
        )

    def star_base(self, token: str) -> DataFrame | None:
        return self._matching(self._stars, self._star_codes, token)

    def star_transition(self, token: str) -> DataFrame | None:
        return self._matching(self._star_routes, self._star_transitions, token)

    def departure_route(
        self, name: object, artcc: object, code: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._departure_routes, self._departure_route_keys, (name, artcc, code)
        )

    def departure_body(
        self, name: object, artcc: object, code: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._departure_routes,
            self._departure_bodies,
            (name, artcc, code, "BODY"),
        )

    def departure_route_transition(
        self, name: object, artcc: object, code: object, transition: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._departure_routes,
            self._departure_route_transitions,
            (name, artcc, code, transition),
        )

    def star_body(self, code: object, artcc: object) -> DataFrame | None:
        return self._matching_composite(
            self._star_routes, self._star_bodies, (code, artcc, "BODY")
        )

    def star_route_transition(
        self, code: object, artcc: object, transition: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._star_routes,
            self._star_route_transitions,
            (code, artcc, transition),
        )


def _airway_vertices(
    tables: Mapping[str, DataFrame],
    airway: str,
    start: str,
    end: str,
    *,
    airway_index: _AirwayIndex | None = None,
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

    if airway_index is None:
        identifiers = {
            match["identifier"],
            f"{match['designation']}{match['identifier']}",
        }
        matching_base = base[base["AWY_ID"].map(_text).isin(identifiers)]
    else:
        matching_base = airway_index.matching(airway)
        assert matching_base is not None
    matches: list[tuple[str, ...]] = []
    for key in matching_base[["REGULATORY", "AWY_LOCATION", "AWY_ID"]].itertuples(
        index=False, name=None
    ):
        if airway_index is not None:
            rows = airway_index.segments(key)
            if rows is None:
                rows = segments.iloc[0:0]
        else:
            rows = segments
            for column, value in zip(("REGULATORY", "AWY_LOCATION", "AWY_ID"), key):
                rows = rows[rows[column].map(_text).eq(_text(value))]
        ordered = sorted(
            zip(
                rows["POINT_SEQ"].to_numpy(copy=False),
                rows["FROM_POINT"].to_numpy(copy=False),
                rows["TO_POINT"].to_numpy(copy=False),
            ),
            key=lambda row: int(str(row[0])),
        )
        vertices: list[str] = []
        for _, raw_source, raw_destination in ordered:
            source, destination = _text(raw_source), _text(raw_destination)
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


def _is_published_airway(
    tables: Mapping[str, DataFrame],
    airway: str,
    *,
    airway_index: _AirwayIndex | None = None,
) -> bool:
    """Whether ``airway`` has a matching published airway base record."""

    match = _AIRWAY.fullmatch(airway)
    base = tables.get("AWY_BASE")
    if match is None or base is None:
        return False
    if airway_index is not None:
        return airway_index.is_published(airway)
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
            and (candidate[0].identifier if reverse else candidate[-1].identifier)
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
    ``IOW.LLROY3``), which identifies a branch in ``STAR_RTE``. STAR rows are
    recorded outbound from the terminal route's end, so they are traversed in
    reverse for an inbound flight plan.
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
        transition_points = _route_rows_points(tables, transition, resolver=resolver)
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
    departure_matches = procedure_index.departure_base(token)
    if departure_matches is None:
        return False
    first_component = token.split(".", 1)[0]
    first_component_matches = procedure_index.departure_base(first_component)
    assert first_component_matches is not None
    return not departure_matches.empty and first_component_matches.empty


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
            ):
                normalized.append(_RouteToken(combined, position))
                component_offset += len(component) + 1 + len(components[index + 1])
                index += 2
            else:
                normalized.append(_RouteToken(component, position))
                component_offset += len(component) + 1
                index += 1
    return tuple(normalized)


def _procedure_step_coordinates(
    nasr: Mapping[str, DataFrame],
    tokens: tuple[_RouteToken, ...],
    index: int,
    token: str,
    *,
    resolver: _WaypointResolver,
    airway_index: _AirwayIndex | None,
    procedure_index: _ProcedureIndex,
) -> tuple[tuple[float, float], ...] | None:
    """Return one procedure token's coordinates, or ``None`` if it is not one.

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
    return tuple(
        (point.latitude, point.longitude)
        for point in (join.prefix if join is not None else procedure)
    )


def _flight_plan_path(
    nasr: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    resolver: _WaypointResolver,
    airway_index: _AirwayIndex | None = None,
    procedure_index: _ProcedureIndex | None = None,
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
    procedure_index = procedure_index or _ProcedureIndex(nasr)
    tokens = _tokenize_flight_plan(
        nasr,
        flight_plan,
        resolver=resolver,
        procedure_index=procedure_index,
    )
    if not tokens or any(not token.value for token in tokens):
        raise ValueError("flight_plan must contain route tokens")

    output: list[tuple[float, float]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index].value
        if token == _DIRECT:
            index += 1
            continue
        procedure_coordinates = _procedure_step_coordinates(
            nasr,
            tokens,
            index,
            token,
            resolver=resolver,
            airway_index=airway_index,
            procedure_index=procedure_index,
        )
        if procedure_coordinates is not None:
            for coordinate in procedure_coordinates:
                if not output or output[-1] != coordinate:
                    output.append(coordinate)
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
                if previous_procedure is not None
                else None
            )
            previous = (
                previous_join.identifier
                if previous_join is not None
                else previous_procedure[-1].identifier
                if previous_procedure is not None
                else tokens[previous_index].value
            )
            following = (
                following_procedure[0].identifier
                if following_procedure is not None
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


class RouteResolver:
    """Resolve multiple routes against one indexed NASR table snapshot.

    The supplied mapping is copied at construction and waypoint indexes are
    built once. Callers that replace a table or mutate a contained DataFrame
    must construct a new resolver; automatic invalidation is intentionally
    not attempted for mutable pandas inputs.
    """

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._cycle = getattr(nasr, "effective_date", None)
        self._nasr = dict(nasr)
        self._waypoints = _WaypointResolver(self._nasr)
        self._airways = _AirwayIndex(self._nasr)
        self._procedures = _ProcedureIndex(self._nasr)

    def path(self, flight_plan: str) -> tuple[tuple[float, float], ...]:
        """Return the source-coordinate path for one FAA route field."""

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


def flight_plan_path(
    nasr: Mapping[str, DataFrame], flight_plan: str
) -> tuple[tuple[float, float], ...]:
    """Return the ``(latitude, longitude)`` path for FAA route-field text.

    For repeated calls against the same tables, prefer :class:`RouteResolver`
    so the waypoint index is built once.
    """

    return RouteResolver(nasr).path(flight_plan)


__all__ = ["RouteResolver", "flight_plan_path"]
