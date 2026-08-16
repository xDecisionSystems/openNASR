"""Rich access to FAA coded departure routes and procedure tables."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import CodedDepartureRouteRecord
from .records import (
    DepartureAirportRecord,
    DepartureProcedureRecord,
    DepartureRouteRecord,
)
from .registry import DEPARTURE_KEY


class CodedDepartureRoute:
    """One standalone FAA coded departure route."""

    def __init__(self, record: CodedDepartureRouteRecord) -> None:
        self.record = record


class CodedDepartureRouteRepository:
    """Look up coded departure routes by their unique FAA route code."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def find(self, identifier: str | None = None) -> tuple[CodedDepartureRoute, ...]:
        rows = self._nasr["CDR"]
        if identifier is not None:
            rows = rows[
                rows["RCode"].map(self._normalized).eq(self._normalized(identifier))
            ]
        return tuple(
            CodedDepartureRoute(CodedDepartureRouteRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: str) -> CodedDepartureRoute:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="CodedDepartureRoute", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="CodedDepartureRoute",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


class DepartureProcedure:
    """One departure procedure with airport associations and ordered routes."""

    def __init__(self, record, airports, routes) -> None:
        self.record = record
        self.airports = airports
        self.routes = routes


class DepartureProcedureRepository:
    """Look up departure procedures by their complete FAA composite key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normal(value: object) -> str:
        return str(value).strip().upper()

    def _rows(self, frame: DataFrame, key: tuple[object, ...]) -> DataFrame:
        rows = frame
        for column, value in zip(DEPARTURE_KEY, key):
            rows = rows[rows[column].map(self._normal).eq(self._normal(value))]
        return rows

    def find(self, identifier: object | None = None) -> tuple[DepartureProcedure, ...]:
        rows = self._nasr["DP_BASE"]
        if identifier is not None:
            if not isinstance(identifier, tuple) or len(identifier) != len(
                DEPARTURE_KEY
            ):
                raise ValueError(
                    f"Departure identifiers require ({', '.join(DEPARTURE_KEY)})"
                )
            rows = self._rows(rows, identifier)
        result = []
        for row in rows.to_dict(orient="records"):
            key = tuple(row[column] for column in DEPARTURE_KEY)
            airports = self._rows(self._nasr["DP_APT"], key).to_dict(orient="records")
            routes = self._rows(self._nasr["DP_RTE"], key).to_dict(orient="records")
            routes.sort(
                key=lambda item: (int(item["BODY_SEQ"]), int(item["POINT_SEQ"]))
            )
            result.append(
                DepartureProcedure(
                    DepartureProcedureRecord(row),
                    tuple(DepartureAirportRecord(item) for item in airports),
                    tuple(DepartureRouteRecord(item) for item in routes),
                )
            )
        return tuple(result)

    def get(self, identifier: object) -> DepartureProcedure:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="DepartureProcedure", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="DepartureProcedure",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


__all__ = [
    "CodedDepartureRoute",
    "CodedDepartureRouteRepository",
    "DepartureProcedure",
    "DepartureProcedureRepository",
]
