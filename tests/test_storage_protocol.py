from collections.abc import Mapping

import pytest
from pandas import DataFrame

pytest.importorskip("duckdb")

from openNASR.duckdb_builder import build_duckdb
from openNASR.duckdb_tables import DuckDbTableRepository
from openNASR.storage import TableStore


def test_duckdb_repository_exposes_the_table_store_contract(tmp_path):
    source = tmp_path / "CSV_Data"
    source.mkdir()
    (source / "APT_BASE.csv").write_text("ARPT_ID\nBWI\n", encoding="utf-8")
    result = build_duckdb(source, tmp_path / "nasr.duckdb", "2026-08-06")

    repository: TableStore = DuckDbTableRepository(
        result.database_path, metadata=result.metadata
    )

    assert isinstance(repository, Mapping)
    assert repository.available_tables == ("APT_BASE",)
    assert isinstance(repository.load("APT_BASE"), DataFrame)
    assert repository.table("APT_BASE") is repository["APT_BASE"]
    assert repository.index("APT_BASE", "ARPT_ID") == {"BWI": (0,)}
    assert repository.normalized_index("APT_BASE", "ARPT_ID") == {"BWI": (0,)}
