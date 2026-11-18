"""Waypoint lookup: airports, fixes, navaids and lat/lon waypoints.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from ._route_common import (
    _KIND_BY_TABLE,
    _LATLON_WAYPOINT,
    _WAYPOINT_TABLES,
    _coordinates,
    _text,
    _Waypoint,
)
from .exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
)


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
                if table == "NAV_BASE" and _text(nav_type) == "FAN MARKER":
                    # Marker beacons share names with navaids but are never
                    # filed as route points.
                    continue
                try:
                    coordinates = float(str(latitude)), float(str(longitude))
                except ValueError:
                    continue
                for raw_identifier in raw_identifiers:
                    identifier = _text(raw_identifier)
                    if not identifier:
                        continue
                    waypoint = _Waypoint(
                        identifier, *coordinates, kind=_KIND_BY_TABLE[table]
                    )
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
            decoded = _latlon_waypoint(identifier)
            if decoded is not None:
                return decoded
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


def _latlon_waypoint(identifier: str) -> _Waypoint | None:
    """Decode an ICAO lat/lon waypoint (``4620N07805W`` or ``46N078W``)."""

    match = _LATLON_WAYPOINT.match(identifier)
    if match is None or (match["lat_min"] is None) != (match["lon_min"] is None):
        return None
    latitude = int(match["lat"]) + int(match["lat_min"] or 0) / 60
    longitude = int(match["lon"]) + int(match["lon_min"] or 0) / 60
    if (
        latitude > 90
        or longitude > 180
        or int(match["lat_min"] or 0) > 59
        or int(match["lon_min"] or 0) > 59
    ):
        return None
    return _Waypoint(
        identifier,
        -latitude if match["ns"] == "S" else latitude,
        -longitude if match["ew"] == "W" else longitude,
        kind="latlon",
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
                waypoint = _Waypoint(
                    identifier, *coordinates, kind=_KIND_BY_TABLE[table]
                )
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
