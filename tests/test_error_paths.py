"""Error handling for malformed and incomplete synthetic NASR cycles."""

from pathlib import Path
from shutil import copytree
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from openNASR import Airport
from openNASR.cycles import CycleManager
from openNASR.exceptions import SchemaMismatchError, TableNotFoundError
from openNASR.nasr import NASR


def test_missing_airport_identifier_raises_schema_mismatch(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("malformed")

    with pytest.raises(SchemaMismatchError) as error:
        nasr["APT_BASE"]

    assert error.value.table == "APT_BASE"
    assert error.value.missing_columns == ("ARPT_ID",)


def test_missing_optional_marker_table_leaves_markers_empty(make_nasr_from_fixture):
    nasr, _ = make_nasr_from_fixture("missing_table_cycle")

    airport = Airport("BWI", nasr)

    assert airport.ils.ids == ["10"]
    assert airport.mkr.ids == []


def test_get_falls_back_for_a_genuinely_missing_table_but_raises_on_drift(
    make_nasr_from_fixture,
):
    """``nasr.get(name, default)`` must distinguish "table not present at
    all" (falls back, per the optional-table pattern used throughout the
    domain modules) from "table present but fails validation" (still
    raises; a caller must not silently treat bad data as absent data)."""
    nasr, _ = make_nasr_from_fixture("malformed")

    assert nasr.get("DOES_NOT_EXIST", "fallback") == "fallback"
    with pytest.raises(SchemaMismatchError):
        nasr.get("APT_BASE", "fallback")


def test_missing_required_base_table_raises_table_not_found(tmp_path):
    """A required base table (APT_BASE) that is entirely absent from the
    cycle -- unlike an optional table such as ILS_MKR -- must raise
    TableNotFoundError, both from direct access and through a domain lookup
    that depends on it."""
    source = (
        Path(__file__).parent
        / "fixtures"
        / "core"
        / "pre_2026_09"
        / "CSV_Data"
        / "pre_2026_09"
    )
    cycle_dir = tmp_path / "cycle"
    copytree(source, cycle_dir)
    (cycle_dir / "APT_BASE.csv").unlink()

    archive = tmp_path / "28DaySubscription_Effective_2026-08-06.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as output:
        for path in sorted(cycle_dir.glob("*.csv")):
            output.write(path, Path("CSV_Data") / "pre_2026_09" / path.name)

    cache_root = tmp_path / "cache"
    manager = CycleManager(cache_root)
    manager.import_archive(archive)

    nasr = NASR(cache_dir=cache_root)

    with pytest.raises(TableNotFoundError, match="APT_BASE"):
        nasr["APT_BASE"]

    with pytest.raises(TableNotFoundError, match="APT_BASE"):
        nasr.airport("BWI")
