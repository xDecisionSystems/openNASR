"""Public exception types raised by :mod:`openNASR`.

The hierarchy deliberately starts small. Additional specialised errors are
introduced with the subsystems that need them, while all public failures share
the stable :class:`OpenNASRError` base class.
"""

from collections.abc import Mapping, Sequence
from typing import Any


class OpenNASRError(Exception):
    """Base class for errors raised by openNASR."""

    # Route resolution populates these only for route-related failures. They
    # live on the public base so callers can inspect diagnostics uniformly.
    token: str | None
    position: int | None
    cycle: Any | None
    route: str | None
    route_text: str | None
    failure_type: str | None


class ConfigurationError(OpenNASRError):
    """Raised when openNASR configuration is incomplete or invalid."""


class CycleNotFoundError(OpenNASRError):
    """Raised when a requested NASR data cycle is unavailable."""


class DownloadError(OpenNASRError):
    """Raised when a NASR download or metadata request fails."""


class ArchiveError(OpenNASRError):
    """Raised when a NASR archive is invalid or unsafe to extract."""


class TableNotFoundError(OpenNASRError):
    """Raised when a required NASR CSV table is unavailable."""


class FieldConversionError(OpenNASRError):
    """Raised when a non-empty FAA field cannot become its typed value."""

    def __init__(
        self,
        *,
        cycle: Any | None,
        table: str | None,
        column: str | None,
        raw_value: str,
        record_identity: Any | None,
        expected_type: type[Any],
    ) -> None:
        self.cycle = cycle
        self.table = table
        self.column = column
        self.raw_value = raw_value
        self.record_identity = record_identity
        self.expected_type = expected_type
        location = ".".join(part for part in (table, column) if part) or "field"
        message = (
            f"Cannot convert {location} value {raw_value!r} to {expected_type.__name__}"
        )
        if cycle is not None:
            message += f" for cycle {cycle}"
        if record_identity is not None:
            message += f" (record {record_identity!r})"
        super().__init__(message)


class SchemaMismatchError(OpenNASRError):
    """Raised when FAA data differs from a supported schema.

    Keyword context is retained as attributes so callers and tooling can
    inspect drift without parsing the human-readable message.
    """

    def __init__(self, message: str, **context: Any) -> None:
        self.context = dict(context)
        for name, value in context.items():
            setattr(self, name, value)
        super().__init__(message)


class RecordNotFoundError(OpenNASRError):
    """Raised when a requested record cannot be found.

    Attributes:
        entity_type: The type of record being looked up.
        identifier: The requested identifier.
        filters: Additional lookup criteria supplied by the caller.
    """

    def __init__(
        self,
        *,
        entity_type: str,
        identifier: Any,
        filters: Mapping[str, Any] | None = None,
    ) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        self.filters = dict(filters or {})
        super().__init__(self._message())

    def _message(self) -> str:
        message = f"{self.entity_type} record {self.identifier!r} was not found"
        if self.filters:
            criteria = ", ".join(
                f"{name}={value!r}" for name, value in self.filters.items()
            )
            message += f" with filters: {criteria}"
        return message


class UnsupportedRouteContentError(OpenNASRError):
    """Raised for recognized route content outside domestic NASR coverage."""

    def __init__(
        self,
        *,
        token: str,
        position: int,
        content_type: str,
        cycle: Any | None,
    ) -> None:
        self.token = token
        self.position = position
        self.content_type = content_type
        self.cycle = cycle
        message = (
            f"Unsupported {content_type.replace('_', ' ')} route content "
            f"{token!r} at position {position}"
        )
        if cycle is not None:
            message += f" for cycle {cycle}"
        super().__init__(message)


class RouteConnectivityError(OpenNASRError):
    """Raised when published route records cannot form a faithful path."""

    def __init__(
        self,
        *,
        entity_type: str,
        identifier: str,
        from_identifier: str | None,
        to_identifier: str | None,
        cycle: Any | None,
        procedure_identifier: str | None = None,
        airway_identifier: str | None = None,
        filed_join_identifier: str | None = None,
        following_identifier: str | None = None,
        candidate_joins: Sequence[str] = (),
    ) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        self.from_identifier = from_identifier
        self.to_identifier = to_identifier
        self.cycle = cycle
        self.procedure_identifier = procedure_identifier
        self.airway_identifier = airway_identifier
        self.filed_join_identifier = filed_join_identifier
        self.following_identifier = following_identifier
        self.candidate_joins = tuple(candidate_joins)
        message = f"{entity_type} {identifier!r} has no published path"
        if from_identifier is not None or to_identifier is not None:
            message += f" from {from_identifier!r} to {to_identifier!r}"
        if cycle is not None:
            message += f" for cycle {cycle}"
        super().__init__(message)


class AmbiguousRecordError(OpenNASRError):
    """Raised when a lookup matches more than one record.

    Attributes:
        entity_type: The type of record being looked up.
        identifier: The requested identifier.
        filters: Additional lookup criteria supplied by the caller.
        candidates: The records that matched the lookup.
    """

    def __init__(
        self,
        *,
        entity_type: str,
        identifier: Any,
        filters: Mapping[str, Any] | None = None,
        candidates: Sequence[Any] = (),
    ) -> None:
        self.entity_type = entity_type
        self.identifier = identifier
        self.filters = dict(filters or {})
        self.candidates = tuple(candidates)
        super().__init__(self._message())

    def _message(self) -> str:
        message = (
            f"{self.entity_type} record {self.identifier!r} matched "
            f"{len(self.candidates)} records"
        )
        if self.filters:
            criteria = ", ".join(
                f"{name}={value!r}" for name, value in self.filters.items()
            )
            message += f" with filters: {criteria}"
        return message


__all__ = [
    "AmbiguousRecordError",
    "ArchiveError",
    "ConfigurationError",
    "CycleNotFoundError",
    "DownloadError",
    "FieldConversionError",
    "OpenNASRError",
    "RecordNotFoundError",
    "RouteConnectivityError",
    "SchemaMismatchError",
    "TableNotFoundError",
    "UnsupportedRouteContentError",
]
