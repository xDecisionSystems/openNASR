"""Lossless base record representation for FAA CSV rows."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any


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


__all__ = ["FaaRecord"]
