"""Structured route-resolution result: points, diagnostics and completeness."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoutePoint:
    """One resolved point and where it came from.

    ``kind`` is the NASR record type (``airport``, ``fix``, ``navaid``) or
    ``latlon`` for a coordinate filed in the route. ``via`` is the airway or
    procedure token that produced the point (``None`` for a point filed
    directly), and ``segment`` places it in the flight.
    """

    lat: float
    lon: float
    name: str
    kind: str
    via: str | None
    segment: str  # origin | departure | enroute | arrival | destination


@dataclass(frozen=True)
class RouteDiagnostic:
    """One thing the resolver could not do exactly, or did only partly."""

    code: str
    message: str
    token: str | None = None
    position: int | None = None
    detail: dict[str, object] = field(default_factory=dict)
    severity: str = "warning"
    """``"info"`` notes how a point was derived and does not make the route
    incomplete; ``"warning"`` means part of the route is missing or unresolved."""


@dataclass(frozen=True)
class RouteResult:
    """The outcome of resolving one route against one cycle.

    ``complete`` is ``True`` only when every part of the route was resolved
    exactly. A route with a warning diagnostic is never complete: its ``points``
    hold what could be resolved without guessing (empty when resolution
    stopped). Diagnostics of severity ``"info"`` do not affect completeness.
    """

    route: str
    cycle: str | None
    points: tuple[tuple[float, float], ...]
    diagnostics: tuple[RouteDiagnostic, ...] = ()
    waypoints: tuple[RoutePoint, ...] = ()
    """The same points as ``points``, with provenance."""

    @property
    def complete(self) -> bool:
        return all(item.severity == "info" for item in self.diagnostics)
