"""Rich access to FAA departure and preferred-route tables."""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .indexing import (
    NormalizedIndexCache,
    cached_normalized_column_index,
    normalized_indexed_rows,
    normalized_index_rows,
)
from .records import FaaRecord, nullable_text


DEPARTURE_KEY = ("DP_NAME", "ARTCC", "DP_COMPUTER_CODE")
PREFERRED_ROUTE_KEY = ("ORIGIN_ID", "DSTN_ID", "PFR_TYPE_CODE", "ROUTE_NO")


class CodedDepartureRouteRecord(FaaRecord):
    """Typed conveniences for a standalone ``CDR`` coded departure route."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def route_code(self) -> str | None:
        return self._text("RCode")

    @property
    def origin(self) -> str | None:
        return self._text("Orig")

    @property
    def destination(self) -> str | None:
        return self._text("Dest")


class DepartureProcedureRecord(FaaRecord):
    """Lossless typed marker for a ``DP_BASE`` departure procedure row."""


class DepartureAirportRecord(FaaRecord):
    """Lossless typed marker for a ``DP_APT`` departure airport row."""


class DepartureRouteRecord(FaaRecord):
    """Lossless typed marker for an ordered ``DP_RTE`` departure route row."""


class PreferredRouteRecord(FaaRecord):
    """Lossless typed marker for a ``PFR_BASE`` preferred route row."""


class PreferredRouteFormatRecord(FaaRecord):
    """Lossless typed marker for a ``PFR_RMT_FMT`` route-format row."""


class PreferredRouteSegmentRecord(FaaRecord):
    """Lossless typed marker for an ordered ``PFR_SEG`` route segment row."""


class CodedDepartureRoute:
    """One standalone FAA coded departure route."""

    def __init__(self, record: CodedDepartureRouteRecord) -> None:
        self.record = record


class CodedDepartureRouteRepository:
    """Look up coded departure routes by their unique FAA route code."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._indexes: NormalizedIndexCache = {}

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def find(self, identifier: str | None = None) -> tuple[CodedDepartureRoute, ...]:
        rows = self._nasr["CDR"]
        if identifier is not None:
            index = cached_normalized_column_index(
                self._indexes, rows, "RCode", self._normalized
            )
            rows = normalized_index_rows(rows, index, identifier, self._normalized)
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

    def __init__(
        self,
        record: DepartureProcedureRecord,
        airports: tuple[DepartureAirportRecord, ...],
        routes: tuple[DepartureRouteRecord, ...],
    ) -> None:
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
        result: list[DepartureProcedure] = []
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
    """A preferred route with format rows and ordered segments."""

    def __init__(
        self,
        record: PreferredRouteRecord,
        formats: tuple[PreferredRouteFormatRecord, ...],
        segments: tuple[PreferredRouteSegmentRecord, ...],
    ) -> None:
        self.record = record
        self.formats = formats
        self.segments = segments


class PreferredRouteRepository:
    """Look up preferred routes by their complete FAA composite key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._indexes: NormalizedIndexCache = {}

    @staticmethod
    def _normal(value: object) -> str:
        return str(value).strip().upper()

    def _rows(
        self,
        frame: DataFrame,
        key: tuple[object, ...],
        *,
        columns: tuple[str, ...] = PREFERRED_ROUTE_KEY,
    ) -> DataFrame:
        return normalized_indexed_rows(
            self._indexes, frame, zip(columns, key), self._normal
        )

    def find(
        self, identifier: tuple[object, ...] | None = None
    ) -> tuple[PreferredRoute, ...]:
        if identifier is not None and len(identifier) != len(PREFERRED_ROUTE_KEY):
            raise ValueError(
                "Preferred route identifiers require "
                f"({', '.join(PREFERRED_ROUTE_KEY)})"
            )
        rows = (
            self._nasr["PFR_BASE"]
            if identifier is None
            else self._rows(self._nasr["PFR_BASE"], identifier)
        )
        result: list[PreferredRoute] = []
        for row in rows.to_dict(orient="records"):
            key = tuple(row[column] for column in PREFERRED_ROUTE_KEY)
            formats = self._rows(
                self._nasr["PFR_RMT_FMT"],
                key,
                columns=("Orig", "Dest", "Type", "Seq"),
            )
            segments = self._rows(self._nasr["PFR_SEG"], key).to_dict(orient="records")
            segments.sort(key=lambda item: int(item["SEGMENT_SEQ"]))
            result.append(
                PreferredRoute(
                    PreferredRouteRecord(row),
                    tuple(
                        PreferredRouteFormatRecord(item)
                        for item in formats.to_dict(orient="records")
                    ),
                    tuple(PreferredRouteSegmentRecord(item) for item in segments),
                )
            )
        return tuple(result)

    def get(self, identifier: tuple[object, ...]) -> PreferredRoute:
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
]
