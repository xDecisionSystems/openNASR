"""Lossless base record representation for FAA CSV rows."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, TypeVar


EnumValue = TypeVar("EnumValue", bound=Enum)


def nullable_text(raw: str) -> str | None:
    """Return an empty FAA field as ``None`` without altering other text."""
    return None if raw == "" else raw


def iso_date(raw: str) -> date | None:
    """Convert an empty-or-ISO-date FAA field to :class:`datetime.date`."""
    return None if raw == "" else date.fromisoformat(raw)


def integer(raw: str) -> int | None:
    """Convert an empty-or-integer FAA field without changing its raw text."""
    return None if raw == "" else int(raw)


def decimal(raw: str) -> Decimal | None:
    """Convert an empty-or-decimal FAA field to an exact :class:`Decimal`."""
    return None if raw == "" else Decimal(raw)


def float_value(raw: str) -> float | None:
    """Convert an empty-or-floating-point FAA field to :class:`float`."""
    return None if raw == "" else float(raw)


def boolean(
    raw: str,
    *,
    true_codes: frozenset[str] = frozenset({"1", "TRUE", "Y", "YES"}),
    false_codes: frozenset[str] = frozenset({"0", "FALSE", "N", "NO"}),
) -> bool | None:
    """Convert a documented FAA boolean code, accepting case and space variants."""
    if raw == "":
        return None

    code = raw.strip().upper()
    if code in true_codes:
        return True
    if code in false_codes:
        return False
    raise ValueError(f"Unsupported boolean code: {raw!r}")


def coordinate(raw: str) -> float | None:
    """Convert an empty-or-decimal coordinate field to :class:`float`."""
    return float_value(raw)


def enum_value(raw: str, enum_type: type[EnumValue]) -> EnumValue | None:
    """Convert an empty FAA code to a member of ``enum_type``."""
    return None if raw == "" else enum_type(raw)


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


__all__ = [
    "FaaRecord",
    "boolean",
    "coordinate",
    "decimal",
    "enum_value",
    "float_value",
    "integer",
    "iso_date",
    "nullable_text",
]
