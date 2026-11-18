"""The API's cycle store: fetching from a bucket, defaults and failure handling."""

from dataclasses import replace
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

import duckdb
import pytest

from openNASR.cycles import CycleManager
from openNASR_api import CycleStore, CycleUnavailableError
from openNASR_archiver import publish_cycle
from openNASR_contract import ArtifactRef, LocalBucket, build_keys, list_builds

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
        builder=1,
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
    manifest = list_builds(bucket)[0]

    keys = build_keys("2026-10-01", manifest.zip.sha256, manifest.builder)
    newer = replace(
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


def test_a_failed_replacement_keeps_the_same_cycle_readable(bucket, tmp_path):
    cache = tmp_path / "api"
    store = CycleStore(cache, bucket)
    assert store.refresh().fetched == [CYCLE]
    manifest = list_builds(bucket)[0]
    keys = build_keys(CYCLE, manifest.zip.sha256, manifest.builder + 1)
    database_hash = sha256(b"expected database").hexdigest()
    sidecar = bucket.get_bytes(manifest.sidecar.key).replace(
        manifest.duckdb.sha256.encode(), database_hash.encode()
    )
    newer = replace(
        manifest,
        builder=manifest.builder + 1,
        zip=replace(manifest.zip, key=keys.zip),
        duckdb=ArtifactRef(keys.duckdb, database_hash, len(b"expected database")),
        sidecar=ArtifactRef(keys.sidecar, sha256(sidecar).hexdigest(), len(sidecar)),
    )
    bucket.put_bytes(keys.manifest, newer.to_json().encode())
    bucket.put_bytes(keys.sidecar, sidecar)
    bucket.put_bytes(keys.duckdb, b"damaged")

    assert CYCLE in store.refresh().failed
    fresh_reader = CycleStore(cache)
    assert fresh_reader.manifest(CYCLE) == manifest
    assert fresh_reader.resolver(CYCLE)[0] == CYCLE


def test_publication_rolls_back_and_a_retry_reopens_the_database(
    bucket, tmp_path, monkeypatch
):
    store = CycleStore(tmp_path / "api", bucket)
    store.refresh()
    original = list_builds(bucket)[0]
    with store.lookup(CYCLE) as (_, query):
        assert not query("APT_BASE", fields=["ARPT_ID"]).rows

    database = tmp_path / "replacement.duckdb"
    database.write_bytes(bucket.get_bytes(original.duckdb.key))
    with duckdb.connect(database) as connection:
        # DuckDB can infer an integer type from the empty fixture column.
        connection.execute("INSERT INTO APT_BASE (ARPT_ID) VALUES ('123')")
    database_bytes = database.read_bytes()
    database_hash = sha256(database_bytes).hexdigest()
    metadata = json.loads(bucket.get_bytes(original.sidecar.key))
    metadata["database_sha256"] = database_hash
    metadata["tables"]["APT_BASE"] = 1
    sidecar = json.dumps(metadata).encode()
    keys = build_keys(CYCLE, original.zip.sha256, original.builder + 1)
    newer = replace(
        original,
        builder=original.builder + 1,
        zip=replace(original.zip, key=keys.zip),
        duckdb=ArtifactRef(keys.duckdb, database_hash, len(database_bytes)),
        sidecar=ArtifactRef(keys.sidecar, sha256(sidecar).hexdigest(), len(sidecar)),
        tables=metadata["tables"],
    )
    bucket.put_bytes(keys.manifest, newer.to_json().encode())
    bucket.put_bytes(keys.sidecar, sidecar)
    bucket.put_bytes(keys.duckdb, database_bytes)

    real_replace = Path.replace

    def fail_manifest_publication(self, target):
        if self.name == "manifest.json" and self.parent.name.startswith(".fetch-"):
            raise OSError("could not replace manifest")
        return real_replace(self, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_manifest_publication)
        assert CYCLE in store.refresh().failed
    assert store.manifest(CYCLE) == original
    with store.lookup(CYCLE) as (_, query):
        assert not query("APT_BASE", fields=["ARPT_ID"]).rows

    assert store.refresh().fetched == [CYCLE]
    assert store.manifest(CYCLE) == newer
    with store.lookup(CYCLE) as (_, query):
        assert query("APT_BASE", fields=["ARPT_ID"]).rows == ({"ARPT_ID": "123"},)


def test_a_bucket_error_preserves_the_cache_and_allows_retry(
    bucket, tmp_path, monkeypatch
):
    store = CycleStore(tmp_path / "api", bucket)
    store.refresh()

    def unavailable(_key):
        raise RuntimeError("temporarily unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(bucket, "get_bytes", unavailable)
        assert store.refresh().failed == {"bucket": "temporarily unavailable"}
        assert store.resolver(CYCLE)[0] == CYCLE

    assert store.refresh().failed == {}


@pytest.mark.parametrize("name", ["manifest.json", "nasr.duckdb", "nasr.duckdb.json"])
def test_refresh_repairs_an_incomplete_cache(bucket, tmp_path, name):
    cache = tmp_path / "api"
    store = CycleStore(cache, bucket)
    store.refresh()
    path = cache / "cycles" / CYCLE / name
    original = path.read_bytes()
    if name == "manifest.json":
        path.write_text("{", encoding="utf-8")
    else:
        path.unlink()

    report = store.refresh()
    assert report.fetched == [CYCLE] and not report.failed
    assert path.read_bytes() == original
    assert store.resolver(CYCLE)[0] == CYCLE


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
