"""Rich access to FAA standard terminal arrival route (STAR) tables."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord


STAR_KEY = ("STAR_COMPUTER_CODE", "ARTCC")


class StarProcedureRecord(FaaRecord):
    """Lossless typed marker for a ``STAR_BASE`` procedure row."""


class StarAirportRecord(FaaRecord):
    """Lossless typed marker for a ``STAR_APT`` airport row."""


class StarRouteRecord(FaaRecord):
    """Lossless typed marker for an ordered ``STAR_RTE`` route row."""


class StarProcedure:
    """One standard terminal arrival route and its children."""

    def __init__(
        self,
        record: StarProcedureRecord,
        airports: tuple[StarAirportRecord, ...],
        routes: tuple[StarRouteRecord, ...],
    ) -> None:
        self.record = record
        self.airports = airports
        self.routes = routes

    def __str__(self) -> str:
        """Return the STAR type and FAA computer code."""

        name = self.record.raw.get("STAR_COMPUTER_CODE")
        return "StarProcedure" if not name else f"StarProcedure: {name}"

    def plot(self, nasr: Mapping[str, DataFrame], **kwargs: Any) -> tuple[Any, Any]:
        """Plot only this STAR's resolved route legs.

        Additional keyword arguments are passed to
        :func:`openNASR.plotting.plot_star`.
        """

        from .plotting import plot_star

        return plot_star(nasr, self, **kwargs)


class StarProcedureRepository:
    """Look up STAR procedures by their complete FAA composite key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normal(value: object) -> str:
        return str(value).strip().upper()

    def _rows(self, frame: DataFrame, key: tuple[object, ...]) -> DataFrame:
        rows = frame
        for column, value in zip(STAR_KEY, key):
            rows = rows[rows[column].map(self._normal).eq(self._normal(value))]
        return rows

    def find(
        self, identifier: tuple[object, ...] | None = None
    ) -> tuple[StarProcedure, ...]:
        if identifier is not None and len(identifier) != len(STAR_KEY):
            raise ValueError(f"STAR identifiers require ({', '.join(STAR_KEY)})")
        rows = (
            self._nasr["STAR_BASE"]
            if identifier is None
            else self._rows(self._nasr["STAR_BASE"], identifier)
        )
        result: list[StarProcedure] = []
        for row in rows.to_dict(orient="records"):
            key = tuple(row[column] for column in STAR_KEY)
            airports = self._rows(self._nasr["STAR_APT"], key).to_dict(orient="records")
            routes = self._rows(self._nasr["STAR_RTE"], key).to_dict(orient="records")
            routes.sort(
                key=lambda item: (int(item["BODY_SEQ"]), int(item["POINT_SEQ"]))
            )
            result.append(
                StarProcedure(
                    StarProcedureRecord(row),
                    tuple(StarAirportRecord(item) for item in airports),
                    tuple(StarRouteRecord(item) for item in routes),
                )
            )
        return tuple(result)

    def get(self, identifier: tuple[object, ...]) -> StarProcedure:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="StarProcedure", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="StarProcedure", identifier=identifier, candidates=records
            )
        return records[0]


__all__ = [
    "StarAirportRecord",
    "StarProcedure",
    "StarProcedureRecord",
    "StarProcedureRepository",
    "StarRouteRecord",
]
