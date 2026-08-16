"""Rich access to FAA air-traffic-control facility records."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import AtcFacilityRecord, AtcRemarkRecord, AtcServiceRecord, AtisRecord
from .registry import ATC_KEY


class AtcFacility:
    """One ATC facility with its ATIS, remarks, and service rows."""

    def __init__(
        self,
        record: AtcFacilityRecord,
        *,
        atis_services: tuple[AtisRecord, ...],
        remarks: tuple[AtcRemarkRecord, ...],
        services: tuple[AtcServiceRecord, ...],
    ) -> None:
        self.record = record
        self.atis_services = atis_services
        self.remarks = remarks
        self.services = services


class AtcFacilityRepository:
    """Look up ATC facilities by their complete verified FAA key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, ...]:
        if not isinstance(identifier, tuple) or len(identifier) != len(ATC_KEY):
            raise ValueError(f"ATC facility identifiers require ({', '.join(ATC_KEY)})")
        return identifier

    def _matching(self, frame: DataFrame, key: tuple[object, ...]) -> DataFrame:
        rows = frame
        for column, value in zip(ATC_KEY, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    @staticmethod
    def _remark_order(row: dict[str, object]) -> tuple[int, str, str]:
        number = row.get("REMARK_NO")
        try:
            sequence = int(str(number))
        except (TypeError, ValueError):
            sequence = -1
        return sequence, str(row.get("TAB_NAME", "")), str(row.get("REF_COL_NAME", ""))

    def _children(self, table: str, key: tuple[object, ...]) -> list[dict[str, object]]:
        frame = self._nasr.get(table)
        if frame is None:
            return []
        return self._matching(frame, key).to_dict(orient="records")

    def _facility(self, row: dict[str, object]) -> AtcFacility:
        key = tuple(row[column] for column in ATC_KEY)
        remarks = sorted(self._children("ATC_RMK", key), key=self._remark_order)
        return AtcFacility(
            AtcFacilityRecord(row),
            atis_services=tuple(
                AtisRecord(item) for item in self._children("ATC_ATIS", key)
            ),
            remarks=tuple(AtcRemarkRecord(item) for item in remarks),
            services=tuple(
                AtcServiceRecord(item) for item in self._children("ATC_SVC", key)
            ),
        )

    def find(self, identifier: object | None = None) -> tuple[AtcFacility, ...]:
        rows = self._nasr["ATC_BASE"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(self._facility(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object) -> AtcFacility:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(entity_type="AtcFacility", identifier=identifier)
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="AtcFacility", identifier=identifier, candidates=records
            )
        return records[0]


__all__ = ["AtcFacility", "AtcFacilityRepository"]
