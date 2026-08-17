from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .fix import FixRecord
from .indexing import NormalizedIndexCache, normalized_indexed_rows
from .nav import NavaidRecord
from .records import FaaRecord, integer, nullable_text
from .relationships import RelationshipIndex, related_record

AIRWAY_KEY = ("REGULATORY", "AWY_LOCATION", "AWY_ID")


class AirwayRecord(FaaRecord):
    """Typed conveniences for an ``AWY_BASE`` airway row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def airway_key(self) -> tuple[str, str, str] | None:
        values = tuple(
            self._text(column) for column in ("REGULATORY", "AWY_LOCATION", "AWY_ID")
        )
        if any(value is None for value in values):
            return None
        return values[0], values[1], values[2]  # type: ignore[return-value]


class AirwaySegmentRecord(AirwayRecord):
    """Typed conveniences for an ordered ``AWY_SEG_ALT`` row."""

    def __init__(
        self,
        raw: Mapping[str, object],
        *,
        fix: FixRecord | None = None,
        navaid: NavaidRecord | None = None,
    ) -> None:
        super().__init__(raw)
        self._fix = fix
        self._navaid = navaid

    @property
    def fix(self) -> FixRecord | None:
        """Fix at this airway point, resolved through its complete FAA key."""

        return self._fix

    @property
    def navaid(self) -> NavaidRecord | None:
        """Navaid at this airway point, resolved through its complete FAA key."""

        return self._navaid

    @property
    def point_sequence(self) -> int | None:
        value = self._text("POINT_SEQ")
        return None if value is None else integer(value)

    @property
    def minimum_enroute_altitude(self) -> int | None:
        value = self._text("MIN_ENROUTE_ALT")
        return None if value is None else integer(value)

    @property
    def maximum_authorized_altitude(self) -> int | None:
        value = self._text("MAX_AUTH_ALT")
        return None if value is None else integer(value)


class Airway:
    """One airway with FAA-ordered segment altitude constraints."""

    def __init__(self, record: AirwayRecord, segments: tuple[AirwaySegmentRecord, ...]):
        self.record = record
        self.segments = segments


class AirwayRepository:
    """Lookup airways by the verified regulatory/location/ID key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._indexes: NormalizedIndexCache = {}
        self._relationship_index = RelationshipIndex()

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
        return normalized_indexed_rows(
            self._indexes, frame, zip(AIRWAY_KEY, key), self._normalized
        )

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
            index=self._relationship_index,
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
            index=self._relationship_index,
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
