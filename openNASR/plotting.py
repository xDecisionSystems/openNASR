"""Map FAA airports and airway segments inside a geographic boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from numpy import ndarray
from pandas import DataFrame, Series
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from .cfcn import ll2xy
from .flightplan import RouteResolver
from .indexing import (
    NormalizedIndexCache,
    cached_normalized_column_index,
    normalized_index_rows,
)


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
        for source, destination, regulatory, location, identifier in zip(*values):
            starts = endpoints.get(_text(source), ())
            ends = endpoints.get(_text(destination), ())
            if len(starts) == 1 and len(ends) == 1 and starts[0] != ends[0]:
                key = _text(regulatory), _text(location), _text(identifier)
                level = "high" if designations.get(key, "") in {"J", "Q"} else "low"
                segments.append((level, LineString((starts[0], ends[0]))))
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
                segments.append(LineString((starts[0], ends[0])))
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
    index: PlottingIndex | None = None,
) -> tuple[LineString, ...]:
    return _plotting_index(nasr, index).procedure_segments(
        airport_id, association_table, route_table, key_columns
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
    longitudes: Any, latitudes: Any, *, center: tuple[float, float] | None
) -> tuple[Any, Any]:
    """Project longitude/latitude coordinates to NM when a center is supplied."""

    if center is None:
        return longitudes, latitudes
    x_values, y_values, _, _ = ll2xy(latitudes, longitudes, llc=center)
    return x_values, y_values


def _plot_points(
    axes: Any,
    coordinates: tuple[tuple[float, float], ...],
    geometry: BaseGeometry,
    *,
    marker: str,
    color: str,
    label: str,
    projection_center: tuple[float, float] | None,
) -> None:
    plotted = False
    for longitude, latitude in coordinates:
        point = Point(longitude, latitude)
        if geometry.covers(point):
            x_values, y_values = _project_coordinates(
                point.x, point.y, center=projection_center
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
            x_values, y_values, center=projection_center
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
                x_values, y_values, center=projection_center
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

    Returns
    -------
    tuple
        The Matplotlib ``(figure, axes)`` pair. Coordinates are longitude and
        latitude by default, or east/north nautical miles when projected.
    """

    plotting_index = _plotting_index(nasr, index)
    geometry = _geometry(boundary)
    active_projection_center = (
        _projection_center(geometry, projection_center) if project_to_nm else None
    )
    from matplotlib import pyplot as plt

    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    _plot_boundary(
        axes,
        geometry,
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
            projection_center=active_projection_center,
        )

    if plot_legend:
        axes.legend()
    axes.set_xlabel("East (NM)" if project_to_nm else "Longitude")
    axes.set_ylabel("North (NM)" if project_to_nm else "Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def _airport_procedure_layers(
    nasr: Mapping[str, DataFrame], airport_id: str, plotting_index: PlottingIndex
) -> tuple[tuple[tuple[LineString, ...], str, int, str], ...]:
    """Return (segments, color, linewidth, label) for each procedure layer."""

    return (
        (
            _runway_segments(nasr, airport_id, index=plotting_index),
            "black",
            3,
            "Runways",
        ),
        (
            _procedure_segments(
                nasr,
                airport_id,
                "DP_APT",
                "DP_RTE",
                ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE"),
                index=plotting_index,
            ),
            "tab:blue",
            1,
            "Departures",
        ),
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


def _draw_projected_layers(
    axes: Any,
    layers: tuple[tuple[tuple[LineString, ...], str, int, str], ...],
    *,
    projection_center: tuple[float, float] | None,
) -> None:
    """Draw each layer's line segments, labeling only the first per layer."""

    for segments, color, linewidth, label in layers:
        plotted = False
        for segment in segments:
            x_values, y_values = segment.xy
            x_values, y_values = _project_coordinates(
                x_values, y_values, center=projection_center
            )
            axes.plot(
                x_values,
                y_values,
                color=color,
                linewidth=linewidth,
                label=None if plotted else label,
            )
            plotted = True


def plot_airport_procedures(
    nasr: Mapping[str, DataFrame],
    airport: object,
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot an airport's runways and its associated arrival/departure legs.

    ``airport`` may be an FAA identifier, an airport object with ``faa_id``, or
    a mapping with ``ARPT_ID``. Departure and STAR legs are included only when
    both endpoint identifiers resolve uniquely to a fix or navaid.

    Set ``project_to_nm=True`` to use the local gnomonic projection in nautical
    miles. It defaults to the airport's FAA coordinate; alternatively pass a
    ``(latitude, longitude)`` ``projection_center``.
    Set ``plot_legend=False`` to hide the default runway/departure/arrival
    legend.
    """

    from matplotlib import pyplot as plt

    airport_id = _airport_identifier(airport)
    if not airport_id:
        raise ValueError("airport must provide a non-empty FAA identifier")
    plotting_index = _plotting_index(nasr, index)
    active_projection_center = (
        projection_center
        or _airport_projection_center(nasr, airport_id, index=plotting_index)
        if project_to_nm
        else None
    )
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    layers = _airport_procedure_layers(nasr, airport_id, plotting_index)
    _draw_projected_layers(axes, layers, projection_center=active_projection_center)
    if plot_legend and axes.get_legend_handles_labels()[0]:
        axes.legend()
    axes.set_title(f"{airport_id} procedures")
    axes.set_xlabel("East (NM)" if project_to_nm else "Longitude")
    axes.set_ylabel("North (NM)" if project_to_nm else "Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def plot_flight_plan(
    nasr: Mapping[str, DataFrame],
    flight_plan: str,
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
    plot_legend: bool = True,
    index: PlottingIndex | None = None,
) -> tuple[Any, Any]:
    """Plot the route-field path from a submitted FAA flight plan.

    ``flight_plan`` uses the same FAA route-field syntax accepted by
    :func:`openNASR.flightplan.flight_plan_path`. Set ``project_to_nm=True``
    to use a local gnomonic projection in nautical miles. Without an explicit
    ``projection_center=(latitude, longitude)``, the route's center is used.
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
    active_projection_center = (
        _projection_center(LineString(zip(longitudes, latitudes)), projection_center)
        if project_to_nm
        else None
    )
    x_values, y_values = _project_coordinates(
        longitudes, latitudes, center=active_projection_center
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
    axes.set_xlabel("East (NM)" if project_to_nm else "Longitude")
    axes.set_ylabel("North (NM)" if project_to_nm else "Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


__all__ = [
    "PlottingIndex",
    "plot_airport_procedures",
    "plot_airspace",
    "plot_flight_plan",
]
