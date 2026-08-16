"""Compatibility behavior for the deferred legacy flight-plan module."""

import importlib

import pytest


def test_legacy_flightplan_module_fails_with_a_clear_error():
    with pytest.raises(NotImplementedError, match="flightplan is not implemented"):
        importlib.import_module("openNASR.flightplan")
