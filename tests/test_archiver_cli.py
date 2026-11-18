"""The archiver command line against a local bucket."""

from datetime import date
from functools import partial
import json

import pytest

from openNASR.cycles import CycleManager
from openNASR_archiver import WebhookNotifier, cli, rebuild_from_bucket
from openNASR_contract import LocalBucket, select_build

FIXTURE = "schema_only/nasr_2026_09"


@pytest.fixture
def cached(make_nasr_from_fixture, tmp_path):
    nasr, cache_root = make_nasr_from_fixture(FIXTURE)
    return nasr.effective_date, cache_root, tmp_path / "bucket"


def _main(*arguments):
    return cli.main(list(arguments))


def test_publish_status_and_rebuild_round_trip(cached, tmp_path, capsys, monkeypatch):
    effective_date, cache, bucket_dir = cached
    # The fixture's tables are empty, so relax the real required-table gate.
    from openNASR_archiver import publish as publish_module

    monkeypatch.setattr(publish_module, "REQUIRED_TABLES", ())
    monkeypatch.setattr(
        cli, "publish_cycle", partial(publish_module.publish_cycle, builder=1)
    )
    common = ["--local-bucket", str(bucket_dir), "--cache-dir", str(cache)]

    assert _main(*common, "publish", effective_date) == 0
    assert "published" in capsys.readouterr().out
    assert _main(*common, "publish", effective_date) == 0
    assert "already published" in capsys.readouterr().out

    assert _main(*common, "status") == 0
    assert f"{effective_date} b1 nasr_2026_09 flight_order" in capsys.readouterr().out

    fresh = tmp_path / "fresh-cache"
    assert (
        _main("--local-bucket", str(bucket_dir), "--cache-dir", str(fresh), "rebuild")
        == 0
    )
    assert "tables match" in capsys.readouterr().out


def test_rebuild_reports_a_difference(cached, tmp_path):
    effective_date, cache, bucket_dir = cached
    bucket = LocalBucket(bucket_dir)
    from openNASR_archiver import publish as publish_module

    publish_module.publish_cycle(
        CycleManager(cache),
        date.fromisoformat(effective_date),
        bucket,
        builder=1,
        required_tables=(),
    )
    manifest = select_build(bucket)
    path = bucket.root / manifest.keys().manifest
    value = json.loads(path.read_text())
    value["tables"] = {**value["tables"], "APT_BASE": 12345}
    path.write_text(json.dumps(value))
    tampered = select_build(bucket)

    report = rebuild_from_bucket(bucket, tampered, tmp_path / "other")

    assert not report.tables_match and not report.ok


def test_missing_s3_settings_are_a_clear_error(capsys, monkeypatch):
    for name in list(__import__("os").environ):
        if name.startswith("OPENNASR_"):
            monkeypatch.delenv(name)

    assert _main("status") == 2
    assert "OPENNASR_S3_BUCKET is not set" in capsys.readouterr().err


def test_status_of_an_empty_bucket(tmp_path, capsys):
    assert _main("--local-bucket", str(tmp_path / "b"), "status") == 0
    assert "no validated builds" in capsys.readouterr().out


def test_webhook_alerts_are_posted_and_failures_do_not_raise():
    sent = []

    class Response:
        def close(self):
            pass

    def opener(request, timeout):
        sent.append(json.loads(request.data))
        return Response()

    WebhookNotifier("https://example.invalid/hook", opener=opener).notify(
        "bucket_unavailable", "firing", "down"
    )
    assert "bucket_unavailable" in sent[0]["text"] and "firing" in sent[0]["text"]

    def broken(request, timeout):
        raise OSError("no route")

    WebhookNotifier("https://example.invalid/hook", opener=broken).notify(
        "x", "firing", "y"
    )
