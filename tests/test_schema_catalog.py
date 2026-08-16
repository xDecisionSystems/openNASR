"""Supported-schema parsing, identification, validation, and registry coverage."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from openNASR.exceptions import SchemaMismatchError
from openNASR.nasr import NASR
import openNASR.nasr as nasr_module
from openNASR.records import FaaRecord
from openNASR.registry import (
    AIRPORT_LINKED_TABLES,
    AIRPORT_SITE_KEY,
    AIRWAY_FIX_KEY,
    AIRWAY_KEY,
    AIRWAY_NAVAID_KEY,
    AIRWAY_SEGMENT_KEY,
    AIRWAY_TABLES,
    FIX_KEY,
    HOLDING_PATTERN_TABLES,
    IndexSpec,
    NAVAID_KEY,
    PROCEDURE_ROUTE_TABLES,
    RelationshipSpec,
    TableRegistry,
    TableSpec,
)
from openNASR.schemas import (
    SchemaCatalog,
    parse_schema_description,
    parse_schema_description_tables,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures"
SCHEMA_IDS = ("pre_2026_09", "nasr_2026_09")


def _manifest(schema_id: str) -> dict[str, object]:
    path = FIXTURE_ROOT / "manifests" / f"{schema_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_csv_dir(schema_id: str) -> Path:
    return FIXTURE_ROOT / "schema_only" / schema_id / "CSV_Data" / schema_id


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_every_schema_description_file_parses(schema_id):
    manifest = _manifest(schema_id)
    parsed_tables = {}

    for filename in manifest["schema_description_files"]:
        path = _schema_csv_dir(schema_id) / filename
        tables = parse_schema_description_tables(path)
        assert tables
        parsed_tables.update(tables)

    assert set(parsed_tables) == set(manifest["tables"])
    for table_name, expected in manifest["tables"].items():
        actual = parsed_tables[table_name]
        assert actual.columns
        assert [column.name for column in actual.columns] == [
            column["name"] for column in expected["columns"]
        ]


def test_single_table_parser_returns_column_rows():
    path = _schema_csv_dir("pre_2026_09") / "APT_CSV_DATA_STRUCTURE.csv"

    columns = parse_schema_description(path, "APT_BASE")

    assert columns[0].name == "EFF_DATE"
    assert columns[0].faa_type == "VARCHAR"
    assert columns[0].max_length == "10"
    assert columns[0].nullable is False


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_catalog_identifies_schema_by_metadata_fingerprint(schema_id):
    catalog = SchemaCatalog()

    assert catalog.identify_schema(_schema_csv_dir(schema_id)) == schema_id


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_catalog_contains_every_operational_table(schema_id):
    catalog = SchemaCatalog()
    manifest = _manifest(schema_id)

    for table_name in manifest["tables"]:
        table = catalog.table(table_name, schema_id)
        assert table.name == table_name
        assert table.columns


def test_validation_reports_structural_and_declared_type_drift():
    catalog = SchemaCatalog()
    schema = catalog.table("APT_BASE", "pre_2026_09")
    columns = [column.name for column in schema.columns]
    frame = pd.DataFrame(columns=[*columns[1:], "FUTURE_COLUMN"])

    report = catalog.validate(
        "APT_BASE",
        frame,
        "pre_2026_09",
        declared_types={"ARPT_ID": "NUMBER"},
    )

    assert report.missing_required_columns == ("EFF_DATE",)
    assert report.unexpected_columns == ("FUTURE_COLUMN",)
    assert report.type_differences == ("ARPT_ID: expected VARCHAR, got NUMBER",)
    with pytest.raises(SchemaMismatchError) as error:
        report.require_compatible(cycle="fixture-cycle")
    assert error.value.table == "APT_BASE"
    assert "registry.py" in error.value.instructions


def test_registry_covers_every_operational_table_and_schema_variant():
    catalog = SchemaCatalog()
    registry = TableRegistry(catalog=catalog)
    expected = set().union(
        *(_manifest(schema_id)["tables"] for schema_id in SCHEMA_IDS)
    )

    assert registry.supported_tables() == expected
    for table_name in expected:
        table = registry.table(table_name)
        assert issubclass(table.record_type, FaaRecord)
        for variant in table.variants:
            declared = {
                column.name
                for column in catalog.table(table_name, variant.schema_id).columns
            }
            assert variant.required_columns <= declared
            rich_metadata_tables = (
                AIRPORT_LINKED_TABLES
                | AIRWAY_TABLES
                | HOLDING_PATTERN_TABLES
                | PROCEDURE_ROUTE_TABLES
                | {"COM", "FRQ", "FIX_BASE", "NAV_BASE"}
            )
            if table_name not in rich_metadata_tables:
                assert variant.identity_key is None
                assert variant.relationships == ()


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
@pytest.mark.parametrize("table_name", sorted(AIRPORT_LINKED_TABLES))
def test_airport_linked_registry_keys_are_verified(table_name, schema_id):
    catalog = SchemaCatalog()
    variant = TableRegistry(catalog=catalog).spec(table_name, schema_id)

    assert variant.identity_key == AIRPORT_SITE_KEY
    assert variant.indexes == (
        IndexSpec("site", AIRPORT_SITE_KEY, unique=True),
        IndexSpec("airport_id", ("ARPT_ID",), unique=False),
    )
    assert variant.relationships == (
        RelationshipSpec("airport", "APT_BASE", AIRPORT_SITE_KEY, AIRPORT_SITE_KEY),
    )

    local_columns = {
        column.name for column in catalog.table(table_name, schema_id).columns
    }
    airport_columns = {
        column.name for column in catalog.table("APT_BASE", schema_id).columns
    }
    assert set(AIRPORT_SITE_KEY) <= local_columns
    assert set(AIRPORT_SITE_KEY) <= airport_columns


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_representative_rows_require_the_full_airport_site_key(schema_id):
    fixture_path = FIXTURE_ROOT / "relationships" / "airport_linked.json"
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))[schema_id]
    airports_by_site = {
        tuple(row[column] for column in AIRPORT_SITE_KEY): row
        for row in rows["APT_BASE"]
    }

    assert len({row["ARPT_ID"] for row in rows["APT_BASE"]}) == 1
    for table_name in AIRPORT_LINKED_TABLES:
        identities = []
        for row in rows[table_name]:
            site_key = tuple(row[column] for column in AIRPORT_SITE_KEY)
            identities.append(site_key)
            assert airports_by_site[site_key]["ARPT_ID"] == row["ARPT_ID"]
        assert len(identities) == len(set(identities))


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_airway_registry_keys_and_ordering_are_verified(schema_id):
    catalog = SchemaCatalog()
    registry = TableRegistry(catalog=catalog)
    base = registry.spec("AWY_BASE", schema_id)
    segments = registry.spec("AWY_SEG_ALT", schema_id)

    assert base.identity_key == AIRWAY_KEY
    assert base.indexes == (IndexSpec("airway", AIRWAY_KEY, unique=True),)
    assert base.relationships == (
        RelationshipSpec("segments", "AWY_SEG_ALT", AIRWAY_KEY, AIRWAY_KEY),
    )
    assert segments.identity_key == AIRWAY_SEGMENT_KEY
    assert segments.indexes == (
        IndexSpec("segment", AIRWAY_SEGMENT_KEY, unique=True),
        IndexSpec("airway", AIRWAY_KEY, unique=False),
    )
    assert segments.order_by == ("POINT_SEQ",)
    assert segments.relationships == (
        RelationshipSpec("airway", "AWY_BASE", AIRWAY_KEY, AIRWAY_KEY),
        RelationshipSpec("fix", "FIX_BASE", AIRWAY_FIX_KEY, FIX_KEY),
        RelationshipSpec("navaid", "NAV_BASE", AIRWAY_NAVAID_KEY, NAVAID_KEY),
    )

    for table_name, variant in (("AWY_BASE", base), ("AWY_SEG_ALT", segments)):
        declared = {
            column.name for column in catalog.table(table_name, schema_id).columns
        }
        assert set(variant.identity_key or ()) <= declared
        assert set(variant.order_by) <= declared
        for relationship in variant.relationships:
            target_columns = {
                column.name
                for column in catalog.table(
                    relationship.target_table, schema_id
                ).columns
            }
            assert set(relationship.local_columns) <= declared
            assert set(relationship.target_columns) <= target_columns


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_representative_airway_rows_require_full_key_and_sequence_order(schema_id):
    fixture_path = FIXTURE_ROOT / "relationships" / "airways.json"
    rows = json.loads(fixture_path.read_text(encoding="utf-8"))[schema_id]
    base_keys = {
        tuple(row[column] for column in AIRWAY_KEY) for row in rows["AWY_BASE"]
    }

    assert len({row["AWY_ID"] for row in rows["AWY_BASE"]}) == 1
    for segment in rows["AWY_SEG_ALT"]:
        assert tuple(segment[column] for column in AIRWAY_KEY) in base_keys

    selected = [
        segment
        for segment in rows["AWY_SEG_ALT"]
        if tuple(segment[column] for column in AIRWAY_KEY) == ("Y", "D", "1")
    ]
    ordered = sorted(selected, key=lambda row: int(row["POINT_SEQ"]))
    assert [row["FROM_POINT"] for row in ordered] == ["ALPHA", "BRAVO"]


def test_test_local_registry_reports_and_rejects_unmodeled_tables():
    registry = TableRegistry(specs=[TableSpec("APT_BASE", FaaRecord, ())])

    assert registry.unmodeled_tables(["APT_BASE.csv", "FUTURE.csv"]) == {"FUTURE"}
    assert registry.require_modeled(["APT_BASE", "FUTURE"], diagnostic=True) == {
        "FUTURE"
    }
    with pytest.raises(SchemaMismatchError, match="FUTURE"):
        registry.require_modeled(["APT_BASE", "FUTURE"])


def test_normal_loading_rejects_unknown_table_but_diagnostic_mode_loads_it(
    monkeypatch, tmp_path
):
    source = _schema_csv_dir("pre_2026_09")
    cache_root = tmp_path / "cache"
    archive_dir = cache_root / "data" / "zip"
    archive_dir.mkdir(parents=True)
    archive = archive_dir / "28DaySubscription_Effective_2026-08-06.zip"

    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
        for path in sorted(source.glob("*.csv")):
            output.write(path, Path("CSV_Data") / "fixture" / path.name)
        output.writestr("CSV_Data/fixture/FUTURE.csv", "FUTURE_ID\n001\n")

    monkeypatch.setattr(nasr_module, "__file__", str(cache_root / "nasr.py"))
    with pytest.raises(SchemaMismatchError) as error:
        NASR()
    assert error.value.unmodeled_tables == ("FUTURE",)

    diagnostic = NASR(diagnostic=True)
    assert diagnostic["FUTURE"].iloc[0]["FUTURE_ID"] == "001"
