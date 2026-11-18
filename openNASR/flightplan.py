"""Resolve FAA route-field text into geographic paths.

This module resolves the navigation portion of a filed domestic FAA flight
plan against one loaded NASR cycle. It deliberately does not validate a
flight plan for operational use.

The implementation is split by layer (``_route_common``, ``_route_waypoints``,
``_route_airways``, ``_route_procedures``, ``_route_tokenizer``,
``_route_resolver``); this module is the stable import point.
"""

from __future__ import annotations

from ._route_common import _RouteToken, _text  # noqa: F401
from ._route_procedures import (  # noqa: F401
    _is_published_dotted_procedure,
    _procedure_path,
    _ProcedureIndex,
)
from ._route_resolver import ROUTE_TABLES, RouteResolver, flight_plan_path
from ._route_tokenizer import _tokenize_flight_plan  # noqa: F401
from ._route_waypoints import _WaypointResolver  # noqa: F401

__all__ = ["ROUTE_TABLES", "RouteResolver", "flight_plan_path"]
