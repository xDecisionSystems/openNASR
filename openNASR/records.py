"""Lossless base record representation for FAA CSV rows."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, TypeVar

from .exceptions import FieldConversionError


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


class AirportRecord(FaaRecord):
    """Airport record with nullable typed conveniences over lossless FAA fields."""

    def __init__(
        self,
        raw: Mapping[str, object],
        *,
        runways: tuple[RunwayRecord, ...] = (),
        runway_ends: tuple[RunwayEndRecord, ...] = (),
    ) -> None:
        super().__init__(raw)
        self._runways = runways
        self._runway_ends = runway_ends

    @property
    def runways(self) -> tuple[RunwayRecord, ...]:
        """Immutable collection of runways belonging to this airport."""
        return self._runways

    @property
    def runway_ends(self) -> tuple[RunwayEndRecord, ...]:
        """Immutable collection of runway ends belonging to this airport."""
        return self._runway_ends

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
