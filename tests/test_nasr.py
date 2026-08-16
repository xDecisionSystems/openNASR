"""Unit tests for NASR cycle-date helpers."""

import pytest

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
