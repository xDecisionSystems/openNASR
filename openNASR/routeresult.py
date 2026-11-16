"""Structured route-resolution result: points, diagnostics and completeness."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteDiagnostic:
    """One thing the resolver could not do exactly, or did only partly."""

    code: str
    message: str
    token: str | None = None
    position: int | None = None
    detail: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteResult:
    """The outcome of resolving one route against one cycle.

    ``complete`` is ``True`` only when every part of the route was resolved
    exactly. A route with a diagnostic is never complete: its ``points`` hold
    what could be resolved without guessing (empty when resolution stopped).
    """

    route: str
    cycle: str | None
    points: tuple[tuple[float, float], ...]
    diagnostics: tuple[RouteDiagnostic, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.diagnostics
