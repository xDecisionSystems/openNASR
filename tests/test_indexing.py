"""Regression coverage for shared normalized row-position indexes."""

from __future__ import annotations

import inspect

from numpy import ndarray
import pandas as pd

from openNASR.indexing import cached_normalized_column_index, normalized_index_rows


def _normalized(value: object) -> str:
    return str(value).strip().upper()


def test_cached_normalized_index_matches_scan_for_high_cardinality_rows():
    frame = pd.DataFrame(
        {
            "IDENTIFIER": [
                *(f" FIX{number:05d} " for number in range(10_000)),
                " FIX05000 ",
            ],
            "SOURCE_ORDER": range(10_001),
        }
    )
    cache = {}

    index = cached_normalized_column_index(cache, frame, "IDENTIFIER", _normalized)
    again = cached_normalized_column_index(cache, frame, "IDENTIFIER", _normalized)
    expected = frame[frame["IDENTIFIER"].map(_normalized).eq(_normalized("fix05000"))]

    actual = normalized_index_rows(frame, index, " fix05000 ", _normalized)

    assert again is index
    assert actual.equals(expected)
    assert actual["SOURCE_ORDER"].tolist() == [5000, 10000]
    assert isinstance(index["FIX05000"], ndarray)
    assert normalized_index_rows(frame, index, "missing", _normalized).empty


def test_cached_normalized_index_uses_positions_not_eager_group_dataframes():
    source = "".join(inspect.getsource(cached_normalized_column_index).split())

    assert ".groupby(normalized).indices" in source
    assert "dict(tuple(" not in source
