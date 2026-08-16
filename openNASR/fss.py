"""Rich access to FAA flight-service-station records."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FlightServiceStationRecord, FlightServiceStationRemarkRecord
from .registry import FSS_KEY


class FlightServiceStation:
    """One flight service station with its remarks."""

    def __init__(
        self,
        record: FlightServiceStationRecord,
        *,
        remarks: tuple[FlightServiceStationRemarkRecord, ...],
    ) -> None:
        self.record = record
        self.remarks = remarks


class FlightServiceStationRepository:
    """Look up flight service stations by their complete verified FAA key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, ...]:
        if not isinstance(identifier, tuple) or len(identifier) != len(FSS_KEY):
            raise ValueError(
                f"Flight-service-station identifiers require ({', '.join(FSS_KEY)})"
            )
        return identifier

    def _matching(self, frame: DataFrame, key: tuple[object, ...]) -> DataFrame:
        rows = frame
        for column, value in zip(FSS_KEY, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    @staticmethod
    def _remark_order(row: dict[str, object]) -> tuple[str, int]:
        sequence = row.get("REF_COL_SEQ_NO")
        try:
            number = int(str(sequence))
        except (TypeError, ValueError):
            number = -1
        return str(row.get("REF_COL_NAME", "")), number

    def _station(self, row: dict[str, object]) -> FlightServiceStation:
        key = tuple(row[column] for column in FSS_KEY)
        frame = self._nasr.get("FSS_RMK")
        remarks = (
            []
            if frame is None
            else self._matching(frame, key).to_dict(orient="records")
        )
        return FlightServiceStation(
            FlightServiceStationRecord(row),
            remarks=tuple(
                FlightServiceStationRemarkRecord(item)
                for item in sorted(remarks, key=self._remark_order)
            ),
        )

    def find(
        self, identifier: object | None = None
    ) -> tuple[FlightServiceStation, ...]:
        rows = self._nasr["FSS_BASE"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(self._station(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object) -> FlightServiceStation:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="FlightServiceStation", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="FlightServiceStation",
                identifier=identifier,
                candidates=records,
            )
        return records[0]


__all__ = ["FlightServiceStation", "FlightServiceStationRepository"]
