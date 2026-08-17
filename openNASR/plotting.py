"""Map FAA airports and airway segments inside a geographic boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pandas import DataFrame
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from .cfcn import ll2xy
from .flightplan import flight_plan_path


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


def _coordinates(
    frame: DataFrame, identifier_column: str
) -> dict[str, list[tuple[float, float]]]:
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
    nasr: Mapping[str, DataFrame],
) -> tuple[tuple[str, LineString], ...]:
    """Resolve plotted airway segments through their fix/navaid endpoints."""

    airway_rows = nasr.get("AWY_SEG_ALT")
    if airway_rows is None or not {"FROM_POINT", "TO_POINT"}.issubset(
        airway_rows.columns
    ):
        return ()
    endpoints: dict[str, list[tuple[float, float]]] = {}
    for table, identifier in (("FIX_BASE", "FIX_ID"), ("NAV_BASE", "NAV_ID")):
        frame = nasr.get(table)
        if frame is not None:
            for name, coordinates in _coordinates(frame, identifier).items():
                endpoints.setdefault(name, []).extend(coordinates)
    designations: dict[tuple[str, str, str], str] = {}
    bases = nasr.get("AWY_BASE")
    if bases is not None:
        for row in bases.to_dict(orient="records"):
            key = (
                _text(row.get("REGULATORY")),
                _text(row.get("AWY_LOCATION")),
                _text(row.get("AWY_ID")),
            )
            designations[key] = _text(row.get("AWY_DESIGNATION"))
    segments = []
    for row in airway_rows.to_dict(orient="records"):
        starts = endpoints.get(_text(row["FROM_POINT"]), ())
        ends = endpoints.get(_text(row["TO_POINT"]), ())
        if len(starts) == 1 and len(ends) == 1 and starts[0] != ends[0]:
            key = (
                _text(row.get("REGULATORY")),
                _text(row.get("AWY_LOCATION")),
                _text(row.get("AWY_ID")),
            )
            level = "high" if designations.get(key, "") in {"J", "Q"} else "low"
            segments.append((level, LineString((starts[0], ends[0]))))
    return tuple(segments)


def _navigation_endpoints(
    nasr: Mapping[str, DataFrame],
) -> dict[str, list[tuple[float, float]]]:
    endpoints: dict[str, list[tuple[float, float]]] = {}
    for table, identifier in (("FIX_BASE", "FIX_ID"), ("NAV_BASE", "NAV_ID")):
        frame = nasr.get(table)
        if frame is not None:
            for name, coordinates in _coordinates(frame, identifier).items():
                endpoints.setdefault(name, []).extend(coordinates)
    return endpoints


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
    nasr: Mapping[str, DataFrame], airport_id: str
) -> tuple[float, float]:
    """Return the FAA latitude/longitude of an airport plotting center."""

    airports = nasr.get("APT_BASE")
    if airports is None or "ARPT_ID" not in airports.columns:
        raise ValueError("projected airport plots require APT_BASE airport coordinates")
    centers = []
    for row in airports.to_dict(orient="records"):
        if _text(row.get("ARPT_ID")) != airport_id:
            continue
        try:
            centers.append((float(row["LAT_DECIMAL"]), float(row["LONG_DECIMAL"])))
        except (KeyError, TypeError, ValueError):
            continue
    if len(centers) != 1:
        raise ValueError(
            f"projected airport plots require one coordinate for {airport_id!r}"
        )
    return centers[0]


def _procedure_segments(
    nasr: Mapping[str, DataFrame],
    airport_id: str,
    association_table: str,
    route_table: str,
    key_columns: tuple[str, ...],
) -> tuple[LineString, ...]:
    associations = nasr.get(association_table)
    routes = nasr.get(route_table)
    if associations is None or routes is None or "ARPT_ID" not in associations.columns:
        return ()
    keys = {
        tuple(_text(row.get(column)) for column in key_columns)
        for row in associations.to_dict(orient="records")
        if _text(row.get("ARPT_ID")) == airport_id
    }
    endpoints = _navigation_endpoints(nasr)
    segments = []
    for row in routes.to_dict(orient="records"):
        key = tuple(_text(row.get(column)) for column in key_columns)
        if key not in keys:
            continue
        starts = endpoints.get(_text(row.get("POINT")), ())
        ends = endpoints.get(_text(row.get("NEXT_POINT")), ())
        if len(starts) == 1 and len(ends) == 1 and starts[0] != ends[0]:
            segments.append(LineString((starts[0], ends[0])))
    return tuple(segments)


def _runway_segments(
    nasr: Mapping[str, DataFrame], airport_id: str
) -> tuple[LineString, ...]:
    ends = nasr.get("APT_RWY_END")
    if ends is None or not {
        "ARPT_ID",
        "RWY_ID",
        "LAT_DECIMAL",
        "LONG_DECIMAL",
    }.issubset(ends.columns):
        return ()
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in ends.to_dict(orient="records"):
        if _text(row.get("ARPT_ID")) != airport_id:
            continue
        try:
            point = float(row["LONG_DECIMAL"]), float(row["LAT_DECIMAL"])
        except (TypeError, ValueError):
            continue
        grouped.setdefault(_text(row.get("RWY_ID")), []).append(point)
    return tuple(
        LineString((points[0], points[1]))
        for points in grouped.values()
        if len(points) >= 2 and points[0] != points[1]
    )


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
    frame: DataFrame | None,
    geometry: BaseGeometry,
    *,
    marker: str,
    color: str,
    label: str,
    projection_center: tuple[float, float] | None,
) -> None:
    if frame is None or not {"LAT_DECIMAL", "LONG_DECIMAL"}.issubset(frame.columns):
        return
    plotted = False
    for row in frame.to_dict(orient="records"):
        try:
            point = Point(float(row["LONG_DECIMAL"]), float(row["LAT_DECIMAL"]))
        except (TypeError, ValueError):
            continue
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
    for polygon in geometries:
        if not hasattr(polygon, "exterior"):
            continue
        x_values, y_values = polygon.exterior.xy
        x_values, y_values = _project_coordinates(
            x_values, y_values, center=projection_center
        )
        axes.plot(x_values, y_values, **kwargs)


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

    if plot_airports:
        _plot_points(
            axes,
            nasr.get("APT_BASE"),
            geometry,
            marker="o",
            color="tab:blue",
            label="Airports",
            projection_center=active_projection_center,
        )
    if plot_fixes:
        _plot_points(
            axes,
            nasr.get("FIX_BASE"),
            geometry,
            marker="x",
            color="tab:green",
            label="Fixes",
            projection_center=active_projection_center,
        )
    if plot_airnavs:
        _plot_points(
            axes,
            nasr.get("NAV_BASE"),
            geometry,
            marker="^",
            color="tab:purple",
            label="Navaids",
            projection_center=active_projection_center,
        )

    airway_labels = {"high": "High-altitude airways", "low": "Low-altitude airways"}
    drawn_levels: set[str] = set()
    for level, segment in _airway_segments(nasr):
        enabled = plot_high_airways if level == "high" else plot_low_airways
        if enabled and geometry.intersects(segment):
            clipped = geometry.intersection(segment)
            for line in _line_parts(clipped):
                x_values, y_values = line.xy
                x_values, y_values = _project_coordinates(
                    x_values, y_values, center=active_projection_center
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

    if plot_legend:
        axes.legend()
    axes.set_xlabel("East (NM)" if project_to_nm else "Longitude")
    axes.set_ylabel("North (NM)" if project_to_nm else "Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


def plot_airport_procedures(
    nasr: Mapping[str, DataFrame],
    airport: object,
    *,
    axes: Any | None = None,
    project_to_nm: bool = False,
    projection_center: tuple[float, float] | None = None,
) -> tuple[Any, Any]:
    """Plot an airport's runways and its associated arrival/departure legs.

    ``airport`` may be an FAA identifier, an airport object with ``faa_id``, or
    a mapping with ``ARPT_ID``. Departure and STAR legs are included only when
    both endpoint identifiers resolve uniquely to a fix or navaid.

    Set ``project_to_nm=True`` to use the local gnomonic projection in nautical
    miles. It defaults to the airport's FAA coordinate; alternatively pass a
    ``(latitude, longitude)`` ``projection_center``.
    """

    from matplotlib import pyplot as plt

    airport_id = _airport_identifier(airport)
    if not airport_id:
        raise ValueError("airport must provide a non-empty FAA identifier")
    active_projection_center = (
        projection_center or _airport_projection_center(nasr, airport_id)
        if project_to_nm
        else None
    )
    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    for segment in _runway_segments(nasr, airport_id):
        x_values, y_values = segment.xy
        x_values, y_values = _project_coordinates(
            x_values, y_values, center=active_projection_center
        )
        axes.plot(x_values, y_values, color="black", linewidth=3)
    for segment in _procedure_segments(
        nasr,
        airport_id,
        "DP_APT",
        "DP_RTE",
        ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE"),
    ):
        x_values, y_values = segment.xy
        x_values, y_values = _project_coordinates(
            x_values, y_values, center=active_projection_center
        )
        axes.plot(x_values, y_values, color="tab:blue", linewidth=1)
    for segment in _procedure_segments(
        nasr,
        airport_id,
        "STAR_APT",
        "STAR_RTE",
        ("STAR_COMPUTER_CODE", "ARTCC"),
    ):
        x_values, y_values = segment.xy
        x_values, y_values = _project_coordinates(
            x_values, y_values, center=active_projection_center
        )
        axes.plot(x_values, y_values, color="tab:green", linewidth=1)
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
) -> tuple[Any, Any]:
    """Plot the route-field path from a submitted FAA flight plan.

    ``flight_plan`` uses the same FAA route-field syntax accepted by
    :func:`openNASR.flightplan.flight_plan_path`. Set ``project_to_nm=True``
    to use a local gnomonic projection in nautical miles. Without an explicit
    ``projection_center=(latitude, longitude)``, the route's center is used.
    The returned route is source data only; it is not an operationally
    validated flight plan or clearance.
    """

    from matplotlib import pyplot as plt

    path = flight_plan_path(nasr, flight_plan)
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
    axes.plot(x_values, y_values, color="tab:blue", marker="o", linewidth=1.5)
    axes.set_title("FAA flight plan")
    axes.set_xlabel("East (NM)" if project_to_nm else "Longitude")
    axes.set_ylabel("North (NM)" if project_to_nm else "Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


__all__ = ["plot_airport_procedures", "plot_airspace", "plot_flight_plan"]
