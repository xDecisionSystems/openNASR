"""Map FAA airports and airway segments inside a geographic boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pandas import DataFrame
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry


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


def _plot_points(
    axes: Any,
    frame: DataFrame | None,
    geometry: BaseGeometry,
    *,
    marker: str,
    color: str,
) -> None:
    if frame is None or not {"LAT_DECIMAL", "LONG_DECIMAL"}.issubset(frame.columns):
        return
    for row in frame.to_dict(orient="records"):
        try:
            point = Point(float(row["LONG_DECIMAL"]), float(row["LAT_DECIMAL"]))
        except (TypeError, ValueError):
            continue
        if geometry.covers(point):
            axes.plot(point.x, point.y, marker=marker, color=color, markersize=4)


def _plot_boundary(axes: Any, geometry: BaseGeometry, **kwargs: Any) -> None:
    geometries = geometry.geoms if hasattr(geometry, "geoms") else (geometry,)
    for polygon in geometries:
        if not hasattr(polygon, "exterior"):
            continue
        x_values, y_values = polygon.exterior.xy
        axes.plot(x_values, y_values, **kwargs)


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

    Returns
    -------
    tuple
        The Matplotlib ``(figure, axes)`` pair. Longitude is plotted on x and
        latitude on y.
    """

    geometry = _geometry(boundary)
    from matplotlib import pyplot as plt

    if axes is None:
        figure, axes = plt.subplots()
    else:
        figure = axes.figure
    _plot_boundary(axes, geometry, color="black", linewidth=1.5, label="Airspace")

    if plot_airports:
        _plot_points(axes, nasr.get("APT_BASE"), geometry, marker="o", color="tab:blue")
    if plot_fixes:
        _plot_points(
            axes, nasr.get("FIX_BASE"), geometry, marker="x", color="tab:green"
        )
    if plot_airnavs:
        _plot_points(
            axes, nasr.get("NAV_BASE"), geometry, marker="^", color="tab:purple"
        )

    for level, segment in _airway_segments(nasr):
        enabled = plot_high_airways if level == "high" else plot_low_airways
        if enabled and geometry.intersects(segment):
            x_values, y_values = segment.xy
            color = "tab:red" if level == "high" else "tab:orange"
            axes.plot(x_values, y_values, color=color, linewidth=1)

    axes.set_xlabel("Longitude")
    axes.set_ylabel("Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


__all__ = ["plot_airspace"]
