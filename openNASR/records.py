"""Lossless base record representation for FAA CSV rows."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar

from .exceptions import FieldConversionError

if TYPE_CHECKING:
    from .airspace import ClassAirspace
    from .military import MilitaryOperation


EnumValue = TypeVar("EnumValue", bound=Enum)


class FieldContext:
    """Source metadata included when a typed FAA field cannot be converted."""

    def __init__(
        self,
        *,
        cycle: Any | None = None,
        table: str | None = None,
        column: str | None = None,
        record_identity: Any | None = None,
    ) -> None:
        self.cycle = cycle
        self.table = table
        self.column = column
        self.record_identity = record_identity


def _convert(
    raw: str,
    expected_type: type[Any],
    converter,
    context: FieldContext | None,
):
    if raw == "":
        return None
    try:
        return converter(raw)
    except (ArithmeticError, TypeError, ValueError) as error:
        details = context or FieldContext()
        raise FieldConversionError(
            cycle=details.cycle,
            table=details.table,
            column=details.column,
            raw_value=raw,
            record_identity=details.record_identity,
            expected_type=expected_type,
        ) from error


def nullable_text(raw: str) -> str | None:
    """Return an empty FAA field as ``None`` without altering other text."""
    return None if raw == "" else raw


def iso_date(raw: str, *, context: FieldContext | None = None) -> date | None:
    """Convert an empty-or-ISO-date FAA field to :class:`datetime.date`."""
    return _convert(raw, date, date.fromisoformat, context)


def integer(raw: str, *, context: FieldContext | None = None) -> int | None:
    """Convert an empty-or-integer FAA field without changing its raw text."""
    return _convert(raw, int, int, context)


def decimal(raw: str, *, context: FieldContext | None = None) -> Decimal | None:
    """Convert an empty-or-decimal FAA field to an exact :class:`Decimal`."""
    return _convert(raw, Decimal, Decimal, context)


def float_value(raw: str, *, context: FieldContext | None = None) -> float | None:
    """Convert an empty-or-floating-point FAA field to :class:`float`."""
    return _convert(raw, float, float, context)


def boolean(
    raw: str,
    *,
    true_codes: frozenset[str] = frozenset({"1", "TRUE", "Y", "YES"}),
    false_codes: frozenset[str] = frozenset({"0", "FALSE", "N", "NO"}),
    context: FieldContext | None = None,
) -> bool | None:
    """Convert a documented FAA boolean code, accepting case and space variants."""

    def convert(value: str) -> bool:
        code = value.strip().upper()
        if code in true_codes:
            return True
        if code in false_codes:
            return False
        raise ValueError(f"Unsupported boolean code: {value!r}")

    return _convert(raw, bool, convert, context)


def coordinate(raw: str, *, context: FieldContext | None = None) -> float | None:
    """Convert an empty-or-decimal coordinate field to :class:`float`."""
    return float_value(raw, context=context)


def enum_value(
    raw: str,
    enum_type: type[EnumValue],
    *,
    context: FieldContext | None = None,
) -> EnumValue | None:
    """Convert an empty FAA code to a member of ``enum_type``."""
    return _convert(raw, enum_type, enum_type, context)


class FaaRecord(Mapping[str, object]):
    """A lossless mapping that preserves FAA column names and raw values."""

    def __init__(self, raw: Mapping[str, object]) -> None:
        self._raw = dict(raw)

    @property
    def raw(self) -> Mapping[str, object]:
        return self._raw

    def as_dict(self) -> dict[str, object]:
        return dict(self._raw)

    def __getitem__(self, key: str) -> object:
        return self._raw[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._raw)

    def __len__(self) -> int:
        return len(self._raw)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._raw[name]
        except KeyError as error:
            raise AttributeError(name) from error


class RunwayRecord(FaaRecord):
    """Lossless typed marker for an airport runway row."""


class RunwayEndRecord(FaaRecord):
    """Lossless typed marker for an airport runway-end row."""


class IlsRecord(FaaRecord):
    """Lossless typed marker for an airport ILS row."""


class DmeRecord(FaaRecord):
    """Lossless typed marker for an airport ILS DME row."""


class GlideSlopeRecord(FaaRecord):
    """Lossless typed marker for an airport ILS glide-slope row."""


class MarkerRecord(FaaRecord):
    """Lossless typed marker for an airport ILS marker row."""


class ClassAirspaceRecord(FaaRecord):
    """Typed conveniences for one airport-linked class-airspace row."""

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
    def classes(self) -> Mapping[str, str | None]:
        """Raw FAA class-airspace codes keyed by class letter."""

        return {
            letter: self._text(f"CLASS_{letter}_AIRSPACE")
            for letter in ("B", "C", "D", "E")
        }


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


class CommunicationOutletRecord(FaaRecord):
    """Typed conveniences for a standalone ``COM`` communication outlet."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def identifier(self) -> str | None:
        return self._text("COMM_LOC_ID")

    @property
    def name(self) -> str | None:
        return self._text("COMM_OUTLET_NAME")

    @property
    def communication_type(self) -> str | None:
        return self._text("COMM_TYPE")


class FrequencyRecord(FaaRecord):
    """Typed conveniences for a standalone ``FRQ`` frequency assignment."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def frequency_key(
        self,
    ) -> (
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str,
            str | None,
            str,
        ]
        | None
    ):
        facility = self._text("FACILITY")
        frequency = self._text("FREQ")
        frequency_use = self._text("FREQ_USE")
        if facility is None or frequency is None or frequency_use is None:
            return None
        return (
            facility,
            self._text("SERVICED_FACILITY"),
            self._text("SERVICED_SITE_TYPE"),
            self._text("SERVICED_STATE"),
            self._text("SERVICED_COUNTRY"),
            frequency,
            self._text("SECTORIZATION"),
            frequency_use,
        )

    @property
    def serviced_facility_key(
        self,
    ) -> tuple[str, str, str | None, str | None] | None:
        facility = self._text("SERVICED_FACILITY")
        site_type = self._text("SERVICED_SITE_TYPE")
        if facility is None or site_type is None:
            return None
        return (
            facility,
            site_type,
            self._text("SERVICED_STATE"),
            self._text("SERVICED_COUNTRY"),
        )

    @property
    def facility(self) -> str | None:
        return self._text("FACILITY")

    @property
    def frequency(self) -> str | None:
        return self._text("FREQ")


class FixRecord(FaaRecord):
    """Fix record with nullable typed conveniences over lossless FAA fields."""

    def _text_from(self, *columns: str) -> str | None:
        for column in columns:
            if column in self._raw:
                value = self._raw[column]
                if value is None or value != value:
                    return None
                return nullable_text(str(value))
        return None

    @property
    def identifier(self) -> str | None:
        return self._text_from("FIX_ID")

    @property
    def name(self) -> str | None:
        return self._text_from("FIX_NAME", "NAME")

    @property
    def latitude(self) -> float | None:
        value = self._text_from("LAT_DECIMAL")
        return None if value is None else coordinate(value)

    @property
    def longitude(self) -> float | None:
        value = self._text_from("LONG_DECIMAL")
        return None if value is None else coordinate(value)

    @property
    def state(self) -> str | None:
        return self._text_from("STATE_CODE", "STATE")

    @property
    def country(self) -> str | None:
        return self._text_from("COUNTRY_CODE", "COUNTRY_NAME")

    @property
    def high_artcc(self) -> str | None:
        return self._text_from("ARTCC_ID_HIGH")

    @property
    def low_artcc(self) -> str | None:
        return self._text_from("ARTCC_ID_LOW")


class NavaidRecord(FaaRecord):
    """Typed conveniences over a lossless navaid source row."""

    def _text(self, *columns: str) -> str | None:
        for column in columns:
            value = self._raw.get(column)
            if value is not None and value == value:
                return nullable_text(str(value))
        return None

    @property
    def identifier(self) -> str | None:
        return self._text("NAV_ID")

    @property
    def nav_type(self) -> str | None:
        return self._text("NAV_TYPE")

    @property
    def name(self) -> str | None:
        return self._text("NAME")

    @property
    def state(self) -> str | None:
        return self._text("STATE_CODE")

    @property
    def country(self) -> str | None:
        return self._text("COUNTRY_CODE", "COUNTRY_NAME")

    @property
    def high_artcc(self) -> str | None:
        return self._text("HIGH_ALT_ARTCC_ID")

    @property
    def low_artcc(self) -> str | None:
        return self._text("LOW_ALT_ARTCC_ID")

    @property
    def frequency(self) -> str | None:
        return self._text("FREQ")

    @property
    def latitude(self) -> float | None:
        value = self._text("LAT_DECIMAL")
        return None if value is None else coordinate(value)

    @property
    def longitude(self) -> float | None:
        value = self._text("LONG_DECIMAL")
        return None if value is None else coordinate(value)


class AirportRecord(FaaRecord):
    """Airport record with nullable typed conveniences over lossless FAA fields."""

    def __init__(
        self,
        raw: Mapping[str, object],
        *,
        runways: tuple[RunwayRecord, ...] = (),
        runway_ends: tuple[RunwayEndRecord, ...] = (),
        ils: tuple[IlsRecord, ...] = (),
        dmes: tuple[DmeRecord, ...] = (),
        glide_slopes: tuple[GlideSlopeRecord, ...] = (),
        markers: tuple[MarkerRecord, ...] = (),
        class_airspace: ClassAirspace | None = None,
        military_operations: tuple[MilitaryOperation, ...] = (),
    ) -> None:
        super().__init__(raw)
        self._runways = runways
        self._runway_ends = runway_ends
        self._ils = ils
        self._dmes = dmes
        self._glide_slopes = glide_slopes
        self._markers = markers
        self._class_airspace = class_airspace
        self._military_operations = military_operations

    @property
    def runways(self) -> tuple[RunwayRecord, ...]:
        """Immutable collection of runways belonging to this airport."""
        return self._runways

    @property
    def runway_ends(self) -> tuple[RunwayEndRecord, ...]:
        """Immutable collection of runway ends belonging to this airport."""
        return self._runway_ends

    @property
    def ils(self) -> tuple[IlsRecord, ...]:
        """Immutable ILS records; empty when the optional table is absent."""
        return self._ils

    @property
    def dmes(self) -> tuple[DmeRecord, ...]:
        """Immutable DME records; empty when the optional table is absent."""
        return self._dmes

    @property
    def glide_slopes(self) -> tuple[GlideSlopeRecord, ...]:
        """Immutable glide-slope records; empty when the optional table is absent."""
        return self._glide_slopes

    @property
    def markers(self) -> tuple[MarkerRecord, ...]:
        """Immutable marker records; empty when the optional table is absent."""
        return self._markers

    @property
    def class_airspace(self) -> ClassAirspace | None:
        """Airport-linked class-airspace data, when exactly one row matches."""

        return self._class_airspace

    @property
    def military_operations(self) -> tuple[MilitaryOperation, ...]:
        """Military-operation records linked through the complete site key."""

        return self._military_operations

    def _field_context(self, column: str) -> FieldContext:
        return FieldContext(
            table="APT_BASE",
            column=column,
            record_identity=self._raw.get("ARPT_ID"),
        )

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def faa_id(self) -> str | None:
        """FAA airport identifier, or ``None`` when the source field is empty."""
        return self._text("ARPT_ID")

    @property
    def icao_id(self) -> str | None:
        """ICAO airport identifier, or ``None`` when the source field is empty."""
        return self._text("ICAO_ID")

    @property
    def name(self) -> str | None:
        """Airport name, or ``None`` when the schema does not provide one."""
        return self._text("ARPT_NAME")

    @property
    def latitude(self) -> float | None:
        """Decimal latitude, or ``None`` when the source field is empty."""
        value = self._raw.get("LAT_DECIMAL")
        if value is None:
            return None
        return coordinate(str(value), context=self._field_context("LAT_DECIMAL"))

    @property
    def longitude(self) -> float | None:
        """Decimal longitude, or ``None`` when the source field is empty."""
        value = self._raw.get("LONG_DECIMAL")
        if value is None:
            return None
        return coordinate(str(value), context=self._field_context("LONG_DECIMAL"))

    @property
    def elevation_ft(self) -> float | None:
        """Airport elevation in feet, or ``None`` when the source field is empty."""
        value = self._raw.get("ELEV")
        if value is None:
            return None
        return float_value(str(value), context=self._field_context("ELEV"))


__all__ = [
    "FaaRecord",
    "AirportRecord",
    "AirwayRecord",
    "AirwaySegmentRecord",
    "ClassAirspaceRecord",
    "CommunicationOutletRecord",
    "DmeRecord",
    "GlideSlopeRecord",
    "HoldingPatternChartRecord",
    "HoldingPatternRecord",
    "HoldingPatternRemarkRecord",
    "HoldingPatternSpeedAltitudeRecord",
    "FixRecord",
    "FrequencyRecord",
    "IlsRecord",
    "MarkerRecord",
    "MilitaryOperationRecord",
    "NavaidRecord",
    "RunwayEndRecord",
    "RunwayRecord",
    "FieldContext",
    "boolean",
    "coordinate",
    "decimal",
    "enum_value",
    "float_value",
    "integer",
    "iso_date",
    "nullable_text",
]
