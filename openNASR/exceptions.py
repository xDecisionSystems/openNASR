"""Public exception types raised by :mod:`openNASR`.

The hierarchy deliberately starts small. Additional specialised errors are
introduced with the subsystems that need them, while all public failures share
the stable :class:`OpenNASRError` base class.
"""

from collections.abc import Mapping, Sequence
from typing import Any


class OpenNASRError(Exception):
    """Base class for errors raised by openNASR."""


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
    "OpenNASRError",
    "RecordNotFoundError",
    "SchemaMismatchError",
    "TableNotFoundError",
]
