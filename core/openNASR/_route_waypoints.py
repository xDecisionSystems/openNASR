"""Waypoint lookup: airports, fixes, navaids and lat/lon waypoints.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from pandas import DataFrame

from ._route_common import (
    _KIND_BY_TABLE,
    _LATLON_WAYPOINT,
    _RADIAL_DISTANCE,
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
        self._variations = _magnetic_variations(tables)
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
                        identifier,
                        *coordinates,
                        kind=_KIND_BY_TABLE[table],
                        subtype=_text(nav_type) if table == "NAV_BASE" else "",
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
            offset = self._radial_distance(identifier)
            if offset is not None:
                return offset
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

    def _radial_distance(self, identifier: str) -> _Waypoint | None:
        """Decode a fix-radial-distance point (``MOL057057``), or None.

        The base is looked up like any route point (navaid first). The radial
        is magnetic, so it is turned into a true bearing with the magnetic
        variation NASR records for the nearest navaid or airport (the base
        itself when it is one); the distance is in nautical miles along a
        great circle on a spherical Earth.
        """

        match = _RADIAL_DISTANCE.match(identifier)
        if match is None:
            return None
        radial, distance = int(match["radial"]), int(match["distance"])
        if radial > 360:
            return None
        try:
            base = self.resolve(
                match["base"], preferred_tables=("NAV_BASE", "FIX_BASE", "APT_BASE")
            )
        except RecordNotFoundError:
            return None
        bearing = math.radians(
            (radial + _nearest_variation(self._variations, base)) % 360
        )
        latitude, longitude = _destination(
            base.latitude, base.longitude, bearing, distance / _EARTH_RADIUS_NM
        )
        return _Waypoint(identifier, latitude, longitude, kind="radial_distance")


# Mean Earth radius in nautical miles (1 NM = 1852 m, R = 6371.0088 km).
_EARTH_RADIUS_NM = 6371008.8 / 1852


def _destination(
    latitude: float, longitude: float, bearing: float, angle: float
) -> tuple[float, float]:
    """Great-circle destination from a point, a true bearing and an angle."""

    phi1, lam1 = math.radians(latitude), math.radians(longitude)
    phi2 = math.asin(
        math.sin(phi1) * math.cos(angle)
        + math.cos(phi1) * math.sin(angle) * math.cos(bearing)
    )
    lam2 = lam1 + math.atan2(
        math.sin(bearing) * math.sin(angle) * math.cos(phi1),
        math.cos(angle) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), (math.degrees(lam2) + 540) % 360 - 180


def _magnetic_variations(
    tables: Mapping[str, DataFrame],
) -> tuple[tuple[float, float, float], ...]:
    """(lat, lon, east-positive variation) of every navaid and airport with one."""

    points: list[tuple[float, float, float]] = []
    for table, hemisphere_column in (
        ("NAV_BASE", "MAG_VARN_HEMIS"),
        ("APT_BASE", "MAG_HEMIS"),
    ):
        frame = tables.get(table)
        if frame is None or not {
            "MAG_VARN",
            hemisphere_column,
            "LAT_DECIMAL",
            "LONG_DECIMAL",
        } <= set(frame.columns):
            continue
        for latitude, longitude, value, hemisphere in frame[
            ["LAT_DECIMAL", "LONG_DECIMAL", "MAG_VARN", hemisphere_column]
        ].to_numpy(dtype=object):
            try:
                variation = float(str(value))
                point = float(str(latitude)), float(str(longitude))
            except ValueError:
                continue
            if math.isnan(variation) or any(math.isnan(c) for c in point):
                continue
            sign = -1.0 if _text(hemisphere) == "W" else 1.0
            points.append((point[0], point[1], sign * variation))
    return tuple(points)


def _nearest_variation(
    variations: tuple[tuple[float, float, float], ...], point: _Waypoint
) -> float:
    """East-positive magnetic variation at the nearest recorded place (0 if none)."""

    best, best_distance = 0.0, math.inf
    cos_lat = math.cos(math.radians(point.latitude))
    for latitude, longitude, variation in variations:
        distance = (latitude - point.latitude) ** 2 + (
            (longitude - point.longitude) * cos_lat
        ) ** 2
        if distance < best_distance:
            best, best_distance = variation, distance
    return best


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
                    identifier,
                    *coordinates,
                    kind=_KIND_BY_TABLE[table],
                    subtype=(
                        _text(row.get("NAV_TYPE", "")) if table == "NAV_BASE" else ""
                    ),
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
