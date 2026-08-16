"""Exact composite-key resolution shared by rich domain repositories."""

from collections.abc import Mapping, Sequence
from typing import TypeVar

from pandas import DataFrame

from .exceptions import AmbiguousRecordError
from .records import FaaRecord


RecordType = TypeVar("RecordType", bound=FaaRecord)


def related_record(
    nasr: Mapping[str, DataFrame],
    *,
    source: Mapping[str, object],
    target_table: str,
    columns: Sequence[tuple[str, str]],
    record_type: type[RecordType],
    relationship: str,
) -> RecordType | None:
    """Resolve at most one row using every column in a verified relationship."""

    frame = nasr.get(target_table)
    if frame is None:
        return None
    values = tuple(source.get(local) for local, _target in columns)
    if any(_normalized(value) == "" for value in values):
        return None
    rows = frame
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


__all__ = ["related_record"]
