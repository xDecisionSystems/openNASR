"""The manifest that marks a published build as validated."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Mapping

from .keys import (
    LAYOUT_VERSION,
    BucketKeyError,
    BuildKeys,
    build_keys,
    class_airspace_source_key,
)

_SHA = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ManifestError(ValueError):
    """Raised for a manifest that is malformed, inconsistent or unsupported."""


@dataclass(frozen=True)
class ArtifactRef:
    key: str
    sha256: str
    size: int


@dataclass(frozen=True)
class ClassAirspace:
    """Class B/C/D/E polygons derived from the FAA shapefile for this cycle."""

    source: ArtifactRef  # the FAA class_airspace_shape_files.zip
    parquet: ArtifactRef  # the derived polygons, one row per FAA record
    rows: int


@dataclass(frozen=True)
class Manifest:
    """What a reader needs to fetch, verify and trust one build.

    ``procedure_order`` is carried so a reader can refuse a cycle whose FAA
    schema declares an ordering it does not support, without opening it.
    """

    effective_date: str
    builder: int
    zip: ArtifactRef
    duckdb: ArtifactRef
    sidecar: ArtifactRef
    duckdb_version: str
    schema_id: str | None
    procedure_order: str | None
    source_schema_fingerprint: str
    tables: Mapping[str, int]
    created_at: str
    archiver_version: str
    layout_version: int = LAYOUT_VERSION
    class_airspace: ClassAirspace | None = None

    def keys(self) -> BuildKeys:
        return build_keys(self.effective_date, self.zip.sha256, self.builder)

    def __post_init__(self) -> None:
        if self.layout_version != LAYOUT_VERSION:
            raise ManifestError(
                f"unsupported layout version {self.layout_version!r}; "
                f"this reader supports {LAYOUT_VERSION}"
            )
        if not _DATE.match(self.effective_date):
            raise ManifestError(f"bad effective date: {self.effective_date!r}")
        for name, ref in (
            ("zip", self.zip),
            ("duckdb", self.duckdb),
            ("sidecar", self.sidecar),
        ):
            if not _SHA.match(ref.sha256):
                raise ManifestError(f"{name} hash must be 64 lowercase hex characters")
            if ref.size < 0:
                raise ManifestError(f"{name} size must not be negative")
        if not _SHA.match(self.source_schema_fingerprint):
            raise ManifestError("source schema fingerprint must be a sha256 hex digest")
        try:
            expected = self.keys()
        except BucketKeyError as error:
            raise ManifestError(str(error)) from error
        if self.class_airspace is not None:
            extra = self.class_airspace
            for name, ref in (("source", extra.source), ("parquet", extra.parquet)):
                if not _SHA.match(ref.sha256) or ref.size < 0:
                    raise ManifestError(
                        f"class airspace {name} hash or size is invalid"
                    )
            if extra.rows < 0:
                raise ManifestError("class airspace row count must not be negative")
            try:
                source_key = class_airspace_source_key(
                    self.effective_date, self.zip.sha256, extra.source.sha256
                )
            except BucketKeyError as error:
                raise ManifestError(str(error)) from error
            if (
                extra.source.key != source_key
                or extra.parquet.key != expected.class_airspace
            ):
                raise ManifestError(
                    "class airspace keys do not match the layout for this build"
                )
        if (
            self.zip.key != expected.zip
            or self.duckdb.key != expected.duckdb
            or self.sidecar.key != expected.sidecar
        ):
            raise ManifestError(
                "artifact keys do not match the layout for this date, hash and builder"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "layout_version": self.layout_version,
            "effective_date": self.effective_date,
            "builder": self.builder,
            "zip": _ref_dict(self.zip),
            "duckdb": _ref_dict(self.duckdb),
            "sidecar": _ref_dict(self.sidecar),
            "duckdb_version": self.duckdb_version,
            "schema_id": self.schema_id,
            "procedure_order": self.procedure_order,
            "source_schema_fingerprint": self.source_schema_fingerprint,
            "tables": dict(sorted(self.tables.items())),
            "created_at": self.created_at,
            "archiver_version": self.archiver_version,
            "class_airspace": _airspace_dict(self.class_airspace),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str | bytes) -> "Manifest":
        try:
            value = json.loads(text)
        except (ValueError, UnicodeDecodeError) as error:
            raise ManifestError("manifest is not valid JSON") from error
        return cls.from_dict(value)

    @classmethod
    def from_dict(cls, value: Any) -> "Manifest":
        if not isinstance(value, Mapping):
            raise ManifestError("manifest must be a JSON object")
        required = (
            "layout_version", "effective_date", "builder", "zip", "duckdb", "sidecar",
            "duckdb_version", "schema_id", "procedure_order",
            "source_schema_fingerprint", "tables", "created_at", "archiver_version",
        )  # fmt: skip
        missing = [name for name in required if name not in value]
        if missing:
            raise ManifestError("manifest is missing: " + ", ".join(missing))
        try:
            tables = value["tables"]
            if not isinstance(tables, Mapping) or not all(
                isinstance(k, str) and type(v) is int and v >= 0
                for k, v in tables.items()
            ):
                raise ManifestError("tables must map names to row counts")
            return cls(
                layout_version=_int(value["layout_version"], "layout_version"),
                effective_date=_str(value["effective_date"], "effective_date"),
                builder=_int(value["builder"], "builder"),
                zip=_ref(value["zip"], "zip"),
                duckdb=_ref(value["duckdb"], "duckdb"),
                sidecar=_ref(value["sidecar"], "sidecar"),
                duckdb_version=_str(value["duckdb_version"], "duckdb_version"),
                schema_id=_opt_str(value["schema_id"], "schema_id"),
                procedure_order=_opt_str(value["procedure_order"], "procedure_order"),
                source_schema_fingerprint=_str(
                    value["source_schema_fingerprint"], "source_schema_fingerprint"
                ),
                tables=dict(tables),
                created_at=_str(value["created_at"], "created_at"),
                archiver_version=_str(value["archiver_version"], "archiver_version"),
                class_airspace=_airspace(value.get("class_airspace")),
            )
        except ManifestError:
            raise
        except (TypeError, ValueError) as error:
            raise ManifestError("manifest has invalid values") from error


def _ref_dict(ref: ArtifactRef) -> dict[str, Any]:
    return {"key": ref.key, "sha256": ref.sha256, "size": ref.size}


def _str(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ManifestError(f"{name} must be a string")
    return value


def _opt_str(value: Any, name: str) -> str | None:
    return None if value is None else _str(value, name)


def _int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ManifestError(f"{name} must be an integer")
    return value


def _ref(value: Any, name: str) -> ArtifactRef:
    if not isinstance(value, Mapping):
        raise ManifestError(f"{name} must be an object")
    return ArtifactRef(
        key=_str(value.get("key"), f"{name}.key"),
        sha256=_str(value.get("sha256"), f"{name}.sha256"),
        size=_int(value.get("size"), f"{name}.size"),
    )


def _airspace_dict(value: ClassAirspace | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "source": _ref_dict(value.source),
        "parquet": _ref_dict(value.parquet),
        "rows": value.rows,
    }


def _airspace(value: Any) -> ClassAirspace | None:
    if value is None:  # builds made before Class B/C/D/E polygons have none
        return None
    if not isinstance(value, Mapping):
        raise ManifestError("class_airspace must be an object or null")
    return ClassAirspace(
        source=_ref(value.get("source"), "class_airspace.source"),
        parquet=_ref(value.get("parquet"), "class_airspace.parquet"),
        rows=_int(value.get("rows"), "class_airspace.rows"),
    )
