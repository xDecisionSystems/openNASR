"""Airway lookup and expansion between two filed points.

Private to :mod:`openNASR.flightplan`; import from there.
"""

from __future__ import annotations

from collections.abc import Mapping

from numpy import ndarray
from pandas import DataFrame

from ._route_common import _AIRWAY, _text
from .exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
)


class _AirwayIndex:
    """Snapshot the normalized AWY_BASE/AWY_SEG_ALT lookups used by one route
    session.

    ``AWY_SEG_ALT`` (the largest airway table) is indexed once by the same
    ``(REGULATORY, AWY_LOCATION, AWY_ID)`` triplet ``_airway_vertices``
    filters on, so expanding an airway never re-scans the full segment table.
    """

    def __init__(self, tables: Mapping[str, DataFrame]) -> None:
        self._base = tables.get("AWY_BASE")
        self._identifiers = (
            self._base["AWY_ID"].map(_text) if self._base is not None else None
        )
        self._segments = tables.get("AWY_SEG_ALT")
        self._segment_keys = self._segment_positions(self._segments)

    @staticmethod
    def _segment_positions(
        segments: DataFrame | None,
    ) -> dict[tuple[str, str, str], ndarray] | None:
        columns = ("REGULATORY", "AWY_LOCATION", "AWY_ID")
        if segments is None or any(column not in segments for column in columns):
            return None
        normalized = [segments[column].map(_text) for column in columns]
        return segments.groupby(normalized, sort=False).indices

    def matching(self, airway: str) -> DataFrame | None:
        match = _AIRWAY.fullmatch(airway)
        if match is None or self._base is None or self._identifiers is None:
            return None
        identifiers = {
            match["identifier"],
            f"{match['designation']}{match['identifier']}",
        }
        return self._base[self._identifiers.isin(identifiers)]

    def is_published(self, airway: str) -> bool:
        matches = self.matching(airway)
        return matches is not None and not matches.empty

    def segments(self, key: tuple[object, object, object]) -> DataFrame | None:
        """Return ``AWY_SEG_ALT`` rows for one ``(REGULATORY, AWY_LOCATION,
        AWY_ID)`` key, without re-scanning the full table."""

        if self._segments is None or self._segment_keys is None:
            return None
        regulatory, location, identifier = key
        positions = self._segment_keys.get(
            (_text(regulatory), _text(location), _text(identifier))
        )
        return self._segments.iloc[positions] if positions is not None else None


def _airway_vertices(
    tables: Mapping[str, DataFrame],
    airway: str,
    start: str,
    end: str,
    *,
    airway_index: _AirwayIndex | None = None,
) -> tuple[str, ...]:
    """Return the published segment path between two filed fixes.

    FAA route tokens print the airway family as an ``AWY_ID`` prefix (for
    example ``Q1``), while ``AWY_DESIGNATION`` is a separate NASR regulatory
    classification (often ``RN`` or ``AT`` for Q/T airways).  The prefix is
    therefore matched through ``AWY_ID``; the regulatory and location fields
    below provide the remaining cycle-specific disambiguation.
    """
    match = _AIRWAY.fullmatch(airway)
    if match is None:
        raise ValueError(f"Invalid airway token: {airway!r}")
    base = tables.get("AWY_BASE")
    segments = tables.get("AWY_SEG_ALT")
    if base is None or segments is None:
        raise RecordNotFoundError(entity_type="Airway", identifier=airway)

    if airway_index is None:
        identifiers = {
            match["identifier"],
            f"{match['designation']}{match['identifier']}",
        }
        matching_base = base[base["AWY_ID"].map(_text).isin(identifiers)]
    else:
        matching_base = airway_index.matching(airway)
        assert matching_base is not None
    matches: list[tuple[str, ...]] = []
    for key in matching_base[["REGULATORY", "AWY_LOCATION", "AWY_ID"]].itertuples(
        index=False, name=None
    ):
        if airway_index is not None:
            rows = airway_index.segments(key)
            if rows is None:
                rows = segments.iloc[0:0]
        else:
            rows = segments
            for column, value in zip(("REGULATORY", "AWY_LOCATION", "AWY_ID"), key):
                rows = rows[rows[column].map(_text).eq(_text(value))]
        ordered = sorted(
            zip(
                rows["POINT_SEQ"].to_numpy(copy=False),
                rows["FROM_POINT"].to_numpy(copy=False),
                rows["TO_POINT"].to_numpy(copy=False),
            ),
            key=lambda row: int(str(row[0])),
        )
        vertices: list[str] = []
        for _, raw_source, raw_destination in ordered:
            source, destination = _text(raw_source), _text(raw_destination)
            if not vertices or vertices[-1] != source:
                vertices.append(source)
            vertices.append(destination)
        try:
            start_index = vertices.index(start)
            end_index = vertices.index(end)
        except ValueError:
            continue
        path = vertices[start_index : end_index + 1]
        if start_index > end_index:
            path = list(reversed(vertices[end_index : start_index + 1]))
        matches.append(tuple(path))

    if not matches:
        raise RecordNotFoundError(
            entity_type="Airway path",
            identifier=airway,
            filters={"from": start, "to": end},
        )
    unique = tuple(dict.fromkeys(matches))
    if len(unique) > 1:
        raise AmbiguousRecordError(
            entity_type="Airway path", identifier=airway, candidates=unique
        )
    return unique[0]


def _is_published_airway(
    tables: Mapping[str, DataFrame],
    airway: str,
    *,
    airway_index: _AirwayIndex | None = None,
) -> bool:
    """Whether ``airway`` has a matching published airway base record."""

    match = _AIRWAY.fullmatch(airway)
    base = tables.get("AWY_BASE")
    if match is None or base is None:
        return False
    if airway_index is not None:
        return airway_index.is_published(airway)
    identifiers = {match["identifier"], f"{match['designation']}{match['identifier']}"}
    return base["AWY_ID"].map(_text).isin(identifiers).any()
