"""Schema-version-aware registry for supported FAA NASR tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .exceptions import SchemaMismatchError, TableNotFoundError
from .records import (
    ClassAirspaceRecord,
    CommunicationOutletRecord,
    FaaRecord,
    HoldingPatternChartRecord,
    HoldingPatternRecord,
    HoldingPatternRemarkRecord,
    HoldingPatternSpeedAltitudeRecord,
    MilitaryOperationRecord,
    FrequencyRecord,
)
from .schemas import SchemaCatalog


AIRPORT_SITE_KEY = ("SITE_NO", "SITE_TYPE_CODE")
AIRPORT_LINKED_TABLES = frozenset({"CLS_ARSP", "MIL_OPS"})
AIRWAY_KEY = ("REGULATORY", "AWY_LOCATION", "AWY_ID")
AIRWAY_SEGMENT_KEY = (*AIRWAY_KEY, "POINT_SEQ")
AIRWAY_TABLES = frozenset({"AWY_BASE", "AWY_SEG_ALT"})
HOLDING_PATTERN_KEY = ("HP_NAME", "HP_NO", "STATE_CODE", "COUNTRY_CODE")
HOLDING_PATTERN_TABLES = frozenset({"HPF_BASE", "HPF_CHRT", "HPF_RMK", "HPF_SPD_ALT"})
FREQUENCY_KEY = ("FACILITY", "FREQ", "FREQ_SUFFIX", "USE_CODE", "FREQ_USE")
RICH_RECORD_TYPES: Mapping[str, type[FaaRecord]] = {
    "CLS_ARSP": ClassAirspaceRecord,
    "MIL_OPS": MilitaryOperationRecord,
    "HPF_BASE": HoldingPatternRecord,
    "HPF_CHRT": HoldingPatternChartRecord,
    "HPF_RMK": HoldingPatternRemarkRecord,
    "HPF_SPD_ALT": HoldingPatternSpeedAltitudeRecord,
    "COM": CommunicationOutletRecord,
    "FRQ": FrequencyRecord,
}


@dataclass(frozen=True)
class IndexSpec:
    """Columns used by a named lookup index."""

    name: str
    columns: tuple[str, ...]
    unique: bool = False


@dataclass(frozen=True)
class RelationshipSpec:
    """Verified columns connecting one table to another."""

    name: str
    target_table: str
    local_columns: tuple[str, ...]
    target_columns: tuple[str, ...]


@dataclass(frozen=True)
class TableVariantSpec:
    """Metadata for one table in one supported schema generation."""

    schema_id: str
    identity_key: tuple[str, ...] | None = None
    indexes: tuple[IndexSpec, ...] = ()
    order_by: tuple[str, ...] = ()
    relationships: tuple[RelationshipSpec, ...] = ()
    required_columns: frozenset[str] = frozenset()
    optional: bool = False


@dataclass(frozen=True)
class TableSpec:
    """Record type and schema variants for one operational FAA table."""

    name: str
    record_type: type[FaaRecord]
    variants: tuple[TableVariantSpec, ...]


class TableRegistry:
    """Registry of every supported operational FAA table."""

    def __init__(
        self,
        specs: Iterable[TableSpec] | None = None,
        *,
        catalog: SchemaCatalog | None = None,
    ) -> None:
        self.catalog = catalog or SchemaCatalog()
        if specs is None:
            specs = self._build_specs()
        self._specs = {spec.name: spec for spec in specs}

    def _build_specs(self) -> tuple[TableSpec, ...]:
        manifests = {
            schema_id: self.catalog.manifest(schema_id)
            for schema_id in self.catalog.SUPPORTED_SCHEMA_IDS
        }
        table_names = sorted(
            set().union(*(manifest["tables"] for manifest in manifests.values()))
        )
        specs = []
        for table_name in table_names:
            variants = []
            for schema_id, manifest in manifests.items():
                if table_name not in manifest["tables"]:
                    continue
                schema = self.catalog.table(table_name, schema_id)
                identity_key: tuple[str, ...] | None = None
                indexes: tuple[IndexSpec, ...] = ()
                order_by: tuple[str, ...] = ()
                relationships: tuple[RelationshipSpec, ...] = ()
                if table_name in AIRPORT_LINKED_TABLES:
                    identity_key = AIRPORT_SITE_KEY
                    indexes = (
                        IndexSpec("site", AIRPORT_SITE_KEY, unique=True),
                        IndexSpec("airport_id", ("ARPT_ID",), unique=False),
                    )
                    relationships = (
                        RelationshipSpec(
                            "airport",
                            "APT_BASE",
                            AIRPORT_SITE_KEY,
                            AIRPORT_SITE_KEY,
                        ),
                    )
                elif table_name == "AWY_BASE":
                    identity_key = AIRWAY_KEY
                    indexes = (IndexSpec("airway", AIRWAY_KEY, unique=True),)
                    relationships = (
                        RelationshipSpec(
                            "segments",
                            "AWY_SEG_ALT",
                            AIRWAY_KEY,
                            AIRWAY_KEY,
                        ),
                    )
                elif table_name == "AWY_SEG_ALT":
                    identity_key = AIRWAY_SEGMENT_KEY
                    indexes = (
                        IndexSpec("segment", AIRWAY_SEGMENT_KEY, unique=True),
                        IndexSpec("airway", AIRWAY_KEY, unique=False),
                    )
                    order_by = ("POINT_SEQ",)
                    relationships = (
                        RelationshipSpec(
                            "airway",
                            "AWY_BASE",
                            AIRWAY_KEY,
                            AIRWAY_KEY,
                        ),
                    )
                elif table_name == "HPF_BASE":
                    identity_key = HOLDING_PATTERN_KEY
                    indexes = (
                        IndexSpec("holding_pattern", HOLDING_PATTERN_KEY, unique=True),
                    )
                    relationships = (
                        RelationshipSpec(
                            "charts",
                            "HPF_CHRT",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                        RelationshipSpec(
                            "remarks",
                            "HPF_RMK",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                        RelationshipSpec(
                            "speed_altitude_limits",
                            "HPF_SPD_ALT",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "HPF_CHRT":
                    identity_key = (*HOLDING_PATTERN_KEY, "CHARTING_TYPE_DESC")
                    indexes = (IndexSpec("holding_pattern", HOLDING_PATTERN_KEY),)
                    relationships = (
                        RelationshipSpec(
                            "holding_pattern",
                            "HPF_BASE",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "HPF_RMK":
                    identity_key = (
                        *HOLDING_PATTERN_KEY,
                        "TAB_NAME",
                        "REF_COL_NAME",
                        "REF_COL_SEQ_NO",
                    )
                    indexes = (IndexSpec("holding_pattern", HOLDING_PATTERN_KEY),)
                    order_by = ("TAB_NAME", "REF_COL_NAME", "REF_COL_SEQ_NO")
                    relationships = (
                        RelationshipSpec(
                            "holding_pattern",
                            "HPF_BASE",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "HPF_SPD_ALT":
                    identity_key = (*HOLDING_PATTERN_KEY, "SPEED_RANGE", "ALTITUDE")
                    indexes = (IndexSpec("holding_pattern", HOLDING_PATTERN_KEY),)
                    relationships = (
                        RelationshipSpec(
                            "holding_pattern",
                            "HPF_BASE",
                            HOLDING_PATTERN_KEY,
                            HOLDING_PATTERN_KEY,
                        ),
                    )
                elif table_name == "COM":
                    identity_key = ("COMM_LOC_ID",)
                    indexes = (
                        IndexSpec("communication_outlet", identity_key, unique=True),
                    )
                elif table_name == "FRQ":
                    identity_key = FREQUENCY_KEY
                    indexes = (
                        IndexSpec("frequency", FREQUENCY_KEY, unique=True),
                        IndexSpec("facility", ("FACILITY",), unique=False),
                    )
                variants.append(
                    TableVariantSpec(
                        schema_id=schema_id,
                        identity_key=identity_key,
                        indexes=indexes,
                        order_by=order_by,
                        relationships=relationships,
                        required_columns=frozenset(
                            column.name for column in schema.columns
                        ),
                    )
                )
            specs.append(
                TableSpec(
                    name=table_name,
                    record_type=RICH_RECORD_TYPES.get(table_name, FaaRecord),
                    variants=tuple(variants),
                )
            )
        return tuple(specs)

    def table(self, name: str) -> TableSpec:
        try:
            return self._specs[name.upper()]
        except KeyError as error:
            raise TableNotFoundError(f"Table {name!r} is not registered") from error

    def spec(self, name: str, schema_id: str) -> TableVariantSpec:
        table = self.table(name)
        for variant in table.variants:
            if variant.schema_id == schema_id:
                return variant
        raise TableNotFoundError(
            f"Table {name!r} has no variant for schema {schema_id!r}"
        )

    def supported_tables(self) -> frozenset[str]:
        return frozenset(self._specs)

    def unmodeled_tables(self, available: Iterable[str | Path]) -> frozenset[str]:
        names = {Path(item).stem.upper() for item in available}
        return frozenset(names - self.supported_tables())

    def require_modeled(
        self,
        available: Iterable[str | Path],
        *,
        cycle: str | Path | None = None,
        diagnostic: bool = False,
    ) -> frozenset[str]:
        """Reject unknown operational tables unless diagnostic mode is explicit."""

        unmodeled = self.unmodeled_tables(available)
        if unmodeled and not diagnostic:
            instructions = (
                "Update openNASR/schemas.py, openNASR/registry.py, the relevant "
                "domain module and record class, fixtures, the coverage manifest, "
                "and PLAN.md."
            )
            raise SchemaMismatchError(
                f"Unmodeled NASR tables in {cycle or 'unknown cycle'}: "
                f"{sorted(unmodeled)}. {instructions}",
                cycle=str(cycle) if cycle is not None else None,
                unmodeled_tables=tuple(sorted(unmodeled)),
                instructions=instructions,
            )
        return unmodeled


__all__ = [
    "AIRPORT_LINKED_TABLES",
    "AIRPORT_SITE_KEY",
    "AIRWAY_KEY",
    "AIRWAY_SEGMENT_KEY",
    "AIRWAY_TABLES",
    "HOLDING_PATTERN_KEY",
    "HOLDING_PATTERN_TABLES",
    "FREQUENCY_KEY",
    "IndexSpec",
    "RICH_RECORD_TYPES",
    "RelationshipSpec",
    "TableRegistry",
    "TableSpec",
    "TableVariantSpec",
]
