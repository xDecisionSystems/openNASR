"""Rich access to standalone FAA communication and frequency tables."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import CommunicationOutletRecord, FrequencyRecord
from .registry import FREQUENCY_KEY


class CommunicationOutlet:
    """One communication-outlet record."""

    def __init__(self, record: CommunicationOutletRecord) -> None:
        self.record = record


class CommunicationOutletRepository:
    """Look up communication outlets by their FAA communication location ID."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def find(self, identifier: str | None = None) -> tuple[CommunicationOutlet, ...]:
        rows = self._nasr["COM"]
        if identifier is not None:
            rows = rows[
                rows["COMM_LOC_ID"]
                .map(self._normalized)
                .eq(self._normalized(identifier))
            ]
        return tuple(
            CommunicationOutlet(CommunicationOutletRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: str) -> CommunicationOutlet:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="CommunicationOutlet", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="CommunicationOutlet",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


class Frequency:
    """One frequency-assignment record."""

    def __init__(self, record: FrequencyRecord) -> None:
        self.record = record


class FrequencyRepository:
    """Look up frequency assignments by their complete FAA composite key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, object, object, object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(FREQUENCY_KEY):
            raise ValueError(
                f"Frequency identifiers require ({', '.join(FREQUENCY_KEY)})"
            )
        return identifier

    def _matching(
        self, frame: DataFrame, key: tuple[object, object, object, object, object]
    ) -> DataFrame:
        rows = frame
        for column, value in zip(FREQUENCY_KEY, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    def find(self, identifier: object | None = None) -> tuple[Frequency, ...]:
        rows = self._nasr["FRQ"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(
            Frequency(FrequencyRecord(row)) for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object) -> Frequency:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(entity_type="Frequency", identifier=identifier)
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="Frequency", identifier=identifier, candidates=records
            )
        return records[0]


__all__ = [
    "CommunicationOutlet",
    "CommunicationOutletRepository",
    "Frequency",
    "FrequencyRepository",
]
