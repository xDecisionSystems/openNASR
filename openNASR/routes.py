"""Rich access to FAA coded departure routes and procedure tables."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import CodedDepartureRouteRecord


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


__all__ = ["CodedDepartureRoute", "CodedDepartureRouteRepository"]
