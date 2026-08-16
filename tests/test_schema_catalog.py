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
from openNASR.registry import TableRegistry, TableSpec
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
    assert report.type_differences == (
        "ARPT_ID: expected VARCHAR, got NUMBER",
    )
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
            assert variant.identity_key is None
            assert variant.relationships == ()


def test_test_local_registry_reports_and_rejects_unmodeled_tables():
    registry = TableRegistry(specs=[TableSpec("APT_BASE", FaaRecord, ())])

    assert registry.unmodeled_tables(["APT_BASE.csv", "FUTURE.csv"]) == {
        "FUTURE"
    }
    assert registry.require_modeled(
        ["APT_BASE", "FUTURE"], diagnostic=True
    ) == {"FUTURE"}
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
