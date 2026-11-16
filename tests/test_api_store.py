"""The API's cycle store: fetching from a bucket, defaults and failure handling."""

from datetime import date

import pytest

from openNASR.cycles import CycleManager
from openNASR_api import CycleStore, CycleUnavailableError
from openNASR_archiver import publish_cycle
from openNASR_contract import LocalBucket

FIXTURE = "schema_only/nasr_2026_09"
CYCLE = "2026-09-03"


@pytest.fixture
def bucket(make_nasr_from_fixture, tmp_path):
    nasr, cache_root = make_nasr_from_fixture(FIXTURE)
    bucket = LocalBucket(tmp_path / "bucket")
    publish_cycle(
        CycleManager(cache_root),
        date.fromisoformat(nasr.effective_date),
        bucket,
        required_tables=(),
    )
    return bucket


def test_refresh_fetches_a_published_cycle_once(bucket, tmp_path):
    store = CycleStore(tmp_path / "api", bucket, today=lambda: date(2026, 9, 10))

    first = store.refresh()
    second = store.refresh()

    assert first.fetched == [CYCLE] and first.failed == {}
    assert second.fetched == []
    assert store.cycles() == [CYCLE]
    assert store.default_cycle() == CYCLE
    assert store.manifest(CYCLE).schema_id == "nasr_2026_09"
    assert store.describe()[0]["in_effect"] is True


def test_an_upcoming_cycle_is_available_but_not_the_default(bucket, tmp_path):
    store = CycleStore(tmp_path / "api", bucket, today=lambda: date(2026, 9, 2))
    store.refresh()

    assert store.cycles() == [CYCLE]
    assert store.describe()[0]["in_effect"] is False
    with pytest.raises(CycleUnavailableError, match="in effect"):
        store.default_cycle()
    store.resolver(CYCLE)  # can still be asked for by date


def test_a_corrupted_download_keeps_the_previous_good_cycle(bucket, tmp_path):
    store = CycleStore(tmp_path / "api", bucket, today=lambda: date(2026, 9, 10))
    store.refresh()
    good = (tmp_path / "api" / "cycles" / CYCLE / "nasr.duckdb").read_bytes()

    # A newer cycle is published but its database is damaged in the bucket.
    from openNASR_contract import list_builds

    manifest = list_builds(bucket)[0]
    import dataclasses

    from openNASR_contract import ArtifactRef, build_keys

    keys = build_keys("2026-10-01", manifest.zip.sha256, manifest.builder)
    newer = dataclasses.replace(
        manifest,
        effective_date="2026-10-01",
        zip=ArtifactRef(keys.zip, manifest.zip.sha256, manifest.zip.size),
        duckdb=ArtifactRef(keys.duckdb, manifest.duckdb.sha256, manifest.duckdb.size),
        sidecar=ArtifactRef(
            keys.sidecar, manifest.sidecar.sha256, manifest.sidecar.size
        ),
    )
    bucket.put_bytes(keys.manifest, newer.to_json().encode())
    bucket.put_bytes(keys.duckdb, b"damaged")
    bucket.put_bytes(keys.sidecar, b"{}")

    report = store.refresh()

    assert "2026-10-01" in report.failed
    assert store.cycles() == [CYCLE]
    assert (tmp_path / "api" / "cycles" / CYCLE / "nasr.duckdb").read_bytes() == good


def test_the_store_serves_from_disk_without_a_bucket(bucket, tmp_path):
    CycleStore(tmp_path / "api", bucket).refresh()

    offline = CycleStore(tmp_path / "api", None, today=lambda: date(2026, 9, 10))

    assert offline.refresh().fetched == []
    assert offline.resolver()[0] == CYCLE


def test_only_the_loaded_cycles_stay_in_memory(bucket, tmp_path):
    store = CycleStore(tmp_path / "api", bucket, max_loaded=1)
    store.refresh()
    first = store.resolver(CYCLE)[1]

    assert store.resolver(CYCLE)[1] is first  # cached
