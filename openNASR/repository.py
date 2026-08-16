"""Lightweight table discovery for a normalized NASR cycle."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path

from pandas import DataFrame, read_csv

from .exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
    SchemaMismatchError,
    TableNotFoundError,
)
from .records import (
    AirportRecord,
    DmeRecord,
    FaaRecord,
    FixRecord,
    GlideSlopeRecord,
    IlsRecord,
    MarkerRecord,
    NavaidRecord,
    RunwayEndRecord,
    RunwayRecord,
)


def discover_tables(cycle_path: str | Path) -> tuple[str, ...]:
    """Return CSV table names without opening CSV contents."""

    root = Path(cycle_path)
    return tuple(sorted({path.stem.upper() for path in root.glob("*.csv")}))


def normalize_table_name(name: str) -> str:
    """Normalize a requested table name to its canonical uppercase form."""

    return name.strip().upper()


class TableRepository(Mapping[str, DataFrame]):
    """Repository shell exposing filesystem-backed table discovery."""

    def __init__(self, cycle_path: str | Path) -> None:
        self.cycle_path = Path(cycle_path)
        self._cache: dict[str, DataFrame] = {}
        self._indexes: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}
        self._normalized_indexes: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}

    @property
    def available_tables(self) -> tuple[str, ...]:
        return discover_tables(self.cycle_path)

    def table_path(self, name: str) -> Path:
        return self.cycle_path / f"{normalize_table_name(name)}.csv"

    def load(self, name: str) -> DataFrame:
        """Load a table once and cache its DataFrame for this repository."""

        normalized = normalize_table_name(name)
        if normalized not in self._cache:
            path = self.table_path(normalized)
            if not path.is_file():
                raise TableNotFoundError(f"NASR table {normalized!r} was not found")
            try:
                self._cache[normalized] = read_csv(path)
            except UnicodeDecodeError:
                self._cache[normalized] = read_csv(path, encoding="latin-1")
        return self._cache[normalized]

    def table(self, name: str, *, copy: bool = False) -> DataFrame:
        """Return the cached table; mutate it only if that shared state is intended.

        Pass ``copy=True`` when callers need an isolated DataFrame.
        """

        frame = self.load(name)
        return frame.copy(deep=True) if copy else frame

    def is_loaded(self, name: str) -> bool:
        return normalize_table_name(name) in self._cache

    def index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Build and cache a row-position index only when requested."""

        normalized = normalize_table_name(name)
        key = (normalized, column)
        if key not in self._indexes:
            index: dict[str, list[int]] = {}
            for position, value in enumerate(self.load(normalized)[column]):
                index.setdefault(str(value), []).append(position)
            self._indexes[key] = {value: tuple(rows) for value, rows in index.items()}
        return self._indexes[key]

    def normalized_index(self, name: str, column: str) -> dict[str, tuple[int, ...]]:
        """Build and cache case-insensitive identifier positions."""

        normalized = normalize_table_name(name)
        key = (normalized, column)
        if key not in self._normalized_indexes:
            index: dict[str, list[int]] = {}
            for position, value in enumerate(self.load(normalized)[column]):
                index.setdefault(str(value).strip().upper(), []).append(position)
            self._normalized_indexes[key] = {
                value: tuple(rows) for value, rows in index.items()
            }
        return self._normalized_indexes[key]

    def __getitem__(self, name: str) -> DataFrame:
        """Provide mapping-style compatibility for legacy table access."""

        return self.load(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self.available_tables)

    def __len__(self) -> int:
        return len(self.available_tables)


class AirportRepository:
    """Lookup lossless airport records in a loaded NASR cycle."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @property
    def _table(self) -> DataFrame:
        return self._nasr["APT_BASE"]

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def get(self, identifier: str) -> AirportRecord:
        """Return one airport matching FAA or ICAO identifier case-insensitively."""
        normalized_identifier = self._normalized(identifier)
        rows = self._table[
            self._table["ARPT_ID"].map(self._normalized).eq(normalized_identifier)
            | self._table["ICAO_ID"].map(self._normalized).eq(normalized_identifier)
        ]
        records = tuple(
            self._airport_record(row) for row in rows.to_dict(orient="records")
        )
        if not records:
            raise RecordNotFoundError(entity_type="Airport", identifier=identifier)
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="Airport",
                identifier=identifier,
                candidates=records,
            )
        return records[0]

    def _airport_record(self, row: dict[str, object]) -> AirportRecord:
        identifier = self._normalized(row["ARPT_ID"])
        runways = self._related_records("APT_RWY", identifier, RunwayRecord)
        runway_ends = self._related_records("APT_RWY_END", identifier, RunwayEndRecord)
        self._validate_reciprocal_runway_ends(identifier, runways, runway_ends)
        return AirportRecord(
            row,
            runways=runways,
            runway_ends=runway_ends,
            ils=self._related_records("ILS_BASE", identifier, IlsRecord),
            dmes=self._related_records("ILS_DME", identifier, DmeRecord),
            glide_slopes=self._related_records("ILS_GS", identifier, GlideSlopeRecord),
            markers=self._related_records("ILS_MKR", identifier, MarkerRecord),
        )

    def _related_records(self, table: str, identifier: str, record_type):
        frame = self._nasr.get(table)
        if frame is None or "ARPT_ID" not in frame.columns:
            return ()
        rows = frame[frame["ARPT_ID"].map(self._normalized).eq(identifier)]
        return tuple(record_type(row) for row in rows.to_dict(orient="records"))

    @classmethod
    def _validate_reciprocal_runway_ends(
        cls,
        airport_identifier: str,
        runways: tuple[RunwayRecord, ...],
        runway_ends: tuple[RunwayEndRecord, ...],
    ) -> None:
        available = {
            cls._normalized(record["RWY_END_ID"])
            for record in runway_ends
            if "RWY_END_ID" in record
        }
        for runway in runways:
            ends = str(runway["RWY_ID"]).split("/")
            invalid = len(ends) != 2 or any(
                cls._normalized(end) not in available for end in ends
            )
            if invalid:
                raise SchemaMismatchError(
                    "Runway is missing a reciprocal runway-end record",
                    table="APT_RWY_END",
                    airport=airport_identifier,
                    runway_id=runway["RWY_ID"],
                )


class RecordRepository:
    """Normalized record lookup for tables with documented identifier columns."""

    def __init__(
        self,
        frame: DataFrame,
        *,
        entity_type: str,
        identifier_columns: tuple[str, ...],
    ) -> None:
        self._frame = frame
        self.entity_type = entity_type
        self.identifier_columns = identifier_columns

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def _identifier_values(self, identifier: object) -> tuple[object, ...]:
        if len(self.identifier_columns) == 1:
            return (identifier,)
        if not isinstance(identifier, tuple) or len(identifier) != len(
            self.identifier_columns
        ):
            columns = ", ".join(self.identifier_columns)
            raise ValueError(f"{self.entity_type} identifiers require ({columns})")
        return identifier

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[FaaRecord, ...]:
        """Return records matching a normalized identifier and every supplied filter."""
        rows = self._frame
        if identifier is not None:
            for column, value in zip(
                self.identifier_columns, self._identifier_values(identifier)
            ):
                rows = rows[
                    rows[column].map(self._normalized).eq(self._normalized(value))
                ]
        for column, value in filters.items():
            if value is not None:
                rows = rows[
                    rows[column].map(self._normalized).eq(self._normalized(value))
                ]
        return tuple(FaaRecord(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object, **filters: object) -> FaaRecord:
        """Return exactly one normalized identifier match with optional filters."""
        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


class FixRepository(RecordRepository):
    """Lookup typed fix records by normalized FAA identifier."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        super().__init__(
            nasr["FIX_BASE"], entity_type="Fix", identifier_columns=("FIX_ID",)
        )

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[FixRecord, ...]:
        records = super().find(identifier, **filters)
        return tuple(FixRecord(record.as_dict()) for record in records)

    def get(self, identifier: object, **filters: object) -> FixRecord:
        record = super().get(identifier, **filters)
        return FixRecord(record.as_dict())


class NavaidRepository(RecordRepository):
    """Lookup navaids with optional conjunctive location and type filters."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        super().__init__(
            nasr["NAV_BASE"], entity_type="Navaid", identifier_columns=("NAV_ID",)
        )

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[NavaidRecord, ...]:
        state = filters.pop("state", None)
        country = filters.pop("country", None)
        artcc = filters.pop("artcc", None)
        nav_type = filters.pop("nav_type", None)
        nav_type_alias = filters.pop("navType", None)
        if nav_type_alias is not None:
            if not isinstance(nav_type_alias, str):
                raise ValueError("navType must be a string")
            if nav_type is not None and not isinstance(nav_type, str):
                raise ValueError("nav_type must be a string")
            if nav_type is not None and self._normalized(
                nav_type_alias
            ) != self._normalized(nav_type):
                raise ValueError(
                    "navType and nav_type must agree when both are supplied"
                )
            nav_type = nav_type_alias
        if filters:
            unexpected = ", ".join(sorted(filters))
            raise ValueError(f"Unsupported Navaid filters: {unexpected}")
        for name, value in (
            ("state", state),
            ("country", country),
            ("artcc", artcc),
            ("nav_type", nav_type),
        ):
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} must be a string")
        rows = self._frame
        if identifier is not None:
            rows = rows[
                rows["NAV_ID"].map(self._normalized).eq(self._normalized(identifier))
            ]
        for column, value in (
            ("STATE_CODE", state),
            ("COUNTRY_CODE", country),
            ("NAV_TYPE", nav_type),
        ):
            if value is not None:
                rows = rows[
                    rows[column].map(self._normalized).eq(self._normalized(value))
                ]
        if artcc is not None:
            normalized = self._normalized(artcc)
            rows = rows[
                rows["HIGH_ALT_ARTCC_ID"].map(self._normalized).eq(normalized)
                | rows["LOW_ALT_ARTCC_ID"].map(self._normalized).eq(normalized)
            ]
        return tuple(NavaidRecord(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object, **filters: object) -> NavaidRecord:
        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type="Navaid", identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="Navaid",
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


__all__ = [
    "AirportRepository",
    "FixRepository",
    "NavaidRepository",
    "RecordRepository",
    "TableRepository",
    "discover_tables",
    "normalize_table_name",
]
