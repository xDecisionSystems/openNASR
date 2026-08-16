"""Rich objects for airport-linked FAA military-operation tables."""

from __future__ import annotations

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord, nullable_text

AIRPORT_SITE_KEY = ("SITE_NO", "SITE_TYPE_CODE")


class MilitaryOperationRecord(FaaRecord):
    """Typed conveniences for one airport-linked military-operation row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def site_no(self) -> str | None:
        return self._text("SITE_NO")

    @property
    def site_type_code(self) -> str | None:
        return self._text("SITE_TYPE_CODE")

    @property
    def airport_id(self) -> str | None:
        return self._text("ARPT_ID")

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        """Verified key shared with the corresponding ``APT_BASE`` row."""

        if self.site_no is None or self.site_type_code is None:
            return None
        return self.site_no, self.site_type_code

    @property
    def operating_code(self) -> str | None:
        return self._text("MIL_OPS_OPER_CODE")

    @property
    def call_sign(self) -> str | None:
        return self._text("MIL_OPS_CALL")

    @property
    def operating_hours(self) -> str | None:
        return self._text("MIL_OPS_HRS")


class MilitaryOperation:
    """Rich view of a ``MIL_OPS`` row linked to one airport site."""

    def __init__(self, record: MilitaryOperationRecord) -> None:
        self.record = record

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        return self.record.airport_site_key

    @property
    def airport_id(self) -> str | None:
        return self.record.airport_id

    @property
    def operating_code(self) -> str | None:
        return self.record.operating_code

    @property
    def call_sign(self) -> str | None:
        return self.record.call_sign

    @property
    def operating_hours(self) -> str | None:
        return self.record.operating_hours


class MilitaryOperationRepository:
    """Lookup military operations by their verified airport-site key."""

    entity_type = "MilitaryOperation"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["MIL_OPS"]

    def _site_key(self, identifier: object) -> tuple[object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            AIRPORT_SITE_KEY
        ):
            columns = ", ".join(AIRPORT_SITE_KEY)
            raise ValueError(f"MilitaryOperation identifiers require ({columns})")
        return identifier

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[MilitaryOperation, ...]:
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
                raise ValueError(f"Unsupported MilitaryOperation filter: {column}")
            source_column = {
                "airport_id": "ARPT_ID",
                "state": "STATE_CODE",
                "country": "COUNTRY_CODE",
            }[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(
            MilitaryOperation(MilitaryOperationRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object, **filters: object) -> MilitaryOperation:
        """Return exactly one military-operation record for a verified site key."""

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


__all__ = ["MilitaryOperation", "MilitaryOperationRepository"]
