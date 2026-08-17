"""Small, snapshot-scoped helpers for normalized DataFrame lookups."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping

from numpy import ndarray
from pandas import DataFrame


NormalizedPositionIndex = dict[str, ndarray]
NormalizedIndexCache = MutableMapping[tuple[int, str], NormalizedPositionIndex]


def cached_normalized_column_index(
    cache: NormalizedIndexCache,
    frame: DataFrame,
    column: str,
    normalize: Callable[[object], str],
) -> NormalizedPositionIndex:
    """Return one cached normalized-value -> source-row-position index.

    Callers own ``cache`` so indexes remain scoped to their repository or
    NASR snapshot. The cached values are positions rather than DataFrames,
    avoiding eager per-group DataFrame materialization for identifier columns
    with many distinct values.
    """

    key = (id(frame), column)
    if key not in cache:
        normalized = frame[column].map(normalize)
        cache[key] = frame.groupby(normalized).indices
    return cache[key]


def normalized_index_rows(
    frame: DataFrame,
    index: NormalizedPositionIndex,
    value: object,
    normalize: Callable[[object], str],
) -> DataFrame:
    """Materialize one normalized index group while retaining source order."""

    positions = index.get(normalize(value))
    return frame.iloc[positions] if positions is not None else frame.iloc[0:0]


__all__ = [
    "NormalizedIndexCache",
    "NormalizedPositionIndex",
    "cached_normalized_column_index",
    "normalized_index_rows",
]
