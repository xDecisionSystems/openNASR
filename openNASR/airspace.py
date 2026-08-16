"""Rich objects for airport-linked FAA airspace tables."""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import ClassAirspaceRecord
from .registry import AIRPORT_SITE_KEY


class ClassAirspace:
    """Rich view of a ``CLS_ARSP`` row linked to one airport site."""

    def __init__(self, record: ClassAirspaceRecord) -> None:
        self.record = record

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        return self.record.airport_site_key

    @property
    def airport_id(self) -> str | None:
        return self.record.airport_id

    @property
    def classes(self) -> Mapping[str, str | None]:
        return self.record.classes


class ClassAirspaceRepository:
    """Lookup class-airspace records by their verified airport-site key."""

    entity_type = "ClassAirspace"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["CLS_ARSP"]

    def _site_key(self, identifier: object) -> tuple[object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            AIRPORT_SITE_KEY
        ):
            columns = ", ".join(AIRPORT_SITE_KEY)
            raise ValueError(f"ClassAirspace identifiers require ({columns})")
        return identifier

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[ClassAirspace, ...]:
        """Return records matching a site key and every supported filter."""

        rows = self._table
        if identifier is not None:
            site_no, site_type_code = self._site_key(identifier)
            rows = rows[
                rows["SITE_NO"].map(self._normalized).eq(self._normalized(site_no))
                & rows["SITE_TYPE_CODE"]
                .map(self._normalized)
                .eq(self._normalized(site_type_code))
            ]
        for column, value in filters.items():
            if column not in {"airport_id", "state", "country"}:
                raise ValueError(f"Unsupported ClassAirspace filter: {column}")
            source_column = {
                "airport_id": "ARPT_ID",
                "state": "STATE_CODE",
                "country": "COUNTRY_CODE",
            }[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(
            ClassAirspace(ClassAirspaceRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object, **filters: object) -> ClassAirspace:
        """Return exactly one class-airspace record for a verified site key."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


__all__ = ["ClassAirspace", "ClassAirspaceRepository"]
