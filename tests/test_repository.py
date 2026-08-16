from openNASR.repository import TableRepository, discover_tables


def test_table_discovery_uses_filenames_without_reading_csv_contents(tmp_path):
    (tmp_path / "APT_BASE.csv").write_text("not valid CSV", encoding="utf-8")
    (tmp_path / "nav_base.csv").write_text("also not valid CSV", encoding="utf-8")

    assert discover_tables(tmp_path) == ("APT_BASE", "NAV_BASE")
    assert TableRepository(tmp_path).available_tables == ("APT_BASE", "NAV_BASE")
