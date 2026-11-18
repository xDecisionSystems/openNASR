"""A reader with only bucket access can fetch, verify and open a build."""

from datetime import date

import pytest

from openNASR.cycles import CycleManager
from openNASR.nasr import NASR
from openNASR_archiver import publish_cycle
from openNASR_contract import (
    FetchError,
    LocalBucket,
    fetch_build,
    list_builds,
    select_build,
)

FIXTURE = "schema_only/nasr_2026_09"


@pytest.fixture
def published(make_nasr_from_fixture, tmp_path):
    nasr, cache_root = make_nasr_from_fixture(FIXTURE)
    bucket = LocalBucket(tmp_path / "bucket")
    result = publish_cycle(
        CycleManager(cache_root),
        date.fromisoformat(nasr.effective_date),
        bucket,
        required_tables=(),
    )
    return bucket, result.manifest


def test_a_fresh_machine_with_only_the_bucket_can_open_the_cycle(published, tmp_path):
    bucket, manifest = published
    fresh_cache = tmp_path / "fresh"

    build = select_build(bucket, effective_date="2026-09-03")
    assert build == manifest
    fetch_build(bucket, build, fresh_cache / "cycles" / "2026-09-03")

    nasr = NASR(cycle="2026-09-03", cache_dir=fresh_cache)
    assert nasr.effective_date == "2026-09-03"
    assert nasr.procedure_order == "flight_order"
    assert "APT_BASE" in set(nasr)
    assert not (fresh_cache / "archives").exists()  # no zip, no CSVs needed


def test_fetching_again_reuses_verified_files(published, tmp_path):
    bucket, manifest = published
    directory = tmp_path / "cache"
    first = fetch_build(bucket, manifest, directory)
    mtime = first.stat().st_mtime_ns

    assert fetch_build(bucket, manifest, directory).stat().st_mtime_ns == mtime


def test_a_corrupted_object_is_never_installed(published, tmp_path):
    bucket, manifest = published
    (bucket.root / manifest.duckdb.key).write_bytes(b"corrupt")

    with pytest.raises(FetchError, match="does not match"):
        fetch_build(bucket, manifest, tmp_path / "cache")

    assert not (tmp_path / "cache" / "nasr.duckdb").exists()
    assert not list((tmp_path / "cache").glob(".fetch-*"))


def test_a_sidecar_for_another_database_is_refused(published, tmp_path):
    bucket, manifest = published
    sidecar_path = bucket.root / manifest.sidecar.key
    text = sidecar_path.read_text(encoding="utf-8").replace(
        manifest.duckdb.sha256, "0" * 64
    )
    sidecar_path.write_text(text, encoding="utf-8")

    with pytest.raises(FetchError):
        fetch_build(bucket, manifest, tmp_path / "cache")


def test_selection_prefers_the_newest_cycle_and_supported_builders(published):
    bucket, manifest = published

    assert select_build(bucket) == manifest
    assert select_build(bucket, on_or_before="2026-09-02") is None
    assert select_build(bucket, on_or_before="2026-12-31") == manifest
    assert select_build(bucket, supported_builders={2}) is None
    assert select_build(bucket, supported_procedure_orders=("reversed",)) is None


def test_unreadable_manifests_are_skipped_not_fatal(published):
    bucket, manifest = published
    broken = manifest.keys().manifest.replace(".b1.", ".b7.")
    bucket.put_bytes(broken, b"not json")

    assert list_builds(bucket) == [manifest]


def test_a_reposted_cycle_resolves_to_the_newest_build(published):
    import dataclasses

    from openNASR_contract import ArtifactRef, build_keys

    bucket, first = published
    keys = build_keys(first.effective_date, "d" * 64, first.builder)
    second = dataclasses.replace(
        first,
        zip=ArtifactRef(keys.zip, "d" * 64, first.zip.size),
        duckdb=ArtifactRef(keys.duckdb, first.duckdb.sha256, first.duckdb.size),
        sidecar=ArtifactRef(keys.sidecar, first.sidecar.sha256, first.sidecar.size),
        created_at="2099-01-01T00:00:00+00:00",
    )
    bucket.put_bytes(second.keys().manifest, second.to_json().encode())

    assert select_build(bucket, effective_date=first.effective_date) == second


def _publish_with_airspace(published):
    """Add a Class B/C/D/E parquet and a matching manifest next to the build."""

    import dataclasses
    import hashlib

    from openNASR_contract import ArtifactRef, ClassAirspace, class_airspace_source_key

    bucket, manifest = published
    keys = manifest.keys()
    parquet = b"parquet bytes"
    source = b"faa shapefile zip"
    parquet_sha = hashlib.sha256(parquet).hexdigest()
    source_sha = hashlib.sha256(source).hexdigest()
    source_key = class_airspace_source_key(
        manifest.effective_date, manifest.zip.sha256, source_sha
    )
    bucket.put_bytes(keys.class_airspace, parquet)
    bucket.put_bytes(source_key, source)
    extended = dataclasses.replace(
        manifest,
        class_airspace=ClassAirspace(
            ArtifactRef(source_key, source_sha, len(source)),
            ArtifactRef(keys.class_airspace, parquet_sha, len(parquet)),
            3,
        ),
    )
    # the manifest key is the same, so replace the stored manifest
    (bucket.root / keys.manifest).write_text(extended.to_json(), encoding="utf-8")
    return bucket, extended


def test_fetching_a_build_with_class_airspace_installs_the_parquet(published, tmp_path):
    bucket, manifest = _publish_with_airspace(published)

    fetch_build(bucket, manifest, tmp_path / "cycle")

    assert (
        tmp_path / "cycle" / "class_airspace.parquet"
    ).read_bytes() == b"parquet bytes"
    assert (tmp_path / "cycle" / "nasr.duckdb").is_file()


def test_a_corrupted_parquet_is_never_installed(published, tmp_path):
    bucket, manifest = _publish_with_airspace(published)
    (bucket.root / manifest.class_airspace.parquet.key).write_bytes(b"damaged")

    with pytest.raises(FetchError, match="does not match"):
        fetch_build(bucket, manifest, tmp_path / "cycle")

    assert not (tmp_path / "cycle" / "class_airspace.parquet").exists()
    assert not (tmp_path / "cycle" / "nasr.duckdb").exists()


def test_a_build_without_class_airspace_installs_no_parquet(published, tmp_path):
    bucket, manifest = published

    fetch_build(bucket, manifest, tmp_path / "cycle")

    assert not (tmp_path / "cycle" / "class_airspace.parquet").exists()
