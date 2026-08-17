"""Bounded, read-only table queries for immutable NASR cycles.

The module intentionally exposes a small typed query contract instead of a
general SQL escape hatch.  CSV uses a pandas DataFrame fallback while a
completed DuckDB store can apply the same allowlisted filters before rows are
materialized.
"""

from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from pandas import isna

from .exceptions import OpenNASRError

if TYPE_CHECKING:
    from .nasr import NASR


MAX_FIELDS = 64
MAX_FILTERS = 8
MAX_FILTER_VALUES = 100
MAX_PAGE_SIZE = 1_000
MAX_PAGE_PAYLOAD_BYTES = 8 * 1024 * 1024
_CURSOR_VERSION = 1


class QueryError(OpenNASRError):
    """Base class for public read-only query failures."""

    http_status = 400


class QueryValidationError(QueryError):
    """Raised when a query does not meet its bounded public contract."""

    http_status = 422


class QueryTableNotFoundError(QueryError):
    """Raised when a selected table is absent from the current cycle."""

    http_status = 404


class QueryFieldNotFoundError(QueryError):
    """Raised when a projection or filter names an unavailable field."""

    http_status = 422


class UnsupportedQueryOperatorError(QueryError):
    """Raised when a filter operator is outside the stable query surface."""

    http_status = 422


class InvalidQueryCursorError(QueryError):
    """Raised when a cursor is malformed or belongs to another query."""

    http_status = 422


class QueryResultTooLargeError(QueryError):
    """Raised when even one source row exceeds the response payload cap."""

    http_status = 413


class QueryOperator(str, Enum):
    """The only first-release filter operators."""

    EQ = "eq"
    IN = "in"


@dataclass(frozen=True)
class QueryFilter:
    """One typed, exact source-text predicate for :func:`query_table`."""

    field: str
    operator: QueryOperator | str
    value: str | tuple[str, ...]

    @classmethod
    def eq(cls, field: str, value: str) -> "QueryFilter":
        """Create an exact single-value predicate."""

        return cls(field=field, operator=QueryOperator.EQ, value=value)

    @classmethod
    def in_(cls, field: str, values: tuple[str, ...]) -> "QueryFilter":
        """Create an exact multi-value predicate."""

        return cls(field=field, operator=QueryOperator.IN, value=values)


@dataclass(frozen=True)
class QueryPage:
    """An immutable, source-ordered page with exact cycle provenance."""

    table: str
    fields: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]
    effective_date: str
    schema_fingerprint: str
    next_cursor: str | None
    storage: str


@dataclass(frozen=True)
class _NormalizedFilter:
    field: str
    operator: QueryOperator
    values: tuple[str, ...]

    def cursor_value(self) -> dict[str, object]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "values": self.values,
        }


def query_table(
    nasr: "NASR",
    table: str,
    *,
    filters: Iterable[QueryFilter] = (),
    fields: Sequence[str] | None = None,
    page_size: int = 100,
    cursor: str | None = None,
) -> QueryPage:
    """Return a bounded source-order page from one exact NASR cycle.

    Identifiers are checked against the selected cycle before any DuckDB
    statement is generated.  Filter values remain strings and are bound by the
    DuckDB implementation; callers cannot submit arbitrary SQL, ordering, or
    expressions through this API.
    """

    canonical_table = _canonical_table(nasr, table)
    columns = nasr._query_columns(canonical_table)
    selected_fields = _normalize_fields(fields, columns)
    normalized_filters = _normalize_filters(filters, columns)
    _validate_page_size(page_size)

    request_fingerprint = _request_fingerprint(
        canonical_table,
        selected_fields,
        normalized_filters,
        page_size,
    )
    start_row = _decode_cursor(
        cursor,
        effective_date=nasr.effective_date,
        schema_fingerprint=nasr.schema_fingerprint,
        request_fingerprint=request_fingerprint,
    )

    candidates = _query_candidates(
        nasr,
        canonical_table,
        selected_fields,
        normalized_filters,
        start_row=start_row,
        limit=page_size + 1,
    )
    has_more = len(candidates) > page_size
    candidates = candidates[:page_size]

    raw_rows: list[dict[str, str]] = []
    last_row: int | None = None
    for candidate_position, (row_position, values) in enumerate(candidates):
        row = {
            field: _source_text(value)
            for field, value in zip(selected_fields, values, strict=True)
        }
        prospective_has_more = has_more or candidate_position < len(candidates) - 1
        prospective_cursor = (
            _encode_cursor(
                effective_date=nasr.effective_date,
                schema_fingerprint=nasr.schema_fingerprint,
                request_fingerprint=request_fingerprint,
                next_row=row_position + 1,
            )
            if prospective_has_more
            else None
        )
        if (
            _page_payload_size(
                canonical_table,
                selected_fields,
                raw_rows + [row],
                nasr,
                next_cursor=prospective_cursor,
            )
            > MAX_PAGE_PAYLOAD_BYTES
        ):
            if not raw_rows:
                raise QueryResultTooLargeError(
                    "A single query row exceeds the maximum page payload."
                )
            has_more = True
            break
        raw_rows.append(row)
        last_row = row_position

    next_cursor = None
    if has_more and last_row is not None:
        next_cursor = _encode_cursor(
            effective_date=nasr.effective_date,
            schema_fingerprint=nasr.schema_fingerprint,
            request_fingerprint=request_fingerprint,
            next_row=last_row + 1,
        )

    return QueryPage(
        table=canonical_table,
        fields=selected_fields,
        rows=tuple(MappingProxyType(row) for row in raw_rows),
        effective_date=nasr.effective_date,
        schema_fingerprint=nasr.schema_fingerprint,
        next_cursor=next_cursor,
        storage=nasr.storage,
    )


def _canonical_table(nasr: "NASR", table: object) -> str:
    if not isinstance(table, str):
        raise QueryTableNotFoundError("The requested NASR table was not found.")
    canonical = table.strip().upper()
    if canonical not in nasr._query_table_names:
        raise QueryTableNotFoundError("The requested NASR table was not found.")
    return canonical


def _normalize_fields(
    fields: Sequence[str] | None, columns: tuple[str, ...]
) -> tuple[str, ...]:
    if fields is None:
        return columns
    if not isinstance(fields, Sequence) or isinstance(fields, str) or not fields:
        raise QueryValidationError(
            "fields must be a non-empty sequence of field names."
        )
    if len(fields) > MAX_FIELDS:
        raise QueryValidationError("fields exceeds the maximum selected field count.")
    available = {column.strip().upper(): column for column in columns}
    selected: list[str] = []
    used: set[str] = set()
    for field in fields:
        if not isinstance(field, str):
            raise QueryValidationError("fields must contain only field names.")
        normalized = field.strip().upper()
        if normalized in used:
            raise QueryValidationError("fields must not contain duplicates.")
        try:
            selected.append(available[normalized])
        except KeyError as error:
            raise QueryFieldNotFoundError(
                "A requested NASR field was not found."
            ) from error
        used.add(normalized)
    return tuple(selected)


def _normalize_filters(
    filters: Iterable[QueryFilter], columns: tuple[str, ...]
) -> tuple[_NormalizedFilter, ...]:
    if isinstance(filters, (str, bytes)):
        raise QueryValidationError("filters must contain QueryFilter values.")
    try:
        supplied = tuple(filters)
    except TypeError as error:
        raise QueryValidationError("filters must be iterable.") from error
    if len(supplied) > MAX_FILTERS:
        raise QueryValidationError("filters exceeds the maximum filter count.")
    available = {column.strip().upper(): column for column in columns}
    normalized: list[_NormalizedFilter] = []
    value_count = 0
    for item in supplied:
        if not isinstance(item, QueryFilter):
            raise QueryValidationError("filters must contain QueryFilter values.")
        if not isinstance(item.field, str):
            raise QueryValidationError("A query filter field must be a string.")
        try:
            field = available[item.field.strip().upper()]
        except KeyError as error:
            raise QueryFieldNotFoundError(
                "A filtered NASR field was not found."
            ) from error
        try:
            operator = QueryOperator(item.operator)
        except (TypeError, ValueError) as error:
            raise UnsupportedQueryOperatorError(
                "The query filter operator is not supported."
            ) from error
        values: tuple[str, ...]
        if operator is QueryOperator.EQ:
            if not isinstance(item.value, str):
                raise QueryValidationError("EQ filter values must be strings.")
            values = (item.value,)
        else:
            if not isinstance(item.value, tuple) or not item.value:
                raise QueryValidationError(
                    "IN filter values must be a non-empty tuple."
                )
            if not all(isinstance(value, str) for value in item.value):
                raise QueryValidationError("IN filter values must be strings.")
            values = item.value
        value_count += len(values)
        if value_count > MAX_FILTER_VALUES:
            raise QueryValidationError(
                "filters exceeds the maximum aggregate value count."
            )
        normalized.append(_NormalizedFilter(field, operator, values))
    return tuple(normalized)


def _validate_page_size(page_size: object) -> None:
    if (
        not isinstance(page_size, int)
        or isinstance(page_size, bool)
        or not 1 <= page_size <= MAX_PAGE_SIZE
    ):
        raise QueryValidationError("page_size must be an integer from 1 through 1000.")


def _query_candidates(
    nasr: "NASR",
    table: str,
    fields: tuple[str, ...],
    filters: tuple[_NormalizedFilter, ...],
    *,
    start_row: int,
    limit: int,
) -> list[tuple[int, tuple[object, ...]]]:
    store = nasr._query_table_store
    execute = getattr(store, "_query_rows", None)
    normalized_filters = tuple(
        (item.field, item.operator.value, item.values) for item in filters
    )
    if callable(execute):
        return execute(
            table,
            fields,
            normalized_filters,
            start_row=start_row,
            limit=limit,
        )

    # CSV (and any future non-querying store) takes the portable DataFrame
    # path.  It preserves source order and applies the exact same text-value
    # comparisons as the parameterized DuckDB path.
    frame = nasr._query_csv_frame(table)
    candidates: list[tuple[int, tuple[object, ...]]] = []
    for position, (_, source_row) in enumerate(frame.iterrows()):
        if position < start_row:
            continue
        if not _matches(source_row, filters):
            continue
        candidates.append((position, tuple(source_row[field] for field in fields)))
        if len(candidates) >= limit:
            break
    return candidates


def _matches(row: Any, filters: tuple[_NormalizedFilter, ...]) -> bool:
    for item in filters:
        value = _source_text(row[item.field])
        if item.operator is QueryOperator.EQ:
            if value != item.values[0]:
                return False
        elif value not in item.values:
            return False
    return True


def _source_text(value: object) -> str:
    """Produce the source-text representation used by both query backends."""

    if isinstance(value, str):
        return value
    try:
        if bool(isna(value)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _request_fingerprint(
    table: str,
    fields: tuple[str, ...],
    filters: tuple[_NormalizedFilter, ...],
    page_size: int,
) -> str:
    payload = {
        "fields": fields,
        "filters": [item.cursor_value() for item in filters],
        "page_size": page_size,
        "table": table,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _encode_cursor(
    *,
    effective_date: str,
    schema_fingerprint: str,
    request_fingerprint: str,
    next_row: int,
) -> str:
    payload = {
        "d": effective_date,
        "p": next_row,
        "r": request_fingerprint,
        "s": schema_fingerprint,
        "v": _CURSOR_VERSION,
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _decode_cursor(
    cursor: str | None,
    *,
    effective_date: str,
    schema_fingerprint: str,
    request_fingerprint: str,
) -> int:
    if cursor is None:
        return 0
    if not isinstance(cursor, str) or not cursor:
        raise InvalidQueryCursorError("The query cursor is invalid.")
    try:
        padding = "=" * (-len(cursor) % 4)
        value = json.loads(urlsafe_b64decode(cursor + padding).decode("utf-8"))
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        raise InvalidQueryCursorError("The query cursor is invalid.") from None
    if not isinstance(value, dict):
        raise InvalidQueryCursorError("The query cursor is invalid.")
    if (
        value.get("v") != _CURSOR_VERSION
        or value.get("d") != effective_date
        or value.get("s") != schema_fingerprint
        or value.get("r") != request_fingerprint
        or not isinstance(value.get("p"), int)
        or isinstance(value.get("p"), bool)
        or value["p"] < 0
    ):
        raise InvalidQueryCursorError("The query cursor does not match this query.")
    return value["p"]


def _page_payload_size(
    table: str,
    fields: tuple[str, ...],
    rows: list[dict[str, str]],
    nasr: "NASR",
    *,
    next_cursor: str | None,
) -> int:
    payload = {
        "effective_date": nasr.effective_date,
        "fields": fields,
        "next_cursor": next_cursor,
        "rows": rows,
        "schema_fingerprint": nasr.schema_fingerprint,
        "storage": nasr.storage,
        "table": table,
    }
    return len(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


__all__ = [
    "InvalidQueryCursorError",
    "MAX_FIELDS",
    "MAX_FILTERS",
    "MAX_FILTER_VALUES",
    "MAX_PAGE_PAYLOAD_BYTES",
    "MAX_PAGE_SIZE",
    "QueryError",
    "QueryFieldNotFoundError",
    "QueryFilter",
    "QueryOperator",
    "QueryPage",
    "QueryResultTooLargeError",
    "QueryTableNotFoundError",
    "QueryValidationError",
    "UnsupportedQueryOperatorError",
    "query_table",
]
