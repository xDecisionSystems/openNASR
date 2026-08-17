"""Unit tests for NASR cycle-date helpers."""

import pytest

from openNASR.cycles import CycleManager
from openNASR.nasr import NASR
from openNASR.nasr import timestampToYearDecimal


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        ("2024-03-01", 2024 + 60 / 366),
        ("2025-07-02", 2025 + 182 / 365),
    ],
)
def test_timestamp_to_year_decimal_handles_leap_and_common_years(timestamp, expected):
    assert timestampToYearDecimal(timestamp) == pytest.approx(expected)


def test_update_compatibility_argument_warns_without_downloading(
    fixture_cycle_archive, tmp_path
):
    cache_root = tmp_path / "cache"
    CycleManager(cache_root).import_archive(fixture_cycle_archive)

    with pytest.warns(DeprecationWarning, match="does not download data"):
        NASR(update=True, cache_dir=cache_root)
