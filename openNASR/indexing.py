"""Small, snapshot-scoped helpers for normalized DataFrame lookups."""

from __future__ import annotations

from collections.abc import Callable, Iterable, MutableMapping

from numpy import intersect1d, ndarray
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


def normalized_indexed_rows(
    cache: NormalizedIndexCache,
    frame: DataFrame,
    criteria: Iterable[tuple[str, object]],
    normalize: Callable[[object], str],
) -> DataFrame:
    """Return source-ordered rows satisfying normalized column criteria."""

    positions: ndarray | None = None
    for column, value in criteria:
        indexed = cached_normalized_column_index(cache, frame, column, normalize)
        matches = indexed.get(normalize(value))
        if matches is None:
            return frame.iloc[0:0]
        positions = (
            matches
            if positions is None
            else intersect1d(positions, matches, assume_unique=True)
        )
    return frame if positions is None else frame.iloc[positions]


__all__ = [
    "NormalizedIndexCache",
    "NormalizedPositionIndex",
    "cached_normalized_column_index",
    "normalized_indexed_rows",
    "normalized_index_rows",
]
