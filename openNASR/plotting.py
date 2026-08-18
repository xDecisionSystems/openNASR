"""Map FAA airports and airway segments inside a geographic boundary."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy import ndarray
from pandas import DataFrame, Series
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.base import BaseGeometry

from .cfcn import ll2xy, xy2ll
from .flightplan import RouteResolver
from .ils import DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM, localizer_wedge_xy
from .indexing import (
    NormalizedIndexCache,
    cached_normalized_column_index,
    normalized_index_rows,
)

PlotProjection = Literal["geographic", "nautical_miles", "web_mercator"]
_WEB_MERCATOR_RADIUS_M = 6_378_137.0
_WEB_MERCATOR_MAX_LATITUDE = 85.0511287798066
_FEET_PER_NAUTICAL_MILE = 6076.12


@dataclass(frozen=True)
class _IlsProfile:
    threshold_latitude: float
    threshold_longitude: float
    threshold_elevation_ft: float
    opposite_latitude: float
    opposite_longitude: float
    opposite_elevation_ft: float
    glide_slope_latitude: float
    glide_slope_longitude: float
    glide_slope_elevation_ft: float
    glide_slope_angle_deg: float


def _plot_projection(
    project_to_nm: bool, projection: PlotProjection | None
) -> PlotProjection:
    """Resolve the new projection selector and the compatible NM flag."""

    if projection is None:
        return "nautical_miles" if project_to_nm else "geographic"
    if projection not in {"geographic", "nautical_miles", "web_mercator"}:
        raise ValueError(
            "projection must be 'geographic', 'nautical_miles', or 'web_mercator'"
        )
    if project_to_nm and projection != "nautical_miles":
        raise ValueError(
            "project_to_nm=True cannot be combined with a different projection"
        )
    return projection


def _axis_labels(projection: PlotProjection) -> tuple[str, str]:
    if projection == "nautical_miles":
        return "East (NM)", "North (NM)"
    if projection == "web_mercator":
        return "Web Mercator X (m)", "Web Mercator Y (m)"
    return "Longitude", "Latitude"


def _geometry(boundary: object) -> BaseGeometry:
    """Return a Shapely geometry from a geometry or NASR boundary object."""

    candidate = getattr(boundary, "getShape", boundary)
    if not isinstance(candidate, BaseGeometry):
        raise TypeError(
            "boundary must be a Shapely geometry or an airspace boundary exposing "
            "getShape"
        )
    if candidate.is_empty:
        raise ValueError("boundary must not be empty")
    return candidate


def _text(value: object) -> str:
    return "" if value is None or value != value else str(value).strip().upper()


class PlottingIndex:
    """Cache the source rows needed by one or more plotting calls.

    The index retains source positions and source-order coordinate lists rather
    than record objects. It can therefore be reused for batch plots against one
    NASR table mapping without changing the existing ambiguity rules.

    Each cached field is built lazily, the first time it is needed, from
    whatever ``nasr`` contains *at that moment* — construction itself does not
    copy any table. Treat the tables as immutable for the lifetime of a
    ``PlottingIndex``: mutating a table in place after some fields are already
    cached but before others are first accessed can make different fields of
    the same instance reflect different points in time. Construct a new
    ``PlottingIndex`` after changing a table.
    """

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._point_coordinates: dict[str, tuple[tuple[float, float], ...]] = {}
        self._coordinate_maps: dict[
            tuple[int, str], dict[str, list[tuple[float, float]]]
        ] = {}
        self._positions: NormalizedIndexCache = {}
        self._route_positions: dict[
            tuple[str, tuple[str, ...]], dict[tuple[str, ...], ndarray]
        ] = {}
        self._navigation: dict[str, list[tuple[float, float]]] | None = None
        self._airport_centers: dict[str, list[tuple[float, float]]] | None = None
        self._airways: tuple[tuple[str, LineString], ...] | None = None
        self._routes: RouteResolver | None = None

    @staticmethod
    def _points(frame: DataFrame | None) -> tuple[tuple[float, float], ...]:
        if frame is None or not {"LAT_DECIMAL", "LONG_DECIMAL"}.issubset(frame.columns):
            return ()
        points = []
        for latitude, longitude in zip(
            frame["LAT_DECIMAL"].to_numpy(copy=False),
            frame["LONG_DECIMAL"].to_numpy(copy=False),
        ):
            try:
                points.append((float(longitude), float(latitude)))
            except (TypeError, ValueError):
                continue
        return tuple(points)

    @staticmethod
    def _coordinates(
        frame: DataFrame, identifier_column: str
    ) -> dict[str, list[tuple[float, float]]]:
        points: dict[str, list[tuple[float, float]]] = {}
        required = {identifier_column, "LAT_DECIMAL", "LONG_DECIMAL"}
        if not required.issubset(frame.columns):
            return points
        for identifier, latitude, longitude in zip(
            frame[identifier_column].to_numpy(copy=False),
            frame["LAT_DECIMAL"].to_numpy(copy=False),
            frame["LONG_DECIMAL"].to_numpy(copy=False),
        ):
            try:
                coordinate = float(longitude), float(latitude)
            except (TypeError, ValueError):
                continue
            normalized = _text(identifier)
            if normalized:
                points.setdefault(normalized, []).append(coordinate)
        return points

    @staticmethod
    def _composite_positions(
        frame: DataFrame, columns: tuple[str, ...]
    ) -> dict[tuple[str, ...], ndarray]:
        normalized = [
            frame[column].map(_text)
            if column in frame
            else Series("", index=frame.index)
            for column in columns
        ]
        grouped = frame.groupby(normalized, sort=False).indices
        if len(columns) == 1:
            # A single-element groupby list yields bare scalar keys, not
            # 1-tuples; normalize to tuples so callers can always look up
            # with `tuple(...)` regardless of how many columns compose the key.
            return {(key,): positions for key, positions in grouped.items()}
        return grouped

    def _merged_navigation_endpoints(self) -> dict[str, list[tuple[float, float]]]:
        endpoints: dict[str, list[tuple[float, float]]] = {}
        for table, identifier in (("FIX_BASE", "FIX_ID"), ("NAV_BASE", "NAV_ID")):
            frame = self._nasr.get(table)
            if frame is None:
                continue
            for name, coordinates in self.coordinates(frame, identifier).items():
                endpoints.setdefault(name, []).extend(coordinates)
        return endpoints

    def _route_position_index(
        self, table: str, columns: tuple[str, ...]
    ) -> dict[tuple[str, ...], ndarray]:
        key = table, columns
        if key not in self._route_positions:
            frame = self._nasr.get(table)
            self._route_positions[key] = (
                self._composite_positions(frame, columns) if frame is not None else {}
            )
        return self._route_positions[key]

    def _indexed_airport_centers(self) -> dict[str, list[tuple[float, float]]]:
        airports = self._nasr.get("APT_BASE")
        if airports is None:
            return {}
        return {
            identifier: [(latitude, longitude) for longitude, latitude in coordinates]
            for identifier, coordinates in self._coordinates(
                airports, "ARPT_ID"
            ).items()
        }

    def _indexed_airway_segments(self) -> tuple[tuple[str, LineString], ...]:
        airway_rows = self._nasr.get("AWY_SEG_ALT")
        if airway_rows is None or not {"FROM_POINT", "TO_POINT"}.issubset(
            airway_rows.columns
        ):
            return ()
        designations: dict[tuple[str, str, str], str] = {}
        bases = self._nasr.get("AWY_BASE")
        if bases is not None:
            base_columns = (
                "REGULATORY",
                "AWY_LOCATION",
                "AWY_ID",
                "AWY_DESIGNATION",
            )
            values = [
                bases[column].to_numpy(copy=False)
                if column in bases
                else (None,) * len(bases.index)
                for column in base_columns
            ]
            for regulatory, location, identifier, designation in zip(*values):
                designations[
                    (_text(regulatory), _text(location), _text(identifier))
                ] = _text(designation)
        segment_columns = (
            "FROM_POINT",
            "TO_POINT",
            "REGULATORY",
            "AWY_LOCATION",
            "AWY_ID",
        )
        values = [
            airway_rows[column].to_numpy(copy=False)
            if column in airway_rows
            else (None,) * len(airway_rows.index)
            for column in segment_columns
        ]
        segments = []
        endpoints = self.navigation_endpoints()
        # Some published airway chains include named international-border
        # placeholders that have no corresponding FIX/NAV coordinate record in
        # the U.S. NASR subscription. Preserve the visual continuity of that
        # published airway by joining the surrounding coordinate-bearing
        # endpoints, rather than dropping the whole crossing.
        pending_continuations: dict[tuple[str, str, str], tuple[float, float]] = {}
        for source, destination, regulatory, location, identifier in zip(*values):
            starts = endpoints.get(_text(source), ())
            ends = endpoints.get(_text(destination), ())
            key = _text(regulatory), _text(location), _text(identifier)
            level = "high" if designations.get(key, "") in {"J", "Q"} else "low"
            if len(starts) == 1 and len(ends) == 1:
                pending_continuations.pop(key, None)
                if starts[0] != ends[0]:
                    segments.append((level, LineString((starts[0], ends[0]))))
            elif len(starts) == 1:
                pending_continuations[key] = starts[0]
            elif len(ends) == 1:
                continuation = pending_continuations.pop(key, None)
                if continuation is not None and continuation != ends[0]:
                    segments.append((level, LineString((continuation, ends[0]))))
        return tuple(segments)

    def _rows(self, table: str, column: str, value: object) -> DataFrame | None:
        frame = self._nasr.get(table)
        if frame is None or column not in frame:
            return None
        index = cached_normalized_column_index(self._positions, frame, column, _text)
        return normalized_index_rows(frame, index, value, _text)

    def validate(self, nasr: Mapping[str, DataFrame]) -> None:
        """Raise if this index was not built from ``nasr``.

        Every ``plot_*`` function calls this automatically for a supplied
        ``index=``. Calling lookup methods directly on a ``PlottingIndex``
        (bypassing ``plot_*``) does not check this on your behalf; call
        ``validate`` yourself first if you built the index from an
        untrusted or possibly-stale mapping reference.
        """
        if nasr is not self._nasr:
            raise ValueError("PlottingIndex belongs to a different NASR table mapping")

    def point_coordinates(self, table: str) -> tuple[tuple[float, float], ...]:
        if table not in self._point_coordinates:
            self._point_coordinates[table] = self._points(self._nasr.get(table))
        return self._point_coordinates.get(table, ())

    def coordinates(
        self, frame: DataFrame, identifier_column: str
    ) -> dict[str, list[tuple[float, float]]]:
        key = id(frame), identifier_column
        if key not in self._coordinate_maps:
            self._coordinate_maps[key] = self._coordinates(frame, identifier_column)
        return self._coordinate_maps[key]

    def navigation_endpoints(self) -> dict[str, list[tuple[float, float]]]:
        if self._navigation is None:
            self._navigation = self._merged_navigation_endpoints()
        return self._navigation

    def airway_segments(self) -> tuple[tuple[str, LineString], ...]:
        if self._airways is None:
            self._airways = self._indexed_airway_segments()
        return self._airways

    def airport_projection_center(self, airport_id: str) -> tuple[float, float]:
        airports = self._nasr.get("APT_BASE")
        if airports is None or "ARPT_ID" not in airports.columns:
            raise ValueError(
                "projected airport plots require APT_BASE airport coordinates"
            )
        if self._airport_centers is None:
            self._airport_centers = self._indexed_airport_centers()
        centers = self._airport_centers.get(_text(airport_id), ())
        if len(centers) != 1:
            raise ValueError(
                f"projected airport plots require one coordinate for {airport_id!r}"
            )
        return centers[0]

    def procedure_segments(
        self,
        airport_id: str,
        association_table: str,
        route_table: str,
        key_columns: tuple[str, ...],
        *,
        reverse: bool = False,
    ) -> tuple[LineString, ...]:
        associations = self._rows(association_table, "ARPT_ID", airport_id)
        routes = self._nasr.get(route_table)
        if associations is None or routes is None:
            return ()
        positions = self._route_position_index(route_table, key_columns)
        values = [
            associations[column].to_numpy(copy=False)
            if column in associations
            else (None,) * len(associations.index)
            for column in key_columns
        ]
        keys = {tuple(_text(value) for value in key) for key in zip(*values)}
        row_positions = sorted(
            {int(position) for key in keys for position in positions.get(key, ())}
        )
        segments = []
        selected = routes.iloc[row_positions]
        values = [
            selected[column].to_numpy(copy=False)
            if column in selected
            else (None,) * len(selected.index)
            for column in ("POINT", "NEXT_POINT")
        ]
        endpoints = self.navigation_endpoints()
        for source, destination in zip(*values):
            starts = endpoints.get(_text(source), ())
            ends = endpoints.get(_text(destination), ())
            if len(starts) == 1 and len(ends) == 1 and starts[0] != ends[0]:
                coordinates = (ends[0], starts[0]) if reverse else (starts[0], ends[0])
                segments.append(LineString(coordinates))
        return tuple(segments)

    def runway_segments(self, airport_id: str) -> tuple[LineString, ...]:
        ends = self._rows("APT_RWY_END", "ARPT_ID", airport_id)
        if ends is None or "RWY_ID" not in ends.columns:
            return ()
        grouped = self._coordinates(ends, "RWY_ID")
        return tuple(
            LineString((points[0], points[1]))
            for points in grouped.values()
            if len(points) >= 2 and points[0] != points[1]
        )

    def runway_segment(self, airport_id: str, runway_id: str) -> LineString:
        """Return the surveyed threshold-to-threshold segment for one runway."""

        frame = self._nasr.get("APT_RWY_END")
        required = {"ARPT_ID", "RWY_ID", "LAT_DECIMAL", "LONG_DECIMAL"}
        if frame is None or not required.issubset(frame.columns):
            raise ValueError("runway plots require APT_RWY_END coordinates")
        positions = self._route_position_index(
            "APT_RWY_END", ("ARPT_ID", "RWY_ID")
        ).get((_text(airport_id), _text(runway_id)), ())
        coordinates = []
        for position in positions:
            row = frame.iloc[int(position)]
            try:
                coordinates.append(
                    (float(row["LONG_DECIMAL"]), float(row["LAT_DECIMAL"]))
                )
            except (TypeError, ValueError):
                continue
        if len(coordinates) < 2 or coordinates[0] == coordinates[1]:
            raise ValueError(
                "runway plots require two surveyed runway thresholds for "
                f"{_text(airport_id)} {_text(runway_id)}"
            )
        return LineString((coordinates[0], coordinates[1]))

    def runway_end_coordinate(
        self, airport_id: str, runway_end_id: str
    ) -> tuple[float, float]:
        """Return one runway threshold as ``(latitude, longitude)``."""

        frame = self._nasr.get("APT_RWY_END")
        required = {"ARPT_ID", "RWY_END_ID", "LAT_DECIMAL", "LONG_DECIMAL"}
        if frame is None or not required.issubset(frame.columns):
            raise ValueError("localizer plots require APT_RWY_END coordinates")
        positions = self._route_position_index(
            "APT_RWY_END", ("ARPT_ID", "RWY_END_ID")
        ).get((_text(airport_id), _text(runway_end_id)), ())
        coordinates = []
        for position in positions:
            row = frame.iloc[int(position)]
            try:
                coordinates.append(
                    (float(row["LAT_DECIMAL"]), float(row["LONG_DECIMAL"]))
                )
            except (TypeError, ValueError):
                continue
        if len(coordinates) != 1:
            raise ValueError(
                "localizer plots require exactly one surveyed runway threshold for "
                f"{_text(airport_id)} {_text(runway_end_id)}"
            )
        return coordinates[0]

    def ils_profile(
        self, airport_id: str, runway_end_id: str, localizer_id: str
    ) -> _IlsProfile:
        """Return runway and glide-slope values for an ILS side view."""

        runway_ends = self._nasr.get("APT_RWY_END")
        runway_columns = {
            "ARPT_ID",
            "RWY_ID",
            "RWY_END_ID",
            "LAT_DECIMAL",
            "LONG_DECIMAL",
            "RWY_END_ELEV",
        }
        if runway_ends is None or not runway_columns.issubset(runway_ends.columns):
            raise ValueError("ILS side views require APT_RWY_END survey data")
        threshold_positions = self._route_position_index(
            "APT_RWY_END", ("ARPT_ID", "RWY_END_ID")
        ).get((_text(airport_id), _text(runway_end_id)), ())
        if len(threshold_positions) != 1:
            raise ValueError(
                "ILS side views require exactly one selected runway threshold"
            )
        threshold = runway_ends.iloc[int(next(iter(threshold_positions)))]
        runway_id = _text(threshold["RWY_ID"])
        runway_positions = self._route_position_index(
            "APT_RWY_END", ("ARPT_ID", "RWY_ID")
        ).get((_text(airport_id), runway_id), ())
        opposite_positions = [
            position
            for position in runway_positions
            if _text(runway_ends.iloc[int(position)]["RWY_END_ID"])
            != _text(runway_end_id)
        ]
        if len(opposite_positions) != 1:
            raise ValueError("ILS side views require one opposite runway threshold")
        opposite = runway_ends.iloc[int(opposite_positions[0])]

        glide_slopes = self._nasr.get("ILS_GS")
        glide_columns = {
            "ARPT_ID",
            "RWY_END_ID",
            "ILS_LOC_ID",
            "LAT_DECIMAL",
            "LONG_DECIMAL",
            "SITE_ELEVATION",
            "G_S_ANGLE",
        }
        if glide_slopes is None or not glide_columns.issubset(glide_slopes.columns):
            raise ValueError("ILS plots require ILS_GS survey data")
        glide_positions = self._route_position_index(
            "ILS_GS", ("ARPT_ID", "RWY_END_ID", "ILS_LOC_ID")
        ).get((_text(airport_id), _text(runway_end_id), _text(localizer_id)), ())
        if len(glide_positions) != 1:
            raise ValueError("ILS plots require exactly one matching glide slope")
        glide_slope = glide_slopes.iloc[int(next(iter(glide_positions)))]

        try:
            return _IlsProfile(
                threshold_latitude=float(threshold["LAT_DECIMAL"]),
                threshold_longitude=float(threshold["LONG_DECIMAL"]),
                threshold_elevation_ft=float(threshold["RWY_END_ELEV"]),
                opposite_latitude=float(opposite["LAT_DECIMAL"]),
                opposite_longitude=float(opposite["LONG_DECIMAL"]),
                opposite_elevation_ft=float(opposite["RWY_END_ELEV"]),
                glide_slope_latitude=float(glide_slope["LAT_DECIMAL"]),
                glide_slope_longitude=float(glide_slope["LONG_DECIMAL"]),
                glide_slope_elevation_ft=float(glide_slope["SITE_ELEVATION"]),
                glide_slope_angle_deg=float(glide_slope["G_S_ANGLE"]),
            )
        except (TypeError, ValueError) as error:
            raise ValueError(
                "ILS top and side views require numeric runway/glide-slope values"
            ) from error

    def record_segments(
        self,
        records: Iterable[Mapping[str, object]],
        source_column: str,
        destination_column: str,
    ) -> tuple[LineString, ...]:
        """Resolve ordered route records through cached fix/navaid coordinates."""

        endpoints = self.navigation_endpoints()
        segments = []
        for record in records:
            starts = endpoints.get(_text(record.get(source_column)), ())
            ends = endpoints.get(_text(record.get(destination_column)), ())
            if len(starts) == 1 and len(ends) == 1 and starts[0] != ends[0]:
                segments.append(LineString((starts[0], ends[0])))
        return tuple(segments)

    def flight_plan_path(self, flight_plan: str) -> tuple[tuple[float, float], ...]:
        if self._routes is None:
            self._routes = RouteResolver(self._nasr)
        return self._routes.path(flight_plan)


def _plotting_index(
    nasr: Mapping[str, DataFrame], index: PlottingIndex | None
) -> PlottingIndex:
    if index is None:
        return PlottingIndex(nasr)
    index.validate(nasr)
    return index


def _coordinates(
    frame: DataFrame, identifier_column: str, *, index: PlottingIndex | None = None
) -> dict[str, list[tuple[float, float]]]:
    if index is not None:
        return index.coordinates(frame, identifier_column)
    points: dict[str, list[tuple[float, float]]] = {}
    required = {identifier_column, "LAT_DECIMAL", "LONG_DECIMAL"}
    if not required.issubset(frame.columns):
        return points
    for row in frame.to_dict(orient="records"):
        try:
            coordinate = float(row["LONG_DECIMAL"]), float(row["LAT_DECIMAL"])
        except (TypeError, ValueError):
            continue
        identifier = _text(row[identifier_column])
        if identifier:
            points.setdefault(identifier, []).append(coordinate)
    return points


def _airway_segments(
    nasr: Mapping[str, DataFrame], *, index: PlottingIndex | None = None
) -> tuple[tuple[str, LineString], ...]:
    """Resolve plotted airway segments through their fix/navaid endpoints."""

    return _plotting_index(nasr, index).airway_segments()


def _airport_identifier(airport: object) -> str:
    if isinstance(airport, str):
        return _text(airport)
    for attribute in ("faa_id", "airport_id"):
        value = getattr(airport, attribute, None)
        if value is not None:
            return _text(value)
    if isinstance(airport, Mapping):
        return _text(airport.get("ARPT_ID"))
    raise TypeError(
        "airport must be an FAA identifier, airport object, or ARPT_ID mapping"
    )


def _airport_projection_center(
    nasr: Mapping[str, DataFrame],
    airport_id: str,
    *,
    index: PlottingIndex | None = None,
) -> tuple[float, float]:
    """Return the FAA latitude/longitude of an airport plotting center."""

    return _plotting_index(nasr, index).airport_projection_center(airport_id)


def _procedure_segments(
    nasr: Mapping[str, DataFrame],
    airport_id: str,
    association_table: str,
    route_table: str,
    key_columns: tuple[str, ...],
    *,
    reverse: bool = False,
    index: PlottingIndex | None = None,
) -> tuple[LineString, ...]:
    return _plotting_index(nasr, index).procedure_segments(
        airport_id, association_table, route_table, key_columns, reverse=reverse
    )


def _runway_segments(
    nasr: Mapping[str, DataFrame],
    airport_id: str,
    *,
    index: PlottingIndex | None = None,
) -> tuple[LineString, ...]:
    return _plotting_index(nasr, index).runway_segments(airport_id)


def _projection_center(
    geometry: BaseGeometry, center: tuple[float, float] | None
) -> tuple[float, float]:
    """Return a latitude/longitude gnomonic center for an airspace plot."""

    if center is not None:
        if len(center) != 2:
            raise ValueError("projection_center must be a (latitude, longitude) pair")
        return float(center[0]), float(center[1])
    centroid = geometry.centroid
    return float(centroid.y), float(centroid.x)


def _project_coordinates(
    longitudes: Any,
    latitudes: Any,
    *,
    projection: PlotProjection,
    center: tuple[float, float] | None,
) -> tuple[Any, Any]:
    """Project longitude/latitude coordinates into the selected plot CRS."""

    if projection == "geographic":
        return longitudes, latitudes
    if projection == "nautical_miles":
        if center is None:
            raise ValueError("nautical-mile projection requires a projection center")
        x_values, y_values, _, _ = ll2xy(latitudes, longitudes, llc=center)
        return x_values, y_values

    longitude_values = np.asarray(longitudes, dtype=float)
    latitude_values = np.asarray(latitudes, dtype=float)
    if np.any(~np.isfinite(longitude_values)) or np.any(
        (longitude_values < -180) | (longitude_values > 180)
    ):
        raise ValueError("longitude must be finite and between -180 and 180 degrees")
    if np.any(~np.isfinite(latitude_values)) or np.any(
        (latitude_values < -90) | (latitude_values > 90)
    ):
        raise ValueError("latitude must be finite and between -90 and 90 degrees")
    clipped_latitudes = np.clip(
        latitude_values,
        -_WEB_MERCATOR_MAX_LATITUDE,
        _WEB_MERCATOR_MAX_LATITUDE,
    )
    x_values = _WEB_MERCATOR_RADIUS_M * np.radians(longitude_values)
    y_values = _WEB_MERCATOR_RADIUS_M * np.log(
        np.tan(np.pi / 4 + np.radians(clipped_latitudes) / 2)
    )
    return x_values, y_values


def _plot_points(
    axes: Any,
    coordinates: tuple[tuple[float, float], ...],
    geometry: BaseGeometry,
    *,
    marker: str,
    color: str,
    label: str,
    projection: PlotProjection,
    projection_center: tuple[float, float] | None,
) -> None:
    plotted = False
    for longitude, latitude in coordinates:
        point = Point(longitude, latitude)
        if geometry.covers(point):
            x_values, y_values = _project_coordinates(
                point.x,
                point.y,
                projection=projection,
                center=projection_center,
            )
            axes.plot(
                x_values,
                y_values,
                marker=marker,
                color=color,
                markersize=4,
                linestyle="None",
                label=None if plotted else label,
            )
            plotted = True


def _plot_boundary(
    axes: Any,
    geometry: BaseGeometry,
    *,
    projection: PlotProjection,
    projection_center: tuple[float, float] | None,
    **kwargs: Any,
) -> None:
    geometries = geometry.geoms if hasattr(geometry, "geoms") else (geometry,)
    plotted = False
    for polygon in geometries:
        if not hasattr(polygon, "exterior"):
            continue
        x_values, y_values = polygon.exterior.xy
        x_values, y_values = _project_coordinates(
            x_values,
            y_values,
            projection=projection,
            center=projection_center,
        )
        axes.plot(
            x_values,
            y_values,
            **({**kwargs, "label": None if plotted else kwargs.get("label")}),
        )
        plotted = True


def _line_parts(geometry: BaseGeometry) -> tuple[LineString, ...]:
    """Return every non-empty line component from an intersection result."""

    if isinstance(geometry, LineString):
        return () if geometry.is_empty else (geometry,)
    if hasattr(geometry, "geoms"):
        parts: list[LineString] = []
        for component in geometry.geoms:
            parts.extend(_line_parts(component))
        return tuple(parts)
    return ()


def _airspace_points(
    axes: Any,
    plotting_index: PlottingIndex,
    geometry: BaseGeometry,
    *,
    plot_airports: bool,
    plot_fixes: bool,
    plot_airnavs: bool,
    projection: PlotProjection,
    projection_center: tuple[float, float] | None,
) -> None:
    """Draw the toggleable airport/fix/navaid point layers."""

    layers = (
        (plot_airports, "APT_BASE", "o", "tab:blue", "Airports"),
        (plot_fixes, "FIX_BASE", "x", "tab:green", "Fixes"),
        (plot_airnavs, "NAV_BASE", "^", "tab:purple", "Navaids"),
    )
    for enabled, table, marker, color, label in layers:
        if enabled:
            _plot_points(
                axes,
                plotting_index.point_coordinates(table),
                geometry,
                marker=marker,
                color=color,
                label=label,
                projection=projection,
                projection_center=projection_center,
            )


def _airspace_airways(
    nasr: Mapping[str, DataFrame],
    axes: Any,
    plotting_index: PlottingIndex,
    geometry: BaseGeometry,
    *,
    plot_high_airways: bool,
    plot_low_airways: bool,
    projection: PlotProjection,
    projection_center: tuple[float, float] | None,
) -> None:
    """Draw intersecting high/low airway segments clipped to the boundary."""

    airway_labels = {"high": "High-altitude airways", "low": "Low-altitude airways"}
    drawn_levels: set[str] = set()
    for level, segment in _airway_segments(nasr, index=plotting_index):
        enabled = plot_high_airways if level == "high" else plot_low_airways
        if not enabled or not geometry.intersects(segment):
            continue
        clipped = geometry.intersection(segment)
        for line in _line_parts(clipped):
            x_values, y_values = line.xy
            x_values, y_values = _project_coordinates(
                x_values,
                y_values,
                projection=projection,
                center=projection_center,
            )
            color = "tab:red" if level == "high" else "tab:orange"
            axes.plot(
                x_values,
                y_values,
                color=color,
                linewidth=1,
                label=None if level in drawn_levels else airway_labels[level],
            )
            drawn_levels.add(level)


def plot_airspace(
    nasr: Mapping[str, DataFrame],
    boundary: object,
    *,
    axes: Any | None = None,
    plot_high_airways: bool = True,
    plot_low_airways: bool = True,
    plot_airports: bool = True,
    plot_fixes: bool = True,
    plot_airnavs: bool = True,
    plot_legend: bool = True,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot a boundary with contained airports and intersecting airway segments.

    Parameters
    ----------
    nasr:
        Loaded NASR tables, normally a :class:`~openNASR.nasr.NASR` instance.
    boundary:
        A Shapely longitude/latitude geometry or a NASR boundary object exposing
        ``getShape`` (such as an ARTCC ``Boundary``).
    axes:
        Optional Matplotlib axes to draw into.
    plot_high_airways, plot_low_airways, plot_airports, plot_fixes, plot_airnavs:
        Toggle high-altitude J/Q airways, low airways, airports, fixes, and
        navaids respectively. All default to ``True``.
    plot_legend:
        Draw a legend for the layers represented in the plot. Defaults to
        ``True``.
    project_to_nm:
        Project longitude/latitude coordinates onto a local gnomonic plane in
        nautical miles. Defaults to ``False``.
    projection_center:
        Optional ``(latitude, longitude)`` center for ``project_to_nm``. When
        omitted, the center of the plotted airspace is used.
    projection:
        Output coordinate system: ``"geographic"`` for longitude/latitude,
        ``"nautical_miles"`` for the local centered projection, or
        ``"web_mercator"`` for EPSG:3857-compatible x/y meters. The existing
        ``project_to_nm=True`` option is equivalent to
        ``projection="nautical_miles"``.

    Returns
    -------
    tuple
        The Matplotlib ``(figure, axes)`` pair. Coordinates are longitude and
        latitude by default, east/north nautical miles for the local
        projection, or EPSG:3857-compatible x/y meters for Web Mercator.
    """

    plotting_index = _plotting_index(nasr, index)
    geometry = _geometry(boundary)
    active_projection = _plot_projection(project_to_nm, projection)
    if active_projection == "web_mercator" and projection_center is not None:
        raise ValueError("projection_center is not used by web_mercator")
    active_projection_center = (
        _projection_center(geometry, projection_center)
        if active_projection == "nautical_miles"
        else None
    )
    from matplotlib import pyplot as plt

    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    _plot_boundary(
        axes,
        geometry,
        projection=active_projection,
        projection_center=active_projection_center,
        color="black",
        linewidth=1.5,
        label="Airspace",
    )

    _airspace_points(
        axes,
        plotting_index,
        geometry,
        plot_airports=plot_airports,
        plot_fixes=plot_fixes,
        plot_airnavs=plot_airnavs,
        projection=active_projection,
        projection_center=active_projection_center,
    )

    if plot_high_airways or plot_low_airways:
        _airspace_airways(
            nasr,
            axes,
            plotting_index,
            geometry,
            plot_high_airways=plot_high_airways,
            plot_low_airways=plot_low_airways,
            projection=active_projection,
            projection_center=active_projection_center,
        )

    if plot_legend:
        axes.legend()
    x_label, y_label = _axis_labels(active_projection)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def _airport_procedure_layers(
    nasr: Mapping[str, DataFrame],
    airport_id: str,
    plotting_index: PlottingIndex,
    *,
    plot_runways: bool,
    plot_departures: bool,
    plot_arrivals: bool,
) -> tuple[tuple[tuple[LineString, ...], str, int, str], ...]:
    """Return (segments, color, linewidth, label) for each procedure layer."""

    layers = []
    if plot_runways:
        layers.append(
            (
                _runway_segments(nasr, airport_id, index=plotting_index),
                "black",
                3,
                "Runways",
            )
        )
    if plot_departures:
        layers.append(
            (
                _procedure_segments(
                    nasr,
                    airport_id,
                    "DP_APT",
                    "DP_RTE",
                    ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE"),
                    reverse=True,
                    index=plotting_index,
                ),
                "tab:blue",
                1,
                "Departures",
            ),
        )
    if plot_arrivals:
        layers.append(
            (
                _procedure_segments(
                    nasr,
                    airport_id,
                    "STAR_APT",
                    "STAR_RTE",
                    ("STAR_COMPUTER_CODE", "ARTCC"),
                    index=plotting_index,
                ),
                "tab:green",
                1,
                "Arrivals",
            ),
        )
    return tuple(layers)


def _draw_projected_layers(
    axes: Any,
    layers: tuple[tuple[tuple[LineString, ...], str, float, str], ...],
    *,
    projection: PlotProjection,
    projection_center: tuple[float, float] | None,
) -> None:
    """Draw each layer's line segments, labeling only the first per layer."""

    for segments, color, linewidth, label in layers:
        plotted = False
        for segment in segments:
            x_values, y_values = segment.xy
            x_values, y_values = _project_coordinates(
                x_values,
                y_values,
                projection=projection,
                center=projection_center,
            )
            axes.plot(
                x_values,
                y_values,
                color=color,
                linewidth=linewidth,
                label=None if plotted else label,
            )
            plotted = True


def _plot_route_object(
    segments: tuple[LineString, ...],
    *,
    axes: Any | None,
    project_to_nm: bool,
    projection: PlotProjection | None,
    projection_center: tuple[float, float] | None,
    plot_legend: bool,
    color: str,
    label: str,
    title: str,
    linewidth: float = 1,
) -> tuple[Any, Any]:
    """Draw one route-like domain object from already-resolved segments."""

    from matplotlib import pyplot as plt

    active_projection = _plot_projection(project_to_nm, projection)
    if active_projection == "web_mercator" and projection_center is not None:
        raise ValueError("projection_center is not used by web_mercator")
    active_projection_center = None
    if active_projection == "nautical_miles":
        if projection_center is not None:
            if len(projection_center) != 2:
                raise ValueError(
                    "projection_center must be a (latitude, longitude) pair"
                )
            active_projection_center = (
                float(projection_center[0]),
                float(projection_center[1]),
            )
        elif segments:
            geometry = MultiLineString([tuple(segment.coords) for segment in segments])
            active_projection_center = _projection_center(geometry, None)
        else:
            raise ValueError(
                "cannot infer projection center without a resolved route segment"
            )
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    _draw_projected_layers(
        axes,
        ((segments, color, linewidth, label),),
        projection=active_projection,
        projection_center=active_projection_center,
    )
    if plot_legend and axes.get_legend_handles_labels()[0]:
        axes.legend()
    axes.set_title(title)
    x_label, y_label = _axis_labels(active_projection)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def plot_runway(
    nasr: Mapping[str, DataFrame],
    runway: Mapping[str, object],
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot one runway between its two surveyed threshold coordinates."""

    if not isinstance(runway, Mapping):
        raise TypeError("runway must be a RunwayRecord or APT_RWY mapping")
    airport_id = _text(runway.get("ARPT_ID"))
    runway_id = _text(runway.get("RWY_ID"))
    if not airport_id or not runway_id:
        raise ValueError("runway plots require ARPT_ID and RWY_ID")
    plotting_index = _plotting_index(nasr, index)
    segment = plotting_index.runway_segment(airport_id, runway_id)
    return _plot_route_object(
        (segment,),
        axes=axes,
        project_to_nm=project_to_nm,
        projection=projection,
        projection_center=projection_center,
        plot_legend=plot_legend,
        color="black",
        label="Runway",
        title=f"{airport_id} runway {runway_id}",
        linewidth=4,
    )


def plot_airway(
    nasr: Mapping[str, DataFrame],
    airway: object,
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot an :class:`Airway` in geographic, local-NM, or Web Mercator coordinates."""

    record = getattr(airway, "record", None)
    records = getattr(airway, "segments", None)
    if not isinstance(record, Mapping) or records is None:
        raise TypeError("airway must be an Airway object with record and segments")
    plotting_index = _plotting_index(nasr, index)
    segments = plotting_index.record_segments(records, "FROM_POINT", "TO_POINT")
    identifier = _text(record.get("AWY_ID")) or "Airway"
    return _plot_route_object(
        segments,
        axes=axes,
        project_to_nm=project_to_nm,
        projection=projection,
        projection_center=projection_center,
        plot_legend=plot_legend,
        color="tab:orange",
        label=identifier,
        title=f"{identifier} airway",
    )


def plot_star(
    nasr: Mapping[str, DataFrame],
    star: object,
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot a :class:`StarProcedure` in geographic, local-NM, or Web Mercator.

    Output coordinates follow the selected projection.
    """

    record = getattr(star, "record", None)
    records = getattr(star, "routes", None)
    if not isinstance(record, Mapping) or records is None:
        raise TypeError("star must be a StarProcedure object with record and routes")
    plotting_index = _plotting_index(nasr, index)
    segments = plotting_index.record_segments(records, "POINT", "NEXT_POINT")
    identifier = (
        _text(record.get("ARRIVAL_NAME"))
        or _text(record.get("STAR_COMPUTER_CODE"))
        or "STAR"
    )
    return _plot_route_object(
        segments,
        axes=axes,
        project_to_nm=project_to_nm,
        projection=projection,
        projection_center=projection_center,
        plot_legend=plot_legend,
        color="tab:green",
        label=identifier,
        title=f"{identifier} arrival",
    )


def plot_artcc(
    nasr: Mapping[str, DataFrame],
    artcc: object,
    *,
    level: str = "high",
    axes: Any | None = None,
    plot_high_airways: bool = True,
    plot_low_airways: bool = True,
    plot_airports: bool = True,
    plot_fixes: bool = True,
    plot_airnavs: bool = True,
    plot_legend: bool = True,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot one altitude boundary from an :class:`Artcc` object.

    ``level`` is ``"high"`` by default and may be set to ``"low"``. The
    selected boundary is passed to :func:`plot_airspace`, which supplies all
    normal layer, projection, axes, legend, and index behavior.
    """

    normalized_level = _text(level).lower()
    if normalized_level not in {"high", "low"}:
        raise ValueError("level must be 'high' or 'low'")
    boundaries = getattr(artcc, "boundaries", None)
    if not isinstance(boundaries, Mapping):
        raise TypeError("artcc must be an Artcc object with boundaries")
    boundary = boundaries.get(normalized_level)
    if boundary is None:
        raise ValueError(f"ARTCC has no {normalized_level!r} boundary")
    figure, axes = plot_airspace(
        nasr,
        boundary,
        axes=axes,
        plot_high_airways=plot_high_airways,
        plot_low_airways=plot_low_airways,
        plot_airports=plot_airports,
        plot_fixes=plot_fixes,
        plot_airnavs=plot_airnavs,
        plot_legend=plot_legend,
        project_to_nm=project_to_nm,
        projection_center=projection_center,
        projection=projection,
        index=index,
    )
    location_id = _text(getattr(artcc, "location_id", None)) or "ARTCC"
    axes.set_title(f"{location_id} {normalized_level}-altitude ARTCC")
    return figure, axes


def _localizer_true_bearing(record: Mapping[str, object]) -> float:
    """Convert the FAA magnetic approach bearing and variation to true bearing."""

    try:
        approach_bearing = float(str(record["APCH_BEAR"]))
        variation = float(str(record.get("MAG_VAR") or 0.0))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "localizer plots require numeric APCH_BEAR and MAG_VAR values"
        ) from error
    hemisphere = _text(record.get("MAG_VAR_HEMIS"))
    if hemisphere == "W":
        variation = -abs(variation)
    elif hemisphere == "E":
        variation = abs(variation)
    if not np.isfinite(approach_bearing) or not np.isfinite(variation):
        raise ValueError("localizer bearing and magnetic variation must be finite")
    return (approach_bearing + variation) % 360.0


def plot_ils_localizer(
    nasr: Mapping[str, DataFrame],
    ils: Mapping[str, object],
    *,
    axes: Any | None = None,
    side_axes: Any | None = None,
    plot_wedge: bool = True,
    wedge_distance_nm: float = DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM,
    plot_glide_slope: bool = True,
    glide_slope_distance_nm: float = 15.0,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot top-view ILS geometry and an optional runway/glide-slope side view.

    ``ils`` is normally an :class:`~openNASR.ils.IlsRecord`. The wedge is 700
    feet wide at the surveyed runway threshold and expands at a 2.5-degree
    half-angle for ``wedge_distance_nm`` nautical miles into the approach
    area. Set ``plot_wedge=False`` to draw only the localizer transmitter.
    The default wedge distance is 20 NM. When ``side_axes`` is supplied, the
    runway elevation profile and FAA-published glide-slope angle are drawn on
    those axes. ``plot_glide_slope`` also controls the surveyed top-view
    glide-slope site.
    """

    if not isinstance(ils, Mapping):
        raise TypeError("ils must be an IlsRecord or ILS_BASE mapping")
    airport_id = _text(ils.get("ARPT_ID"))
    runway_end_id = _text(ils.get("RWY_END_ID"))
    if not airport_id or not runway_end_id:
        raise ValueError("localizer plots require ARPT_ID and RWY_END_ID")
    try:
        localizer_latitude = float(str(ils["LAT_DECIMAL"]))
        localizer_longitude = float(str(ils["LONG_DECIMAL"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "localizer plots require surveyed ILS_BASE coordinates"
        ) from error
    if not np.isfinite(localizer_latitude) or not np.isfinite(localizer_longitude):
        raise ValueError("localizer coordinates must be finite")

    plotting_index = _plotting_index(nasr, index)
    threshold = plotting_index.runway_end_coordinate(airport_id, runway_end_id)
    profile = None
    if plot_glide_slope or side_axes is not None:
        localizer_id = _text(ils.get("ILS_LOC_ID"))
        if not localizer_id:
            if side_axes is not None:
                raise ValueError("ILS side views require ILS_LOC_ID")
        else:
            try:
                profile = plotting_index.ils_profile(
                    airport_id, runway_end_id, localizer_id
                )
            except ValueError:
                if side_axes is not None:
                    raise
    active_projection = _plot_projection(project_to_nm, projection)
    if active_projection == "web_mercator" and projection_center is not None:
        raise ValueError("projection_center is not used by web_mercator")
    active_projection_center = (
        _projection_center(Point(threshold[1], threshold[0]), projection_center)
        if active_projection == "nautical_miles"
        else None
    )

    from matplotlib import pyplot as plt

    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    localizer_x, localizer_y = _project_coordinates(
        localizer_longitude,
        localizer_latitude,
        projection=active_projection,
        center=active_projection_center,
    )
    axes.scatter(
        localizer_x,
        localizer_y,
        color="tab:blue",
        marker="h",
        label="Localizer",
    )

    if plot_glide_slope and profile is not None:
        glide_x, glide_y = _project_coordinates(
            profile.glide_slope_longitude,
            profile.glide_slope_latitude,
            projection=active_projection,
            center=active_projection_center,
        )
        axes.scatter(
            glide_x,
            glide_y,
            color="tab:red",
            marker="^",
            label="Glide slope",
        )

    if plot_wedge:
        wedge_x, wedge_y = localizer_wedge_xy(
            0.0,
            0.0,
            _localizer_true_bearing(ils),
            distance_nm=wedge_distance_nm,
        )
        wedge_latitudes, wedge_longitudes = xy2ll(
            np.asarray(wedge_x),
            np.asarray(wedge_y),
            llc=threshold,
        )
        projected_x, projected_y = _project_coordinates(
            wedge_longitudes,
            wedge_latitudes,
            projection=active_projection,
            center=active_projection_center,
        )
        axes.fill(
            projected_x,
            projected_y,
            facecolor="tab:blue",
            edgecolor="tab:blue",
            alpha=0.2,
            label="Localizer course",
        )

    if side_axes is not None and profile is not None:
        side_distance = float(glide_slope_distance_nm)
        if not np.isfinite(side_distance) or side_distance <= 0:
            raise ValueError("glide_slope_distance_nm must be greater than zero")
        local_x, local_y, _, _ = ll2xy(
            [profile.opposite_latitude, profile.glide_slope_latitude],
            [profile.opposite_longitude, profile.glide_slope_longitude],
            llc=threshold,
        )
        runway_length = float(np.hypot(local_x[0], local_y[0]))
        outbound = np.radians((_localizer_true_bearing(ils) + 180.0) % 360.0)
        glide_distance = float(
            local_x[1] * np.sin(outbound) + local_y[1] * np.cos(outbound)
        )
        approach_elevation = profile.glide_slope_elevation_ft + (
            side_distance - glide_distance
        ) * _FEET_PER_NAUTICAL_MILE * np.tan(np.radians(profile.glide_slope_angle_deg))
        side_axes.plot(
            (-runway_length, 0.0),
            (profile.opposite_elevation_ft, profile.threshold_elevation_ft),
            color="black",
            linewidth=4,
            label="Runway",
        )
        if plot_glide_slope:
            side_axes.plot(
                (glide_distance, side_distance),
                (profile.glide_slope_elevation_ft, approach_elevation),
                color="tab:red",
                linewidth=2,
                label=f"{profile.glide_slope_angle_deg:g}° glide slope",
            )
            side_axes.scatter(
                glide_distance,
                profile.glide_slope_elevation_ft,
                color="tab:red",
                zorder=3,
            )
        side_axes.axvline(0, color="gray", linestyle="--", linewidth=1)
        side_axes.set_title(f"{airport_id} {runway_end_id}: side view")
        side_axes.set_xlabel("NM from runway threshold")
        side_axes.set_ylabel("Elevation (ft MSL)")
        if plot_legend:
            side_axes.legend()

    if plot_legend:
        axes.legend()
    axes.set_title(f"{airport_id} {runway_end_id} localizer")
    x_label, y_label = _axis_labels(active_projection)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def plot_airport_procedures(
    nasr: Mapping[str, DataFrame],
    airport: object,
    *,
    axes: Any | None = None,
    plot_runways: bool = True,
    plot_departures: bool = True,
    plot_arrivals: bool = True,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot an airport's runways and its associated arrival/departure legs.

    ``airport`` may be an FAA identifier, an airport object with ``faa_id``, or
    a mapping with ``ARPT_ID``. Departure and STAR legs are included only when
    both endpoint identifiers resolve uniquely to a fix or navaid.

    ``plot_runways``, ``plot_departures``, and ``plot_arrivals`` select the
    layers to draw; all three are enabled by default.

    Set ``project_to_nm=True`` (or ``projection="nautical_miles"``) to use the
    local gnomonic projection in nautical miles. It defaults to the airport's
    FAA coordinate; alternatively pass a ``(latitude, longitude)``
    ``projection_center``. Use ``projection="web_mercator"`` for
    EPSG:3857-compatible x/y meters.
    Set ``plot_legend=False`` to hide the default runway/departure/arrival
    legend.
    """

    from matplotlib import pyplot as plt

    airport_id = _airport_identifier(airport)
    if not airport_id:
        raise ValueError("airport must provide a non-empty FAA identifier")
    plotting_index = _plotting_index(nasr, index)
    active_projection = _plot_projection(project_to_nm, projection)
    if active_projection == "web_mercator" and projection_center is not None:
        raise ValueError("projection_center is not used by web_mercator")
    active_projection_center = (
        projection_center
        or _airport_projection_center(nasr, airport_id, index=plotting_index)
        if active_projection == "nautical_miles"
        else None
    )
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    layers = _airport_procedure_layers(
        nasr,
        airport_id,
        plotting_index,
        plot_runways=plot_runways,
        plot_departures=plot_departures,
        plot_arrivals=plot_arrivals,
    )
    _draw_projected_layers(
        axes,
        layers,
        projection=active_projection,
        projection_center=active_projection_center,
    )
    if plot_legend and axes.get_legend_handles_labels()[0]:
        axes.legend()
    axes.set_title(f"{airport_id} procedures")
    x_label, y_label = _axis_labels(active_projection)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def plot_flight_plan(
    nasr: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    projection: PlotProjection | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot the route-field path from a submitted FAA flight plan.

    ``flight_plan`` uses the same FAA route-field syntax accepted by
    :func:`openNASR.flightplan.flight_plan_path`. Set ``project_to_nm=True``
    to use a local gnomonic projection in nautical miles. Without an explicit
    ``projection_center=(latitude, longitude)``, the route's center is used.
    Use ``projection="web_mercator"`` for EPSG:3857-compatible x/y meters.
    The returned route is source data only; it is not an operationally
    validated flight plan or clearance. Set ``plot_legend=False`` to hide the
    default flight-plan legend.
    """

    from matplotlib import pyplot as plt

    path = _plotting_index(nasr, index).flight_plan_path(flight_plan)
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    latitudes, longitudes = zip(*path)
    active_projection = _plot_projection(project_to_nm, projection)
    if active_projection == "web_mercator" and projection_center is not None:
        raise ValueError("projection_center is not used by web_mercator")
    active_projection_center = (
        _projection_center(LineString(zip(longitudes, latitudes)), projection_center)
        if active_projection == "nautical_miles"
        else None
    )
    x_values, y_values = _project_coordinates(
        longitudes,
        latitudes,
        projection=active_projection,
        center=active_projection_center,
    )
    axes.plot(
        x_values,
        y_values,
        color="tab:blue",
        marker="o",
        linewidth=1.5,
        label="Flight plan",
    )
    if plot_legend:
        axes.legend()
    axes.set_title("FAA flight plan")
    x_label, y_label = _axis_labels(active_projection)
    axes.set_xlabel(x_label)
    axes.set_ylabel(y_label)
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


__all__ = [
    "PlotProjection",
    "PlottingIndex",
    "plot_airway",
    "plot_artcc",
    "plot_airport_procedures",
    "plot_airspace",
    "plot_flight_plan",
    "plot_ils_localizer",
    "plot_runway",
    "plot_star",
]
