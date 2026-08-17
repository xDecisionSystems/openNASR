"""Rich access to FAA location identifiers."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .indexing import NormalizedIndexCache, normalized_indexed_rows
from .records import FaaRecord


LOCATION_IDENTIFIER_KEY = (
    "COUNTRY_CODE",
    "LOC_ID",
    "REGION_CODE",
    "STATE",
    "CITY",
    "LID_GROUP",
    "FAC_TYPE",
)


class LocationIdentifierRecord(FaaRecord):
    """Lossless typed marker for a location-identifier row."""


class LocationIdentifier:
    """One standalone FAA location-identifier record."""

    def __init__(self, record: LocationIdentifierRecord) -> None:
        self.record = record


class LocationIdentifierRepository:
    """Look up location identifiers by their complete verified FAA key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._indexes: NormalizedIndexCache = {}

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, ...]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            LOCATION_IDENTIFIER_KEY
        ):
            raise ValueError(
                "Location-identifier identifiers require "
                f"({', '.join(LOCATION_IDENTIFIER_KEY)})"
            )
        return identifier

    def _matching(self, frame: DataFrame, key: tuple[object, ...]) -> DataFrame:
        return normalized_indexed_rows(
            self._indexes, frame, zip(LOCATION_IDENTIFIER_KEY, key), self._normalized
        )

    def find(self, identifier: object | None = None) -> tuple[LocationIdentifier, ...]:
        rows = self._nasr["LID"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(
            LocationIdentifier(LocationIdentifierRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object) -> LocationIdentifier:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="LocationIdentifier", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="LocationIdentifier",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


__all__ = [
    "LocationIdentifier",
    "LocationIdentifierRecord",
    "LocationIdentifierRepository",
]
