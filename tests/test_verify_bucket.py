"""tools/verify_bucket.py finds damaged or missing objects."""

from datetime import date

import pytest

from openNASR.cycles import CycleManager
from openNASR_archiver import publish_cycle
from openNASR_contract import LocalBucket
from tools.verify_bucket import main, verify_build

FIXTURE = "schema_only/nasr_2026_09"


@pytest.fixture
def published(make_nasr_from_fixture, tmp_path):
    nasr, cache_root = make_nasr_from_fixture(FIXTURE)
    bucket = LocalBucket(tmp_path / "bucket")
    result = publish_cycle(
        CycleManager(cache_root),
        date.fromisoformat(nasr.effective_date),
        bucket,
        builder=1,
        required_tables=(),
    )
    return bucket, result.manifest, tmp_path / "bucket"


def test_a_sound_build_has_no_problems(published):
    bucket, manifest, _ = published

    assert verify_build(bucket, manifest, check_zip=True) == []


def test_a_damaged_database_is_reported(published):
    bucket, manifest, root = published
    (root / manifest.duckdb.key).write_bytes(b"damaged")

    problems = verify_build(bucket, manifest)

    assert len(problems) == 1 and "does not match" in problems[0]


def test_the_archive_is_only_checked_when_asked(published):
    bucket, manifest, root = published
    (root / manifest.zip.key).write_bytes(b"not the archive")

    assert verify_build(bucket, manifest) == []
    problems = verify_build(bucket, manifest, check_zip=True)
    assert any("size differs" in p for p in problems)
    assert any("hash differs" in p for p in problems)


def test_a_missing_archive_is_reported(published):
    bucket, manifest, root = published
    (root / manifest.zip.key).unlink()

    problems = verify_build(bucket, manifest, check_zip=True)

    assert len(problems) == 1 and "cannot read" in problems[0]


def test_the_command_exits_nonzero_only_on_problems(published, capsys):
    _, manifest, root = published

    assert main(["--local-bucket", str(root), "--zips"]) == 0
    assert f"ok {manifest.effective_date}" in capsys.readouterr().out

    (root / manifest.duckdb.key).write_bytes(b"damaged")
    assert main(["--local-bucket", str(root)]) == 1
    assert "FAIL" in capsys.readouterr().out
    assert main(["--local-bucket", str(root), "--cycle", "2020-01-02"]) == 1
