"""Supported-schema parsing, identification, validation, and registry coverage."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest

from openNASR.exceptions import SchemaMismatchError
from openNASR.nasr import NASR
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
    FACILITY_TABLES,
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
        # A schema-description file declares each column using its own
        # spelling, which is `faa_declared_name` when the data file's actual
        # header casing differs (e.g. CDR's `RCode` data column is declared
        # `RCODE`), and `name` otherwise.
        assert [column.name for column in actual.columns] == [
            column.get("faa_declared_name") or column["name"]
            for column in expected["columns"]
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
def test_identify_schema_matches_a_column_whose_declared_casing_differs_from_data(
    schema_id,
):
    """A schema-description file may declare a column differently than the
    data file actually spells it (e.g. CDR declares ``RCODE`` but the CSV
    data header is ``RCode``). ``identify_schema`` must recognize the cycle
    from the schema-description file's own (declared) spelling, not the
    data-file spelling recorded on ``ColumnSchema.name``.
    """
    catalog = SchemaCatalog()
    cdr_column = next(
        column
        for column in catalog.table("CDR", schema_id).columns
        if column.name == "RCode"
    )
    assert cdr_column.faa_declared_name == "RCODE"
    assert cdr_column.declared_name == "RCODE"

    # The checked-in fixture schema-description file already declares this
    # column with FAA's real casing; identify_schema must match it.
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
                | FACILITY_TABLES
                | {"COM", "FRQ", "FIX_BASE", "NAV_BASE"}
            )
            if table_name not in rich_metadata_tables:
                assert variant.identity_key is None
                assert variant.relationships == ()


def _synthetic_value(column) -> str:
    """A minimal schema-conformant value: empty for nullable, a short
    placeholder otherwise. Not a semantically meaningful FAA value — only
    structurally valid enough to load and construct a record."""

    if column.nullable:
        return ""
    if column.faa_type == "NUMBER":
        return "0"
    return "X"


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_every_operational_table_loads_and_constructs_at_least_one_record(
    schema_id, tmp_path
):
    """Every table registered for this schema can be loaded independently
    through TableRepository, and its TableSpec.record_type can construct a
    record from the loaded row without error."""

    from openNASR.tables import TableRepository

    catalog = SchemaCatalog()
    registry = TableRegistry(catalog=catalog)

    for table_name in sorted(registry.supported_tables()):
        variant = registry.spec(table_name, schema_id)
        schema = catalog.table(table_name, schema_id)
        row = {column.name: _synthetic_value(column) for column in schema.columns}

        cycle_dir = tmp_path / table_name
        cycle_dir.mkdir()
        frame = pd.DataFrame([row])
        frame.to_csv(cycle_dir / f"{table_name}.csv", index=False)

        loaded = TableRepository(cycle_dir).load(table_name)
        assert len(loaded) == 1

        record_type = registry.table(table_name).record_type
        record = record_type(loaded.iloc[0].to_dict())
        assert record.as_dict()[schema.columns[0].name] == row[schema.columns[0].name]
        assert variant.required_columns <= set(row)


def test_raw_table_loading_preserves_leading_zero_identifiers_and_empty_nulls(
    tmp_path,
):
    """The raw layer must read every column as text -- leading-zero
    identifiers like SITE_NO must not be coerced to a number (which would
    drop the leading zero), and an empty identifier field must remain an
    empty string, never become NaN or change the column's dtype."""

    from openNASR.tables import TableRepository

    cycle_dir = tmp_path / "cycle"
    cycle_dir.mkdir()
    frame = pd.DataFrame(
        [
            {"SITE_NO": "00128.", "NAV_ID": "ABC"},
            {"SITE_NO": "", "NAV_ID": "DEF"},
        ]
    )
    frame.to_csv(cycle_dir / "NAV_BASE.csv", index=False)

    read_options = {"dtype": str, "keep_default_na": False, "na_filter": False}
    loaded = TableRepository(cycle_dir, read_options=read_options).load("NAV_BASE")

    assert loaded.loc[0, "SITE_NO"] == "00128."
    assert isinstance(loaded.loc[0, "SITE_NO"], str)
    assert loaded.loc[1, "SITE_NO"] == ""
    assert isinstance(loaded.loc[1, "SITE_NO"], str)
    assert loaded.loc[1, "NAV_ID"] == "DEF"


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


def test_coverage_checks_fail_when_a_known_table_is_removed_from_the_registry():
    """A meta-test for the coverage machinery itself: if a real, currently
    registered table's TableSpec were accidentally deleted, the coverage
    assertions this suite relies on (registry.supported_tables() containing
    every manifest table, and require_modeled() accepting every real
    filename) must actually fail -- proving those assertions are load-bearing
    and not vacuously true. Uses the real production registry's own specs
    with one entry removed, not a from-scratch synthetic registry."""
    real_registry = TableRegistry()
    all_table_names = real_registry.supported_tables()
    assert "APT_BASE" in all_table_names

    real_specs = [real_registry.table(name) for name in sorted(all_table_names)]
    specs_missing_apt_base = [spec for spec in real_specs if spec.name != "APT_BASE"]
    reduced_registry = TableRegistry(specs=specs_missing_apt_base)

    assert reduced_registry.supported_tables() == all_table_names - {"APT_BASE"}
    assert "APT_BASE" not in reduced_registry.supported_tables()

    other_real_tables = sorted(all_table_names - {"APT_BASE"})[:5]
    with pytest.raises(SchemaMismatchError, match="APT_BASE"):
        reduced_registry.require_modeled(["APT_BASE", *other_real_tables])


def test_normal_loading_rejects_unknown_table_but_diagnostic_mode_loads_it(tmp_path):
    source = _schema_csv_dir("pre_2026_09")
    cache_root = tmp_path / "cache"
    archives_dir = cache_root / "archives"
    archives_dir.mkdir(parents=True)
    archive = archives_dir / "28DaySubscription_Effective_2026-08-06.zip"

    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
        for path in sorted(source.glob("*.csv")):
            output.write(path, Path("CSV_Data") / "fixture" / path.name)
        output.writestr("CSV_Data/fixture/FUTURE.csv", "FUTURE_ID\n001\n")

    with pytest.raises(SchemaMismatchError) as error:
        NASR(cache_dir=cache_root)
    assert error.value.unmodeled_tables == ("FUTURE",)

    diagnostic = NASR(cache_dir=cache_root, diagnostic=True)
    assert diagnostic["FUTURE"].iloc[0]["FUTURE_ID"] == "001"
