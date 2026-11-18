"""Exact composite-key resolution shared by rich domain repositories."""

from collections.abc import Mapping, Sequence
from typing import TypeVar

from numpy import ndarray
from pandas import DataFrame

from .exceptions import AmbiguousRecordError
from .records import FaaRecord


RecordType = TypeVar("RecordType", bound=FaaRecord)


class RelationshipIndex:
    """Repository-owned composite relationship indexes for one table snapshot."""

    def __init__(self) -> None:
        self._positions: dict[
            tuple[int, tuple[str, ...]], dict[tuple[str, ...], ndarray]
        ] = {}

    def rows(
        self,
        frame: DataFrame,
        columns: tuple[str, ...],
        values: tuple[str, ...],
    ) -> DataFrame:
        """Materialize matching source rows without caching record objects."""

        cache_key = (id(frame), columns)
        if cache_key not in self._positions:
            normalized_columns = [frame[column].map(_normalized) for column in columns]
            grouped = frame.groupby(normalized_columns, sort=False).indices
            self._positions[cache_key] = {
                key if isinstance(key, tuple) else (key,): positions
                for key, positions in grouped.items()
            }
        positions = self._positions[cache_key].get(values)
        return frame.iloc[positions] if positions is not None else frame.iloc[0:0]


def related_record(
    nasr: Mapping[str, DataFrame],
    *,
    source: Mapping[str, object],
    target_table: str,
    columns: Sequence[tuple[str, str]],
    record_type: type[RecordType],
    relationship: str,
    index: RelationshipIndex | None = None,
) -> RecordType | None:
    """Resolve at most one row using every column in a verified relationship."""

    frame = nasr.get(target_table)
    if frame is None:
        return None
    values = tuple(source.get(local) for local, _target in columns)
    if any(_normalized(value) == "" for value in values):
        return None
    rows = (
        index.rows(
            frame,
            tuple(target for _local, target in columns),
            tuple(_normalized(value) for value in values),
        )
        if index is not None
        else frame
    )
    if index is None:
        for value, (_local, target) in zip(values, columns):
            rows = rows[rows[target].map(_normalized).eq(_normalized(value))]
    records = tuple(record_type(row) for row in rows.to_dict(orient="records"))
    if not records:
        return None
    if len(records) > 1:
        raise AmbiguousRecordError(
            entity_type=record_type.__name__,
            identifier=values,
            filters={"relationship": relationship},
            candidates=records,
        )
    return records[0]


def _normalized(value: object) -> str:
    if value is None or value != value:
        return ""
    return str(value).strip().upper()


__all__ = ["RelationshipIndex", "related_record"]
