from openNASR.repository import TableRepository, discover_tables, normalize_table_name
from collections.abc import Mapping
import pytest
from pandas.errors import ParserError

from openNASR.exceptions import TableNotFoundError


def test_table_discovery_uses_filenames_without_reading_csv_contents(tmp_path):
    (tmp_path / "APT_BASE.csv").write_text("not valid CSV", encoding="utf-8")
    (tmp_path / "nav_base.csv").write_text("also not valid CSV", encoding="utf-8")

    assert discover_tables(tmp_path) == ("APT_BASE", "NAV_BASE")
    assert TableRepository(tmp_path).available_tables == ("APT_BASE", "NAV_BASE")


def test_requested_table_names_are_normalized_to_uppercase():
    assert normalize_table_name(" apt_base ") == "APT_BASE"


def test_missing_table_raises_a_clear_typed_error(tmp_path):
    with pytest.raises(TableNotFoundError, match="MISSING"):
        TableRepository(tmp_path).load("missing")


def test_table_loading_retries_only_for_text_encoding_errors(tmp_path):
    (tmp_path / "APT_BASE.csv").write_bytes(b"ARPT_ID,NAME\nBWI,Montr\xe9al\n")

    table = TableRepository(tmp_path).load("APT_BASE")

    assert table.loc[0, "NAME"] == "Montréal"


def test_parser_errors_are_not_retried_or_hidden(monkeypatch, tmp_path):
    path = tmp_path / "APT_BASE.csv"
    path.write_text("ARPT_ID\nBWI\n", encoding="utf-8")

    def malformed_csv(*_args, **_kwargs):
        raise ParserError("malformed row")

    monkeypatch.setattr("openNASR.repository.read_csv", malformed_csv)
    with pytest.raises(ParserError, match="malformed row"):
        TableRepository(tmp_path).load("APT_BASE")


def test_loaded_dataframes_are_cached_per_repository_instance(tmp_path):
    (tmp_path / "APT_BASE.csv").write_text("ARPT_ID\nBWI\n", encoding="utf-8")
    repository = TableRepository(tmp_path)

    first = repository.load("apt_base")
    second = repository.load("APT_BASE")

    assert repository.is_loaded("APT_BASE")
    assert first is second
    assert repository["APT_BASE"] is first
    assert repository.table("APT_BASE") is first
    isolated = repository.table("APT_BASE", copy=True)
    isolated.loc[0, "ARPT_ID"] = "MUTATED"
    assert first.loc[0, "ARPT_ID"] == "BWI"
    assert isinstance(repository, Mapping)
    assert list(repository) == ["APT_BASE"]
