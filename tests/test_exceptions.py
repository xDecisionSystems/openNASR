"""Tests for the public exception hierarchy."""

import pytest

from openNASR.exceptions import (
    AmbiguousRecordError,
    CycleNotFoundError,
    OpenNASRError,
    RecordNotFoundError,
    TableNotFoundError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        CycleNotFoundError,
        TableNotFoundError,
    ],
)
def test_public_exception_types_share_open_nasr_base(error_type):
    error = error_type("lookup failed")

    assert isinstance(error, OpenNASRError)
    assert str(error) == "lookup failed"


def test_record_not_found_error_preserves_lookup_context():
    error = RecordNotFoundError(
        entity_type="Navaid",
        identifier="DUP",
        filters={"state": "FL", "nav_type": "VOR"},
    )

    assert isinstance(error, OpenNASRError)
    assert error.entity_type == "Navaid"
    assert error.identifier == "DUP"
    assert error.filters == {"state": "FL", "nav_type": "VOR"}
    assert "Navaid record 'DUP' was not found" in str(error)
    assert "state='FL'" in str(error)


def test_ambiguous_record_error_preserves_candidates_and_context():
    candidates = [{"NAV_ID": "DUP", "STATE": "FL"}, {"NAV_ID": "DUP", "STATE": "GA"}]
    error = AmbiguousRecordError(
        entity_type="Navaid",
        identifier="DUP",
        filters={"country": "US"},
        candidates=candidates,
    )

    assert isinstance(error, OpenNASRError)
    assert error.entity_type == "Navaid"
    assert error.identifier == "DUP"
    assert error.filters == {"country": "US"}
    assert error.candidates == tuple(candidates)
    assert "matched 2 records" in str(error)
