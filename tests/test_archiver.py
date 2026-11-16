"""Publishing a cached cycle to a bucket."""

from datetime import date

import pytest

from openNASR.cycles import CycleManager
from openNASR_archiver import PublishError, publish_cycle
from openNASR_contract import ImmutableKeyError, LocalBucket, Manifest, build_keys

FIXTURE = "schema_only/nasr_2026_09"


@pytest.fixture
def cycle(make_nasr_from_fixture):
    nasr, cache_root = make_nasr_from_fixture(FIXTURE)
    return CycleManager(cache_root), date.fromisoformat(nasr.effective_date)


def test_publish_uploads_zip_database_then_manifest(cycle, tmp_path):
    manager, effective_date = cycle
    bucket = LocalBucket(tmp_path / "bucket")

    result = publish_cycle(manager, effective_date, bucket, required_tables=())

    assert not result.already_published
    manifest = result.manifest
    keys = manifest.keys()
    assert sorted(bucket.list_keys()) == sorted(
        [keys.zip, keys.duckdb, keys.sidecar, keys.manifest]
    )
    assert Manifest.from_json(bucket.get_bytes(keys.manifest)) == manifest
    assert manifest.schema_id == "nasr_2026_09"
    assert manifest.procedure_order == "flight_order"
    assert keys == build_keys(effective_date.isoformat(), manifest.zip.sha256, 1)


def test_publishing_again_changes_nothing(cycle, tmp_path):
    manager, effective_date = cycle
    bucket = LocalBucket(tmp_path / "bucket")
    first = publish_cycle(manager, effective_date, bucket, required_tables=())

    second = publish_cycle(manager, effective_date, bucket, required_tables=())

    assert second.already_published
    assert second.manifest == first.manifest


def test_an_unrecognized_schema_is_not_published(make_nasr_from_fixture, tmp_path):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    bucket = LocalBucket(tmp_path / "bucket")

    with pytest.raises(PublishError, match="schema was not recognized"):
        publish_cycle(
            CycleManager(cache_root), date(2026, 8, 6), bucket, required_tables=()
        )

    assert list(bucket.list_keys()) == []


def test_missing_required_tables_block_publication(cycle, tmp_path):
    manager, effective_date = cycle
    bucket = LocalBucket(tmp_path / "bucket")

    with pytest.raises(PublishError, match="required tables"):
        publish_cycle(manager, effective_date, bucket, required_tables=("NO_SUCH",))

    assert list(bucket.list_keys()) == []


def test_a_cycle_that_was_never_downloaded_is_refused(tmp_path):
    with pytest.raises(PublishError, match="no downloaded archive"):
        publish_cycle(
            CycleManager(tmp_path / "cache"),
            date(2026, 10, 29),
            LocalBucket(tmp_path / "bucket"),
        )


def test_a_failed_upload_leaves_no_manifest_and_a_rerun_completes(cycle, tmp_path):
    manager, effective_date = cycle
    bucket = LocalBucket(tmp_path / "bucket")
    real_put_file = bucket.put_file

    def failing(key, path, sha256):
        if key.endswith(".duckdb"):
            raise OSError("network down")
        real_put_file(key, path, sha256)

    bucket.put_file = failing
    with pytest.raises(OSError):
        publish_cycle(manager, effective_date, bucket, required_tables=())
    assert not any(key.endswith(".json") for key in bucket.list_keys())

    bucket.put_file = real_put_file
    result = publish_cycle(manager, effective_date, bucket, required_tables=())
    assert not result.already_published
    assert result.manifest.keys().manifest in set(bucket.list_keys())


def test_a_key_is_never_overwritten_with_different_bytes(tmp_path):
    bucket = LocalBucket(tmp_path / "bucket")
    bucket.put_bytes("2026/a.json", b"one")

    bucket.put_bytes("2026/a.json", b"one")  # identical bytes: no-op
    with pytest.raises(ImmutableKeyError):
        bucket.put_bytes("2026/a.json", b"two")


def test_local_bucket_refuses_keys_outside_its_root(tmp_path):
    bucket = LocalBucket(tmp_path / "bucket")

    with pytest.raises(ValueError, match="escapes"):
        bucket.put_bytes("../outside", b"x")
