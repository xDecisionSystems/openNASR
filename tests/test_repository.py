from openNASR.repository import TableRepository, discover_tables, normalize_table_name


def test_table_discovery_uses_filenames_without_reading_csv_contents(tmp_path):
    (tmp_path / "APT_BASE.csv").write_text("not valid CSV", encoding="utf-8")
    (tmp_path / "nav_base.csv").write_text("also not valid CSV", encoding="utf-8")

    assert discover_tables(tmp_path) == ("APT_BASE", "NAV_BASE")
    assert TableRepository(tmp_path).available_tables == ("APT_BASE", "NAV_BASE")


def test_requested_table_names_are_normalized_to_uppercase():
    assert normalize_table_name(" apt_base ") == "APT_BASE"


def test_loaded_dataframes_are_cached_per_repository_instance(tmp_path):
    (tmp_path / "APT_BASE.csv").write_text("ARPT_ID\nBWI\n", encoding="utf-8")
    repository = TableRepository(tmp_path)

    first = repository.load("apt_base")
    second = repository.load("APT_BASE")

    assert repository.is_loaded("APT_BASE")
    assert first is second
    assert repository["APT_BASE"] is first
