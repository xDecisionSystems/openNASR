"""Entity repositories for lookup and relationship assembly over a NASR cycle.

The lazy, indexed CSV table repository (:class:`~openNASR.tables.TableRepository`
and its helpers) lives in :mod:`openNASR.tables`. It is re-exported here for
backward compatibility with existing imports from this module.
"""

from __future__ import annotations

from collections.abc import Mapping

from numpy import ndarray
from pandas import DataFrame

from .exceptions import (
    AmbiguousRecordError,
    RecordNotFoundError,
    SchemaMismatchError,
)
from .airspace import ClassAirspaceRecord
from .airport import AirportRecord
from .fix import FixRecord
from .ils import DmeRecord, GlideSlopeRecord, IlsRecord, MarkerRecord
from .military import MilitaryOperationRecord
from .nav import NavaidRecord
from .records import FaaRecord
from .rwy import RunwayEndRecord, RunwayRecord
from .airspace import ClassAirspace
from .military import MilitaryOperation
from .registry import AIRPORT_SITE_KEY
from .tables import TableRepository, discover_tables, normalize_table_name


class AirportRepository:
    """Lookup lossless airport records in a loaded NASR cycle."""

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr
        self._related_indexes: dict[tuple[str, int], dict[str, ndarray]] = {}

    @property
    def _table(self) -> DataFrame:
        return self._nasr["APT_BASE"]

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def get(self, identifier: str) -> AirportRecord:
        """Return one airport matching FAA or ICAO identifier case-insensitively."""
        normalized_identifier = self._normalized(identifier)
        by_faa_id = self._related_index("APT_BASE:ARPT_ID", self._table, "ARPT_ID")
        by_icao_id = self._related_index("APT_BASE:ICAO_ID", self._table, "ICAO_ID")
        matches = {
            row_id: row
            for positions in (
                by_faa_id.get(normalized_identifier),
                by_icao_id.get(normalized_identifier),
            )
            if positions is not None
            for row_id, row in self._table.iloc[positions].iterrows()
        }
        records = tuple(self._airport_record(row.to_dict()) for row in matches.values())
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
            class_airspace=self._class_airspace(row),
            military_operations=self._military_operations(row),
        )

    def _class_airspace(self, airport: dict[str, object]) -> ClassAirspace | None:
        """Return the sole class-airspace row joined through the site key."""

        frame = self._nasr.get("CLS_ARSP")
        if frame is None or any(
            column not in frame.columns for column in AIRPORT_SITE_KEY
        ):
            return None
        if any(column not in airport for column in AIRPORT_SITE_KEY):
            return None
        site_values = tuple(airport[column] for column in AIRPORT_SITE_KEY)
        if any(value is None or str(value).strip() == "" for value in site_values):
            return None
        rows = frame
        for column, value in zip(AIRPORT_SITE_KEY, site_values):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        records = tuple(
            ClassAirspace(ClassAirspaceRecord(row))
            for row in rows.to_dict(orient="records")
        )
        if not records:
            return None
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type="ClassAirspace",
                identifier=site_values,
                candidates=records,
            )
        return records[0]

    def _military_operations(
        self, airport: dict[str, object]
    ) -> tuple[MilitaryOperation, ...]:
        """Return military-operation rows joined through the complete site key."""

        frame = self._nasr.get("MIL_OPS")
        if frame is None or any(
            column not in frame.columns for column in AIRPORT_SITE_KEY
        ):
            return ()
        if any(column not in airport for column in AIRPORT_SITE_KEY):
            return ()
        site_values = tuple(airport[column] for column in AIRPORT_SITE_KEY)
        if any(value is None or str(value).strip() == "" for value in site_values):
            return ()
        rows = frame
        for column, value in zip(AIRPORT_SITE_KEY, site_values):
            rows = rows[rows[column].map(self._normalized).eq(self._normalized(value))]
        return tuple(
            MilitaryOperation(MilitaryOperationRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def _related_records(self, table: str, identifier: str, record_type):
        frame = self._nasr.get(table)
        if frame is None or "ARPT_ID" not in frame.columns:
            return ()
        index = self._related_index(table, frame, "ARPT_ID")
        positions = index.get(identifier)
        rows = frame.iloc[positions] if positions is not None else frame.iloc[0:0]
        return tuple(record_type(row) for row in rows.to_dict(orient="records"))

    def _related_index(
        self, cache_key: str, frame: DataFrame, column: str
    ) -> dict[str, ndarray]:
        """Build and cache a ``column`` -> source-row-position index once.

        Every airport lookup through this repository joins the same handful
        of related tables (runways, runway ends, ILS components) and matches
        against the same columns (``ARPT_ID``/``ICAO_ID`` on ``APT_BASE``
        itself); indexing each column once avoids re-scanning and
        re-normalizing it on every airport. ``groupby.indices`` retains only
        row positions, so a high-cardinality column does not eagerly
        materialize one DataFrame per airport.
        """
        key = (cache_key, id(frame))
        if key not in self._related_indexes:
            normalized = frame[column].map(self._normalized)
            self._related_indexes[key] = frame.groupby(normalized).indices
        return self._related_indexes[key]

    @classmethod
    def _validate_reciprocal_runway_ends(
        cls,
        airport_identifier: str,
        runways: tuple[RunwayRecord, ...],
        runway_ends: tuple[RunwayEndRecord, ...],
    ) -> None:
        """Validate that every declared runway end actually has a record.

        A runway's ``RWY_ID`` is reciprocal (``"01/19"``) for a standard
        paved runway, or a single token (``"H1"``) for a helipad or other
        non-reciprocal landing surface. Only the reciprocal form requires
        exactly two ends; a single-token ``RWY_ID`` requires only itself.
        """
        available = {
            cls._normalized(record["RWY_END_ID"])
            for record in runway_ends
            if "RWY_END_ID" in record
        }
        for runway in runways:
            rwy_id = str(runway["RWY_ID"])
            ends = rwy_id.split("/")
            expected_end_count = 2 if "/" in rwy_id else 1
            invalid = len(ends) != expected_end_count or any(
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
    """Normalized record lookup for tables with documented identifier columns.

    ``frame`` may be an already-loaded DataFrame, or ``None`` if the
    subclass instead sets ``self._nasr``/``self._table_name`` so the table is
    only loaded from ``nasr[table_name]`` the first time a lookup actually
    needs it (see :class:`FixRepository`/:class:`NavaidRepository`) — this
    keeps constructing the repository, which ``NASR.__init__`` does eagerly
    for every family, from forcing a table load a caller may never request.
    """

    def __init__(
        self,
        frame: DataFrame | None,
        *,
        entity_type: str,
        identifier_columns: tuple[str, ...],
    ) -> None:
        self._loaded_frame = frame
        self._nasr: Mapping[str, DataFrame] | None = None
        self._table_name: str | None = None
        self.entity_type = entity_type
        self.identifier_columns = identifier_columns
        self._normalized_indexes: dict[str, dict[str, ndarray]] = {}

    @property
    def _frame(self) -> DataFrame:
        if self._loaded_frame is None:
            assert self._nasr is not None and self._table_name is not None
            self._loaded_frame = self._nasr[self._table_name]
        return self._loaded_frame

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

    def _normalized_index(self, column: str) -> dict[str, ndarray]:
        """Build and cache a normalized-value -> source-row-position index.

        Repeated identifier lookups on the same column then cost one dict
        lookup instead of re-scanning and re-normalizing the full column.
        ``groupby.indices`` builds every group in one pass without eagerly
        materializing one DataFrame per distinct identifier; masking per
        unique value would instead rescan the whole column once per group.
        """
        if column not in self._normalized_indexes:
            normalized = self._frame[column].map(self._normalized)
            self._normalized_indexes[column] = self._frame.groupby(normalized).indices
        return self._normalized_indexes[column]

    def _rows_for_identifier_column(self, column: str, value: object) -> DataFrame:
        index = self._normalized_index(column)
        normalized_value = self._normalized(value)
        if normalized_value not in index:
            return self._frame.iloc[0:0]
        return self._frame.iloc[index[normalized_value]]

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[FaaRecord, ...]:
        """Return records matching a normalized identifier and every supplied filter."""
        rows = self._frame
        if identifier is not None:
            for column, value in zip(
                self.identifier_columns, self._identifier_values(identifier)
            ):
                candidates = self._rows_for_identifier_column(column, value)
                rows = rows.loc[rows.index.intersection(candidates.index)]
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
        super().__init__(None, entity_type="Fix", identifier_columns=("FIX_ID",))
        self._nasr = nasr
        self._table_name = "FIX_BASE"

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
        super().__init__(None, entity_type="Navaid", identifier_columns=("NAV_ID",))
        self._nasr = nasr
        self._table_name = "NAV_BASE"

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
            rows = self._rows_for_identifier_column("NAV_ID", identifier)
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
