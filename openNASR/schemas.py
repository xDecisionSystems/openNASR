"""Versioned FAA NASR schema metadata and structural validation."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pandas import DataFrame

from .exceptions import ConfigurationError, SchemaMismatchError, TableNotFoundError


SCHEMA_SUFFIX = "_CSV_DATA_STRUCTURE"
SCHEMA_COLUMNS = (
    "CSV File",
    "Column Name",
    "Max Length",
    "Data Type",
    "Nullable",
)


@dataclass(frozen=True)
class ColumnSchema:
    """FAA-declared metadata for one CSV column.

    ``name`` is the column's canonical name, normalized to match the actual
    CSV data-file header casing used by :meth:`SchemaCatalog.validate`. FAA's
    own ``*_CSV_DATA_STRUCTURE.csv`` schema-description files sometimes
    declare a column with different casing than the data file actually uses
    (for example ``CDR`` declares ``RCODE`` but the data file header is
    ``RCode``). When that happens, ``faa_declared_name`` preserves the
    schema-description file's original spelling so schema *identification*
    (which parses those files at runtime) can still recognize a supported
    schema; it is ``None`` when the declared and actual names already match.
    """

    name: str
    faa_type: str
    max_length: str | None
    nullable: bool
    faa_declared_name: str | None = None

    @property
    def declared_name(self) -> str:
        """The name as it appears in a real schema-description file."""
        return self.faa_declared_name or self.name


@dataclass(frozen=True)
class TableSchema:
    """Ordered FAA-declared columns for one operational table."""

    name: str
    columns: tuple[ColumnSchema, ...]


@dataclass(frozen=True)
class ValidationReport:
    """Structural differences between a DataFrame and a supported schema."""

    table: str
    schema_id: str
    schema_description_file: str
    missing_required_columns: tuple[str, ...] = ()
    unexpected_columns: tuple[str, ...] = ()
    type_differences: tuple[str, ...] = ()

    @property
    def compatible(self) -> bool:
        return not (
            self.missing_required_columns
            or self.unexpected_columns
            or self.type_differences
        )

    def require_compatible(
        self,
        *,
        cycle: str | Path | None = None,
        table_spec: object | None = None,
        record_class: type[object] | None = None,
    ) -> None:
        """Raise a detailed error if this report contains schema drift."""

        if self.compatible:
            return
        instructions = (
            "Update openNASR/schemas.py, openNASR/registry.py, the relevant "
            "domain module and record class, schema fixtures, the coverage "
            "manifest, and PLAN.md before accepting this FAA schema."
        )
        message = (
            f"Unsupported schema drift for {self.table} in {cycle or 'unknown cycle'} "
            f"({self.schema_id}, {self.schema_description_file}): "
            f"missing={list(self.missing_required_columns)}, "
            f"unexpected={list(self.unexpected_columns)}, "
            f"type_differences={list(self.type_differences)}. {instructions}"
        )
        raise SchemaMismatchError(
            message,
            cycle=str(cycle) if cycle is not None else None,
            table=self.table,
            schema_id=self.schema_id,
            schema_description_file=self.schema_description_file,
            missing_columns=self.missing_required_columns,
            unexpected_columns=self.unexpected_columns,
            type_differences=self.type_differences,
            table_spec=table_spec,
            record_class=record_class,
            instructions=instructions,
        )


def parse_schema_description_tables(path: str | Path) -> dict[str, TableSchema]:
    """Parse one FAA schema-description CSV and group rows by ``CSV File``."""

    source = Path(path)
    grouped: dict[str, list[ColumnSchema]] = {}
    with source.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SCHEMA_COLUMNS:
            raise SchemaMismatchError(
                f"Unexpected schema-description columns in {source}: "
                f"{reader.fieldnames}; expected {list(SCHEMA_COLUMNS)}",
                schema_description_file=str(source),
                missing_columns=tuple(
                    name
                    for name in SCHEMA_COLUMNS
                    if name not in (reader.fieldnames or ())
                ),
                unexpected_columns=tuple(
                    name
                    for name in (reader.fieldnames or ())
                    if name not in SCHEMA_COLUMNS
                ),
            )
        for row in reader:
            nullable = row["Nullable"].strip().lower()
            if nullable not in {"yes", "no"}:
                raise SchemaMismatchError(
                    f"Unexpected Nullable value {row['Nullable']!r} in {source}",
                    schema_description_file=str(source),
                    table=row["CSV File"],
                )
            grouped.setdefault(row["CSV File"], []).append(
                ColumnSchema(
                    name=row["Column Name"],
                    faa_type=row["Data Type"],
                    max_length=row["Max Length"] or None,
                    nullable=nullable == "yes",
                )
            )
    return {
        name: TableSchema(name=name, columns=tuple(columns))
        for name, columns in grouped.items()
    }


def parse_schema_description(path: str | Path, table_name: str) -> list[ColumnSchema]:
    """Return the declared columns for one table in a schema-description file."""

    tables = parse_schema_description_tables(path)
    try:
        return list(tables[table_name].columns)
    except KeyError as error:
        raise TableNotFoundError(
            f"{table_name} is not described by {Path(path).name}"
        ) from error


class SchemaCatalog:
    """Catalog of the checked-in supported NASR schema generations."""

    SUPPORTED_SCHEMA_IDS = ("pre_2026_09", "nasr_2026_09")

    def __init__(self, manifest_dir: str | Path | None = None) -> None:
        if manifest_dir is None:
            manifest_dir = (
                Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "manifests"
            )
        self.manifest_dir = Path(manifest_dir)
        if not self.manifest_dir.is_dir():
            raise ConfigurationError(
                f"NASR schema manifest directory does not exist: {self.manifest_dir}"
            )
        self._manifests = {
            schema_id: json.loads(
                (self.manifest_dir / f"{schema_id}.json").read_text(encoding="utf-8")
            )
            for schema_id in self.SUPPORTED_SCHEMA_IDS
        }
        self._tables = {
            schema_id: self._tables_from_manifest(manifest)
            for schema_id, manifest in self._manifests.items()
        }

    @staticmethod
    def _tables_from_manifest(manifest: Mapping[str, Any]) -> dict[str, TableSchema]:
        return {
            name: TableSchema(
                name=name,
                columns=tuple(
                    ColumnSchema(
                        name=column["name"],
                        faa_type=column["faa_type"],
                        max_length=column["max_length"],
                        nullable=column["nullable"],
                        faa_declared_name=column.get("faa_declared_name"),
                    )
                    for column in table["columns"]
                ),
            )
            for name, table in manifest["tables"].items()
        }

    def manifest(self, schema_id: str) -> Mapping[str, Any]:
        try:
            return self._manifests[schema_id]
        except KeyError as error:
            raise SchemaMismatchError(
                f"Unsupported schema id {schema_id!r}; expected one of "
                f"{list(self.SUPPORTED_SCHEMA_IDS)}",
                schema_id=schema_id,
            ) from error

    def table(self, name: str, schema_id: str) -> TableSchema:
        try:
            return self._tables[schema_id][name.upper()]
        except KeyError as error:
            raise TableNotFoundError(
                f"Table {name!r} is not present in schema {schema_id!r}"
            ) from error

    @staticmethod
    def _fingerprint(tables: Mapping[str, TableSchema]) -> tuple[object, ...]:
        """Fingerprint using each column's schema-description-file spelling.

        ``parse_schema_description_tables`` (used both here for the checked-in
        manifests and at runtime for a real cycle) always reads a column's
        name as declared in the ``*_CSV_DATA_STRUCTURE.csv`` file itself. The
        manifest's ``ColumnSchema.name`` may differ from that declared
        spelling (see :class:`ColumnSchema`), so the fingerprint must compare
        ``declared_name`` on both sides, not ``name``, or a genuine supported
        cycle whose schema-description file uses FAA's original casing would
        never match.
        """
        return tuple(
            (
                name,
                tuple(
                    (column.declared_name, column.faa_type) for column in table.columns
                ),
            )
            for name, table in sorted(tables.items())
        )

    def identify_schema(self, cycle_path: str | Path) -> str:
        path = Path(cycle_path)
        described: dict[str, TableSchema] = {}
        files = sorted(path.rglob(f"*{SCHEMA_SUFFIX}.csv"))
        for schema_file in files:
            described.update(parse_schema_description_tables(schema_file))
        fingerprint = self._fingerprint(described)
        for schema_id, supported in self._tables.items():
            if fingerprint == self._fingerprint(supported):
                return schema_id
        raise SchemaMismatchError(
            f"The schema fingerprint in {path} is not supported. Parsed "
            f"{len(described)} tables from {len(files)} schema-description files; "
            f"supported schemas are {list(self.SUPPORTED_SCHEMA_IDS)}.",
            cycle=str(path),
            discovered_tables=tuple(sorted(described)),
            schema_description_files=tuple(str(file) for file in files),
            supported_schema_ids=self.SUPPORTED_SCHEMA_IDS,
        )

    def validate(
        self,
        name: str,
        frame: DataFrame,
        schema_id: str,
        *,
        declared_types: Mapping[str, str] | None = None,
    ) -> ValidationReport:
        schema = self.table(name, schema_id)
        expected_names = tuple(column.name for column in schema.columns)
        actual_names = tuple(str(column) for column in frame.columns)
        expected_set = set(expected_names)
        actual_set = set(actual_names)
        expected_types = {column.name: column.faa_type for column in schema.columns}
        type_differences: tuple[str, ...] = ()
        if declared_types is not None:
            type_differences = tuple(
                f"{column}: expected {expected_types[column]}, "
                f"got {declared_types[column]}"
                for column in sorted(expected_set & declared_types.keys())
                if expected_types[column] != declared_types[column]
            )
        manifest_table = self.manifest(schema_id)["tables"][schema.name]
        return ValidationReport(
            table=schema.name,
            schema_id=schema_id,
            schema_description_file=manifest_table["schema_description_file"],
            missing_required_columns=tuple(
                column for column in expected_names if column not in actual_set
            ),
            unexpected_columns=tuple(
                column for column in actual_names if column not in expected_set
            ),
            type_differences=type_differences,
        )


__all__ = [
    "ColumnSchema",
    "SchemaCatalog",
    "TableSchema",
    "ValidationReport",
    "parse_schema_description",
    "parse_schema_description_tables",
]
