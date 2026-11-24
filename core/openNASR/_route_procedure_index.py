"""Ordered DP and STAR table indexes for one route resolver."""

from __future__ import annotations

from collections.abc import Mapping

from numpy import ndarray
from pandas import DataFrame

from ._route_common import _ROUTE_AIRPORTS, _text


def _narrow_to_route_airports(
    keys: set[tuple[str, ...]],
    served: dict[tuple[str, ...], frozenset[str]],
) -> set[tuple[str, ...]]:
    """Keep the procedures serving a route-end airport, if that decides it."""

    airports = _ROUTE_AIRPORTS.get()
    if len(keys) <= 1 or not airports:
        return keys
    kept = {key for key in keys if served.get(key, frozenset()) & airports}
    return kept or keys


class _ProcedureIndex:
    """Snapshot normalized procedure-table lookups for one route session.

    The position arrays retain each source table's ordering without eagerly
    materializing a DataFrame per procedure code.
    """

    @staticmethod
    def _served_airports(
        frame: DataFrame | None, key_columns: tuple[str, ...]
    ) -> dict[tuple[str, ...], frozenset[str]]:
        columns = (*key_columns, "ARPT_ID")
        if frame is None or any(column not in frame for column in columns):
            return {}
        served: dict[tuple[str, ...], set[str]] = {}
        for *key, airport in zip(*(frame[c].map(_text).to_numpy() for c in columns)):
            served.setdefault(tuple(key), set()).add(airport)
        return {key: frozenset(value) for key, value in served.items()}

    def narrow_departures(self, keys: set[tuple[str, ...]]) -> set[tuple[str, ...]]:
        return _narrow_to_route_airports(keys, self._served_departures)

    def narrow_bodies(
        self, entity_type: str, rows: DataFrame, names: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Keep the named bodies that serve a route-end airport, if any do."""

        airports = _ROUTE_AIRPORTS.get()
        departure = entity_type == "DepartureProcedure"
        columns = (
            ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
            if departure
            else ("STAR_COMPUTER_CODE", "ARTCC")
        )
        if not airports or rows.empty or any(c not in rows for c in columns):
            return names
        prefix = tuple(_text(rows[column].iloc[0]) for column in columns)
        served = (
            self._served_departure_bodies if departure else self._served_star_bodies
        )
        kept = tuple(
            name
            for name in names
            if served.get((*prefix, name), frozenset()) & airports
        )
        return kept or names

    def narrow_stars(self, keys: set[tuple[str, ...]]) -> set[tuple[str, ...]]:
        return _narrow_to_route_airports(keys, self._served_stars)

    def stars_joined_at(self, point: str, name: str) -> set[tuple[str, str]]:
        """STARs called ``name`` (short name) that contain ``point``."""

        return {
            key
            for key in self._stars_by_name.get(_text(name), set())
            if _text(point) in self._star_points.get(key, frozenset())
        }

    def star_transitions(self, code: object, artcc: object) -> DataFrame | None:
        return self._matching_composite(
            self._star_routes, self._star_portions, (code, artcc, "TRANSITION")
        )

    def __init__(self, tables: Mapping[str, DataFrame]) -> None:
        self._served_departures = self._served_airports(
            tables.get("DP_APT"), ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
        )
        self._served_stars = self._served_airports(
            tables.get("STAR_APT"), ("STAR_COMPUTER_CODE", "ARTCC")
        )
        self._served_departure_bodies = self._served_airports(
            tables.get("DP_APT"), ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE", "BODY_NAME")
        )
        self._served_star_bodies = self._served_airports(
            tables.get("STAR_APT"), ("STAR_COMPUTER_CODE", "ARTCC", "BODY_NAME")
        )
        self._departures = tables.get("DP_BASE")
        self._departure_routes = tables.get("DP_RTE")
        self._stars = tables.get("STAR_BASE")
        self._star_routes = tables.get("STAR_RTE")
        self._departure_codes = self._positions(self._departures, "DP_COMPUTER_CODE")
        self._departure_transitions = self._positions(
            self._departure_routes, "TRANSITION_COMPUTER_CODE"
        )
        self._star_codes = self._positions(self._stars, "STAR_COMPUTER_CODE")
        self._star_transitions = self._positions(
            self._star_routes, "TRANSITION_COMPUTER_CODE"
        )
        self._departure_route_keys = self._composite_positions(
            self._departure_routes, ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
        )
        self._departure_bodies = self._composite_positions(
            self._departure_routes,
            ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE", "ROUTE_PORTION_TYPE"),
        )
        self._departure_route_transitions = self._composite_positions(
            self._departure_routes,
            (
                "DP_NAME",
                "ARTCC",
                "DP_COMPUTER_CODE",
                "TRANSITION_COMPUTER_CODE",
            ),
        )
        self._star_bodies = self._composite_positions(
            self._star_routes,
            ("STAR_COMPUTER_CODE", "ARTCC", "ROUTE_PORTION_TYPE"),
        )
        self._star_route_transitions = self._composite_positions(
            self._star_routes,
            ("STAR_COMPUTER_CODE", "ARTCC", "TRANSITION_COMPUTER_CODE"),
        )
        self._star_portions = self._composite_positions(
            self._star_routes,
            ("STAR_COMPUTER_CODE", "ARTCC", "ROUTE_PORTION_TYPE"),
        )
        # STARs by their short name (``OZZZI2`` for code ``OZZZI.OZZZI2``) and
        # the points each one contains, for routes that join a STAR at a fix
        # inside one of its transitions or its body (FAA SWIM / ERAM amended
        # routes, for example ``SCHUL.OZZZI2``).
        self._stars_by_name: dict[str, set[tuple[str, str]]] = {}
        self._star_points: dict[tuple[str, str], frozenset[str]] = {}
        routes = self._star_routes
        if routes is not None and all(
            column in routes for column in ("STAR_COMPUTER_CODE", "ARTCC", "POINT")
        ):
            points: dict[tuple[str, str], set[str]] = {}
            for code, artcc, point in zip(
                routes["STAR_COMPUTER_CODE"].map(_text).to_numpy(),
                routes["ARTCC"].map(_text).to_numpy(),
                routes["POINT"].map(_text).to_numpy(),
            ):
                key = (code, artcc)
                self._stars_by_name.setdefault(code.rsplit(".", 1)[-1], set()).add(key)
                points.setdefault(key, set()).add(point)
            self._star_points = {k: frozenset(v) for k, v in points.items()}

    @staticmethod
    def _positions(frame: DataFrame | None, column: str) -> dict[str, ndarray] | None:
        if frame is None or column not in frame:
            return None
        return frame.groupby(frame[column].map(_text), sort=False).indices

    @staticmethod
    def _matching(
        frame: DataFrame | None,
        positions: dict[str, ndarray] | None,
        token: str,
    ) -> DataFrame | None:
        if frame is None or positions is None:
            return None
        matches = positions.get(_text(token))
        return frame.iloc[matches] if matches is not None else frame.iloc[0:0]

    @staticmethod
    def _composite_positions(
        frame: DataFrame | None, columns: tuple[str, ...]
    ) -> dict[tuple[str, ...], ndarray] | None:
        if frame is None or any(column not in frame for column in columns):
            return None
        normalized = [frame[column].map(_text) for column in columns]
        return frame.groupby(normalized, sort=False).indices

    @staticmethod
    def _matching_composite(
        frame: DataFrame | None,
        positions: dict[tuple[str, ...], ndarray] | None,
        values: tuple[object, ...],
    ) -> DataFrame | None:
        if frame is None or positions is None:
            return None
        matches = positions.get(tuple(_text(value) for value in values))
        return frame.iloc[matches] if matches is not None else frame.iloc[0:0]

    def departure_base(self, token: str) -> DataFrame | None:
        return self._matching(self._departures, self._departure_codes, token)

    def departure_transition(self, token: str) -> DataFrame | None:
        return self._matching(
            self._departure_routes, self._departure_transitions, token
        )

    def star_base(self, token: str) -> DataFrame | None:
        return self._matching(self._stars, self._star_codes, token)

    def star_transition(self, token: str) -> DataFrame | None:
        return self._matching(self._star_routes, self._star_transitions, token)

    def departure_route(
        self, name: object, artcc: object, code: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._departure_routes, self._departure_route_keys, (name, artcc, code)
        )

    def departure_body(
        self, name: object, artcc: object, code: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._departure_routes,
            self._departure_bodies,
            (name, artcc, code, "BODY"),
        )

    def departure_route_transition(
        self, name: object, artcc: object, code: object, transition: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._departure_routes,
            self._departure_route_transitions,
            (name, artcc, code, transition),
        )

    def star_body(self, code: object, artcc: object) -> DataFrame | None:
        return self._matching_composite(
            self._star_routes, self._star_bodies, (code, artcc, "BODY")
        )

    def star_route_transition(
        self, code: object, artcc: object, transition: object
    ) -> DataFrame | None:
        return self._matching_composite(
            self._star_routes,
            self._star_route_transitions,
            (code, artcc, transition),
        )
