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
from .registry import PREFERRED_ROUTE_KEY
from .records import (
    PreferredRouteRecord,
    PreferredRouteFormatRecord,
    PreferredRouteSegmentRecord,
)


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


class PreferredRoute:
    def __init__(self, record, formats, segments):
        self.record, self.formats, self.segments = record, formats, segments


class PreferredRouteRepository:
    def __init__(self, nasr):
        self._nasr = nasr

    def _rows(self, frame, key):
        rows = frame
        for col, value in zip(PREFERRED_ROUTE_KEY, key):
            rows = rows[
                rows[col]
                .map(lambda x: str(x).strip().upper())
                .eq(str(value).strip().upper())
            ]
        return rows

    def find(self, identifier=None):
        rows = (
            self._nasr["PFR_BASE"]
            if identifier is None
            else self._rows(self._nasr["PFR_BASE"], identifier)
        )
        result = []
        for row in rows.to_dict(orient="records"):
            key = tuple(row[x] for x in PREFERRED_ROUTE_KEY)
            formats = self._nasr["PFR_RMT_FMT"]
            for col, value in zip(("Orig", "Dest", "Type", "Seq"), key):
                formats = formats[
                    formats[col]
                    .map(lambda x: str(x).strip().upper())
                    .eq(str(value).strip().upper())
                ]
            segments = sorted(
                self._rows(self._nasr["PFR_SEG"], key).to_dict(orient="records"),
                key=lambda x: int(x["SEGMENT_SEQ"]),
            )
            result.append(
                PreferredRoute(
                    PreferredRouteRecord(row),
                    tuple(
                        PreferredRouteFormatRecord(x)
                        for x in formats.to_dict(orient="records")
                    ),
                    tuple(PreferredRouteSegmentRecord(x) for x in segments),
                )
            )
        return tuple(result)

    def get(self, identifier):
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="PreferredRoute", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="PreferredRoute", identifier=identifier, candidates=records
            )
        return records[0]


__all__ = [
    "CodedDepartureRoute",
    "CodedDepartureRouteRepository",
    "DepartureProcedure",
    "DepartureProcedureRepository",
    "PreferredRoute",
    "PreferredRouteRepository",
]
