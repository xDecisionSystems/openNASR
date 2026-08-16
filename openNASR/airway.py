from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import AirwayRecord, AirwaySegmentRecord, FixRecord, NavaidRecord
from .registry import AIRWAY_KEY
from .relationships import related_record


class Airway:
    """One airway with FAA-ordered segment altitude constraints."""

    def __init__(self, record: AirwayRecord, segments: tuple[AirwaySegmentRecord, ...]):
        self.record = record
        self.segments = segments


class AirwayRepository:
    """Lookup airways by the verified regulatory/location/ID key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(AIRWAY_KEY):
            raise ValueError(f"Airway identifiers require ({', '.join(AIRWAY_KEY)})")
        return identifier

    def _matching(
        self, frame: DataFrame, key: tuple[object, object, object]
    ) -> DataFrame:
        rows = frame
        for column, value in zip(AIRWAY_KEY, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    def _airway(self, row: dict[str, object]) -> Airway:
        key = tuple(row[column] for column in AIRWAY_KEY)
        airway_key = key[0], key[1], key[2]
        segments = self._matching(self._nasr["AWY_SEG_ALT"], airway_key)
        ordered = sorted(
            segments.to_dict(orient="records"),
            key=lambda item: int(str(item["POINT_SEQ"])),
        )
        return Airway(AirwayRecord(row), tuple(self._segment(item) for item in ordered))

    def _segment(self, row: dict[str, object]) -> AirwaySegmentRecord:
        fix = related_record(
            self._nasr,
            source=row,
            target_table="FIX_BASE",
            columns=(
                ("FROM_POINT", "FIX_ID"),
                ("ICAO_REGION_CODE", "ICAO_REGION_CODE"),
                ("STATE_CODE", "STATE_CODE"),
                ("COUNTRY_CODE", "COUNTRY_CODE"),
            ),
            record_type=FixRecord,
            relationship="airway segment fix",
        )
        navaid = related_record(
            self._nasr,
            source=row,
            target_table="NAV_BASE",
            columns=(
                ("FROM_POINT", "NAV_ID"),
                ("FROM_PT_TYPE", "NAV_TYPE"),
                ("NAV_CITY", "CITY"),
                ("STATE_CODE", "STATE_CODE"),
                ("COUNTRY_CODE", "COUNTRY_CODE"),
            ),
            record_type=NavaidRecord,
            relationship="airway segment navaid",
        )
        return AirwaySegmentRecord(row, fix=fix, navaid=navaid)

    def find(self, identifier: object | None = None) -> tuple[Airway, ...]:
        rows = self._nasr["AWY_BASE"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(self._airway(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object) -> Airway:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(entity_type="Airway", identifier=identifier)
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="Airway", identifier=identifier, candidates=records
            )
        return records[0]
