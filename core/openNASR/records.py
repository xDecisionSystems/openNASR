"""Lossless base record representation for FAA CSV rows."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date
from decimal import Decimal
from enum import Enum
from importlib import import_module
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


def dms_coordinate(raw: str, *, context: FieldContext | None = None) -> float | None:
    """Convert an FAA formatted ``DD-MM-SS.ssssH`` coordinate to decimal degrees.

    Used by tables such as ``MAA_SHP`` that publish only a formatted
    latitude/longitude string, with no accompanying ``*_DECIMAL`` column.
    """

    def convert(value: str) -> float:
        hemisphere = value[-1]
        if hemisphere not in "NSEW":
            raise ValueError(f"Unsupported coordinate hemisphere: {value!r}")
        degrees_str, minutes_str, seconds_str = value[:-1].split("-")
        magnitude = int(degrees_str) + int(minutes_str) / 60 + float(seconds_str) / 3600
        return -magnitude if hemisphere in "SW" else magnitude

    return _convert(raw, float, convert, context)


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

    def __str__(self) -> str:
        """Return a concise human-readable description of this FAA record.

        The raw mapping remains the authoritative representation. This method
        is intentionally only a display summary: it names the typed record
        and selects the best available FAA identifier/name. Point records also
        include decimal ``(latitude, longitude)`` coordinates.
        """

        type_name = self.__class__.__name__.removesuffix("Record")
        name = next(
            (
                self._display_value(column)
                for column in (
                    "ARPT_NAME",
                    "FIX_NAME",
                    "NAME",
                    "LOCATION_NAME",
                    "DROP_ZONE_NAME",
                    "MAA_NAME",
                    "RWY_ID",
                    "ILS_ID",
                    "DP_NAME",
                    "STAR_COMPUTER_CODE",
                    "AWY_ID",
                    "RCode",
                    "FAC_NAME",
                    "FIX_ID",
                    "NAV_ID",
                    "ARPT_ID",
                    "LOCATION_ID",
                    "MAA_ID",
                    "PJA_ID",
                )
                if self._display_value(column) is not None
            ),
            None,
        )
        summary = type_name if name is None else f"{type_name}: {name}"
        latitude = self._display_value("LAT_DECIMAL")
        longitude = self._display_value("LONG_DECIMAL")
        if latitude is not None and longitude is not None:
            summary += f" ({latitude}, {longitude})"
        return summary

    def _display_value(self, column: str) -> str | None:
        value = self._raw.get(column)
        if value is None or value != value:
            return None
        text = str(value).strip()
        return text or None

    def __getattr__(self, name: str) -> Any:
        try:
            return self._raw[name]
        except KeyError as error:
            raise AttributeError(name) from error


_COMPATIBILITY_RECORD_MODULES = {
    "AtcFacilityRecord": "atc",
    "AtcRemarkRecord": "atc",
    "AtcServiceRecord": "atc",
    "AtisRecord": "atc",
    "RadarRecord": "atc",
    "AutomatedWeatherStationRecord": "weather",
    "WeatherLocationRecord": "weather",
    "WeatherServiceRecord": "weather",
    "FlightServiceStationRecord": "fss",
    "FlightServiceStationRemarkRecord": "fss",
    "FixRecord": "fix",
    "LocationIdentifierRecord": "locations",
    "ClassAirspaceRecord": "airspace",
    "ArtccRecord": "airspace",
    "MaaRecord": "airspace",
    "MaaContactRecord": "airspace",
    "MaaRemarkRecord": "airspace",
    "MaaShapePointRecord": "airspace",
    "ParachuteJumpAreaRecord": "airspace",
    "ParachuteJumpAreaContactRecord": "airspace",
    "MilitaryOperationRecord": "military",
    "MilitaryTrainingRouteRecord": "military",
    "MilitaryTrainingRouteAgencyRecord": "military",
    "MilitaryTrainingRoutePointRecord": "military",
    "MilitaryTrainingRouteProcedureRecord": "military",
    "MilitaryTrainingRouteTerrainRecord": "military",
    "MilitaryTrainingRouteWidthRecord": "military",
    "NavaidRecord": "nav",
    "AirportRecord": "airport",
    "AirwayRecord": "airway",
    "AirwaySegmentRecord": "airway",
    "HoldingPatternRecord": "holding",
    "HoldingPatternChartRecord": "holding",
    "HoldingPatternRemarkRecord": "holding",
    "HoldingPatternSpeedAltitudeRecord": "holding",
    "CommunicationOutletRecord": "communications",
    "FrequencyRecord": "communications",
    "CodedDepartureRouteRecord": "departure",
    "DepartureProcedureRecord": "departure",
    "DepartureAirportRecord": "departure",
    "DepartureRouteRecord": "departure",
    "PreferredRouteRecord": "departure",
    "PreferredRouteFormatRecord": "departure",
    "PreferredRouteSegmentRecord": "departure",
    "StarProcedureRecord": "arrivals",
    "StarAirportRecord": "arrivals",
    "StarRouteRecord": "arrivals",
    "RunwayRecord": "rwy",
    "RunwayEndRecord": "rwy",
    "IlsRecord": "ils",
    "DmeRecord": "ils",
    "GlideSlopeRecord": "ils",
    "MarkerRecord": "ils",
}


def __getattr__(name: str) -> Any:
    """Lazily preserve legacy record imports after domain ownership moved."""

    module_name = _COMPATIBILITY_RECORD_MODULES.get(name)
    if module_name is None:
        raise AttributeError(name)
    record_type = getattr(import_module(f"{__package__}.{module_name}"), name)
    globals()[name] = record_type
    return record_type


__all__ = [
    "FaaRecord",
    "FieldContext",
    "boolean",
    "coordinate",
    "decimal",
    "enum_value",
    "float_value",
    "integer",
    "iso_date",
    "nullable_text",
    *_COMPATIBILITY_RECORD_MODULES,
]
