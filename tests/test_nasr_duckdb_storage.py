"""``NASR`` serves every cycle from a DuckDB artifact."""

from __future__ import annotations

import json
from shutil import rmtree

import pytest

pytest.importorskip("duckdb")

from openNASR.cycles import CycleManager
from openNASR.duckdb_builder import duckdb_metadata_path
from openNASR.duckdb_metadata import DuckDbMetadataDateMismatchError
from openNASR.exceptions import ConfigurationError, CycleNotFoundError
from openNASR.nasr import NASR


def _keep_only_the_artifact(manager, cache_root):
    rmtree(manager.archives_dir)
    for child in (cache_root / "cycles" / "2026-08-06").iterdir():
        if not child.name.startswith("nasr.duckdb"):
            rmtree(child) if child.is_dir() else child.unlink()


def test_a_mismatched_artifact_is_rebuilt_when_sources_exist(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    manager = CycleManager(cache_root)
    result = manager.build_duckdb("2026-08-06")
    sidecar = duckdb_metadata_path(result.database_path)
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["effective_date"] = "2026-09-03"
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")

    assert NASR(cycle="2026-08-06", cache_dir=cache_root).effective_date == "2026-08-06"


def test_first_use_builds_the_artifact_and_reports_duckdb(make_nasr_from_fixture):
    nasr, cache_root = make_nasr_from_fixture("core/pre_2026_09")

    assert nasr.storage == "duckdb"
    assert nasr.effective_date == "2026-08-06"
    assert nasr.table("APT_BASE")["ARPT_ID"].tolist() == ["BWI", "DCA"]
    assert CycleManager(cache_root).duckdb_path("2026-08-06").is_file()


def test_artifact_alone_is_enough_to_serve_a_cycle(make_nasr_from_fixture):
    """An API host holds only nasr.duckdb and its sidecar, never CSVs or zips."""

    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    manager = CycleManager(cache_root)
    manager.build_duckdb("2026-08-06")
    _keep_only_the_artifact(manager, cache_root)

    nasr = NASR(cycle="2026-08-06", cache_dir=cache_root)

    assert nasr.table("APT_BASE")["ARPT_ID"].tolist() == ["BWI", "DCA"]
    assert nasr.schema_fingerprint


def test_missing_cycle_without_any_source_is_a_typed_error(tmp_path):
    with pytest.raises(CycleNotFoundError):
        NASR(cycle="2026-08-06", cache_dir=tmp_path)


def test_rejects_metadata_for_another_cycle(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    manager = CycleManager(cache_root)
    result = manager.build_duckdb("2026-08-06")
    sidecar = duckdb_metadata_path(result.database_path)
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["effective_date"] = "2026-09-03"
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    _keep_only_the_artifact(manager, cache_root)

    with pytest.raises(DuckDbMetadataDateMismatchError):
        NASR(cycle="2026-08-06", cache_dir=cache_root)


def test_csv_storage_was_removed_with_a_migration_message():
    with pytest.raises(ConfigurationError, match="removed in openNASR 2.0"):
        NASR(storage="csv")


@pytest.mark.parametrize("storage", ("auto", "CSV", "sqlite"))
def test_nasr_rejects_unrecognized_storage_backend(storage):
    with pytest.raises(ConfigurationError, match="storage must be"):
        NASR(storage=storage)


def test_built_artifact_records_the_schemas_procedure_order(make_nasr_from_fixture):
    nasr, cache_root = make_nasr_from_fixture("schema_only/nasr_2026_09")

    sidecar = duckdb_metadata_path(
        CycleManager(cache_root).duckdb_path(nasr.effective_date)
    )
    assert json.loads(sidecar.read_text("utf-8"))["procedure_order"] == "flight_order"
    assert nasr.procedure_order == "flight_order"
