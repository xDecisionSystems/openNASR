"""Public repository parity checks for CSV and DuckDB cycle storage."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
import math

import pytest

pytest.importorskip("duckdb")

from openNASR.cycles import CycleManager
from openNASR.exceptions import TableNotFoundError
from openNASR.nasr import NASR
from openNASR.records import FaaRecord


FIXTURE_DATES = {
    "core/pre_2026_09": "2026-08-06",
    "schema_only/nasr_2026_09": "2026-09-03",
}


def _observable(value):
    """Convert a public repository result to a stable, value-only shape.

    Repository results intentionally contain rich wrappers around ``FaaRecord``
    instances.  This helper follows their public attributes and raw mappings,
    while avoiding private caches and implementation-specific object identity.
    """

    if isinstance(value, FaaRecord):
        return {str(key): _observable(item) for key, item in value.as_dict().items()}
    if isinstance(value, Mapping):
        return {str(key): _observable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_observable(item) for item in value)
    if isinstance(value, float) and math.isnan(value):
        # The compact legacy fixture has no schema catalog, so CSV mode lets
        # pandas infer blank fields as NaN while the lossless DuckDB path keeps
        # them as empty source strings.  Both represent the same FAA value.
        return ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _observable(str(value))
    if isinstance(value, str):
        # In a no-schema CSV fixture pandas may infer a decimal coordinate as
        # ``39.0`` while source-text ingestion retains ``39.0000``.  Compare
        # decimal spellings numerically, but leave integer-like identifiers
        # (including leading zeroes) untouched.
        if "." in value:
            try:
                return format(Decimal(value), "f").rstrip("0").rstrip(".")
            except InvalidOperation:
                pass
        return value
    if isinstance(value, (bool, type(None))):
        return value
    attributes = getattr(value, "__dict__", None)
    if attributes is not None:
        return {
            key: _observable(item)
            for key, item in sorted(attributes.items())
            if not key.startswith("_")
        }
    return repr(value)


@pytest.fixture(params=tuple(FIXTURE_DATES))
def storage_pair(make_nasr_from_fixture, request):
    """Build one temporary DuckDB artifact beside its CSV fixture archive."""

    fixture_name = str(request.param)
    csv_nasr, cache_root = make_nasr_from_fixture(fixture_name)
    cycle = FIXTURE_DATES[fixture_name]
    CycleManager(cache_root).build_duckdb(cycle)
    duckdb_nasr = NASR(cycle=cycle, cache_dir=cache_root, storage="duckdb")
    try:
        yield csv_nasr, duckdb_nasr
    finally:
        # NASR intentionally keeps its table store private.  Closing the
        # optional read-only connection here makes this fixture portable to
        # platforms that do not allow a temporary directory to be removed
        # while a database file is open.
        for nasr in (csv_nasr, duckdb_nasr):
            store = getattr(nasr, "_NASR__tables", None)
            close = getattr(store, "close", None)
            if close is not None:
                close()


def test_record_repositories_match_for_populated_and_schema_fixtures(storage_pair):
    """Compare airport, fix, and navaid values plus their typed errors."""

    csv, duckdb = storage_pair
    identifiers = (("airports", "BWI"), ("fixes", "AABEE"), ("navaids", "UNIQ"))
    for repository_name, identifier in identifiers:
        csv_repository = getattr(csv, repository_name)
        duckdb_repository = getattr(duckdb, repository_name)
        if repository_name == "airports" and "APT_BASE" not in csv:
            continue
        if repository_name == "fixes" and "FIX_BASE" not in csv:
            continue
        if repository_name == "navaids" and "NAV_BASE" not in csv:
            continue
        try:
            csv_result = csv_repository.get(identifier)
        except Exception as csv_error:
            with pytest.raises(type(csv_error)):
                duckdb_repository.get(identifier)
        else:
            assert _observable(duckdb_repository.get(identifier)) == _observable(
                csv_result
            )

        with pytest.raises(Exception) as csv_missing:
            csv_repository.get("__OPENNASR_MISSING__")
        with pytest.raises(type(csv_missing.value)):
            duckdb_repository.get("__OPENNASR_MISSING__")


def test_all_public_repository_find_results_match(storage_pair):
    """Every repository that exposes ``find`` behaves identically in both modes.

    The populated core fixture exercises the families for which it has rows;
    the schema-generation fixture covers all remaining table names and proves
    that an empty, valid table set follows the same path in both backends.
    """

    repository_names = (
        "class_airspaces",
        "artccs",
        "maas",
        "parachute_jump_areas",
        "atc_facilities",
        "radars",
        "weather_stations",
        "weather_locations",
        "flight_service_stations",
        "location_identifiers",
        "airways",
        "holding_patterns",
        "communication_outlets",
        "frequencies",
        "coded_departure_routes",
        "departures",
        "preferred_routes",
        "stars",
        "military_operations",
        "military_training_routes",
    )

    csv, duckdb = storage_pair
    for repository_name in repository_names:
        csv_repository = getattr(csv, repository_name)
        duckdb_repository = getattr(duckdb, repository_name)
        try:
            csv_result = csv_repository.find()
        except (KeyError, TableNotFoundError):
            # The compact core fixture deliberately omits unrelated FAA
            # tables. The same repository is covered by the schema fixture.
            continue
        assert _observable(duckdb_repository.find()) == _observable(csv_result)
