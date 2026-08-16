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


def _airway_segments(nasr: Mapping[str, DataFrame]) -> tuple[LineString, ...]:
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
    segments = []
    for row in airway_rows.to_dict(orient="records"):
        starts = endpoints.get(_text(row["FROM_POINT"]), ())
        ends = endpoints.get(_text(row["TO_POINT"]), ())
        if len(starts) == 1 and len(ends) == 1 and starts[0] != ends[0]:
            segments.append(LineString((starts[0], ends[0])))
    return tuple(segments)


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

    airports = nasr.get("APT_BASE")
    if airports is not None:
        for row in airports.to_dict(orient="records"):
            try:
                point = Point(float(row["LONG_DECIMAL"]), float(row["LAT_DECIMAL"]))
            except (KeyError, TypeError, ValueError):
                continue
            if geometry.covers(point):
                axes.plot(point.x, point.y, marker="o", color="tab:blue", markersize=4)

    for segment in _airway_segments(nasr):
        if geometry.intersects(segment):
            x_values, y_values = segment.xy
            axes.plot(x_values, y_values, color="tab:orange", linewidth=1)

    axes.set_xlabel("Longitude")
    axes.set_ylabel("Latitude")
    axes.set_aspect("equal", adjustable="datalim")
    return figure, axes


__all__ = ["plot_airspace"]
