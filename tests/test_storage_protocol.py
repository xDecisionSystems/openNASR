from collections.abc import Mapping

from pandas import DataFrame

from openNASR.storage import TableStore
from openNASR.tables import TableRepository


def test_csv_repository_exposes_the_table_store_contract(tmp_path):
    (tmp_path / "APT_BASE.csv").write_text("ARPT_ID\nBWI\n", encoding="utf-8")

    repository: TableStore = TableRepository(tmp_path)

    assert isinstance(repository, Mapping)
    assert repository.available_tables == ("APT_BASE",)
    assert isinstance(repository.load("APT_BASE"), DataFrame)
    assert repository.table("APT_BASE") is repository["APT_BASE"]
    assert repository.index("APT_BASE", "ARPT_ID") == {"BWI": (0,)}
    assert repository.normalized_index("APT_BASE", "ARPT_ID") == {"BWI": (0,)}
