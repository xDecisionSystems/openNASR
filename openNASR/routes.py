"""Backward-compatible procedure API; use :mod:`departure` or :mod:`arrivals`."""

from .arrivals import (
    StarAirportRecord,
    StarProcedure,
    StarProcedureRecord,
    StarProcedureRepository,
    StarRouteRecord,
)
from .departure import (
    CodedDepartureRoute,
    CodedDepartureRouteRecord,
    CodedDepartureRouteRepository,
    DepartureAirportRecord,
    DepartureProcedure,
    DepartureProcedureRecord,
    DepartureProcedureRepository,
    DepartureRouteRecord,
    PreferredRoute,
    PreferredRouteFormatRecord,
    PreferredRouteRecord,
    PreferredRouteRepository,
    PreferredRouteSegmentRecord,
)

__all__ = [
    "CodedDepartureRoute",
    "CodedDepartureRouteRecord",
    "CodedDepartureRouteRepository",
    "DepartureAirportRecord",
    "DepartureProcedure",
    "DepartureProcedureRecord",
    "DepartureProcedureRepository",
    "DepartureRouteRecord",
    "PreferredRoute",
    "PreferredRouteFormatRecord",
    "PreferredRouteRecord",
    "PreferredRouteRepository",
    "PreferredRouteSegmentRecord",
    "StarAirportRecord",
    "StarProcedure",
    "StarProcedureRecord",
    "StarProcedureRepository",
    "StarRouteRecord",
]
