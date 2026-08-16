"""Rich access to FAA holding-pattern records and their child tables."""

from collections.abc import Mapping

from pandas import DataFrame

from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import (
    FaaRecord,
    FixRecord,
    integer,
    nullable_text,
)
from .relationships import related_record

HOLDING_PATTERN_KEY = ("HP_NAME", "HP_NO", "STATE_CODE", "COUNTRY_CODE")


class HoldingPatternRecord(FaaRecord):
    """Typed conveniences for an ``HPF_BASE`` holding-pattern row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def holding_pattern_key(self) -> tuple[str, str, str | None, str] | None:
        """Verified key shared by every holding-pattern source table."""

        name = self._text("HP_NAME")
        number = self._text("HP_NO")
        country = self._text("COUNTRY_CODE")
        if name is None or number is None or country is None:
            return None
        return name, number, self._text("STATE_CODE"), country


class HoldingPatternChartRecord(HoldingPatternRecord):
    """Typed conveniences for an ``HPF_CHRT`` charting row."""

    @property
    def charting_type(self) -> str | None:
        return self._text("CHARTING_TYPE_DESC")


class HoldingPatternRemarkRecord(HoldingPatternRecord):
    """Typed conveniences for an ordered ``HPF_RMK`` remark row."""

    @property
    def sequence(self) -> int | None:
        value = self._text("REF_COL_SEQ_NO")
        return None if value is None else integer(value)


class HoldingPatternSpeedAltitudeRecord(HoldingPatternRecord):
    """Typed conveniences for an ``HPF_SPD_ALT`` restriction row."""

    @property
    def speed_range(self) -> str | None:
        return self._text("SPEED_RANGE")

    @property
    def altitude(self) -> str | None:
        return self._text("ALTITUDE")


class HoldingPattern:
    """One holding pattern with its charting, remarks, and restrictions."""

    def __init__(
        self,
        record: HoldingPatternRecord,
        *,
        charts: tuple[HoldingPatternChartRecord, ...],
        remarks: tuple[HoldingPatternRemarkRecord, ...],
        speed_altitude_limits: tuple[HoldingPatternSpeedAltitudeRecord, ...],
        fix: FixRecord | None,
    ) -> None:
        self.record = record
        self.charts = charts
        self.remarks = remarks
        self.speed_altitude_limits = speed_altitude_limits
        self.fix = fix


class HoldingPatternRepository:
    """Lookup holding patterns by their complete FAA composite key."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    def _key(self, identifier: object) -> tuple[object, object, object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            HOLDING_PATTERN_KEY
        ):
            raise ValueError(
                "Holding-pattern identifiers require "
                f"({', '.join(HOLDING_PATTERN_KEY)})"
            )
        return identifier

    def _matching(
        self, frame: DataFrame, key: tuple[object, object, object, object]
    ) -> DataFrame:
        rows = frame
        for column, value in zip(HOLDING_PATTERN_KEY, key):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return rows

    @staticmethod
    def _remark_order(row: dict[str, object]) -> tuple[str, str, int]:
        sequence = row.get("REF_COL_SEQ_NO")
        return (
            str(row.get("TAB_NAME", "")),
            str(row.get("REF_COL_NAME", "")),
            int(str(sequence)) if sequence not in (None, "") else -1,
        )

    def _holding_pattern(self, row: dict[str, object]) -> HoldingPattern:
        key = tuple(row[column] for column in HOLDING_PATTERN_KEY)
        holding_key = key[0], key[1], key[2], key[3]
        charts = self._matching(self._nasr["HPF_CHRT"], holding_key)
        remarks = self._matching(self._nasr["HPF_RMK"], holding_key)
        restrictions = self._matching(self._nasr["HPF_SPD_ALT"], holding_key)
        ordered_remarks = sorted(
            remarks.to_dict(orient="records"), key=self._remark_order
        )
        return HoldingPattern(
            HoldingPatternRecord(row),
            charts=tuple(
                HoldingPatternChartRecord(item)
                for item in charts.to_dict(orient="records")
            ),
            remarks=tuple(HoldingPatternRemarkRecord(item) for item in ordered_remarks),
            speed_altitude_limits=tuple(
                HoldingPatternSpeedAltitudeRecord(item)
                for item in restrictions.to_dict(orient="records")
            ),
            fix=related_record(
                self._nasr,
                source=row,
                target_table="FIX_BASE",
                columns=(
                    ("FIX_ID", "FIX_ID"),
                    ("ICAO_REGION_CODE", "ICAO_REGION_CODE"),
                    ("STATE_CODE", "STATE_CODE"),
                    ("COUNTRY_CODE", "COUNTRY_CODE"),
                ),
                record_type=FixRecord,
                relationship="holding-pattern fix",
            ),
        )

    def find(self, identifier: object | None = None) -> tuple[HoldingPattern, ...]:
        rows = self._nasr["HPF_BASE"]
        if identifier is not None:
            rows = self._matching(rows, self._key(identifier))
        return tuple(
            self._holding_pattern(row) for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object) -> HoldingPattern:
        records = self.find(identifier)
        if not records:
            raise RecordNotFoundError(
                entity_type="HoldingPattern", identifier=identifier
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="HoldingPattern", identifier=identifier, candidates=records
            )
        return records[0]


__all__ = ["HoldingPattern", "HoldingPatternRepository"]
