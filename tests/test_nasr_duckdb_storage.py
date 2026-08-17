"""Public ``NASR(storage=...)`` lifecycle coverage."""

from __future__ import annotations

import json

import pytest

from openNASR.cycles import CycleManager
from openNASR.duckdb_builder import DuckDbBuildError, duckdb_metadata_path
from openNASR.duckdb_metadata import DuckDbMetadataDateMismatchError
from openNASR.exceptions import ConfigurationError
from openNASR.nasr import NASR


def test_csv_is_the_default_and_duckdb_uses_the_same_exact_cycle(
    make_nasr_from_fixture,
):
    csv, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    CycleManager(cache_root).build_duckdb("2026-08-06")

    duckdb = NASR(
        cycle="2026-08-06",
        cache_dir=cache_root,
        storage="duckdb",
    )

    assert csv.storage == "csv"
    assert duckdb.storage == "duckdb"
    assert csv._NASR__useDate == duckdb._NASR__useDate == "2026-08-06"
    assert duckdb.table("APT_BASE")["ARPT_ID"].tolist() == ["BWI", "DCA"]


def test_duckdb_requires_a_prebuilt_database_for_the_exact_cycle(
    make_nasr_from_fixture,
):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")

    with pytest.raises(DuckDbBuildError, match="no completed artifact"):
        NASR(cycle="2026-08-06", cache_dir=cache_root, storage="duckdb")


def test_duckdb_rejects_metadata_for_another_cycle(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    manager = CycleManager(cache_root)
    result = manager.build_duckdb("2026-08-06")
    sidecar = duckdb_metadata_path(result.database_path)
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["effective_date"] = "2026-09-03"
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(DuckDbMetadataDateMismatchError):
        NASR(cycle="2026-08-06", cache_dir=cache_root, storage="duckdb")


@pytest.mark.parametrize("storage", ("auto", "CSV", "sqlite"))
def test_nasr_rejects_unrecognized_storage_backend(storage):
    with pytest.raises(ConfigurationError, match="storage must be"):
        NASR(storage=storage)
