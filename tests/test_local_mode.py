"""Local mode: `opennasr route|fetch|serve` match the HTTP API."""

from datetime import date
import json

import pytest
from fastapi.testclient import TestClient

from openNASR import cli
from openNASR.cycles import CycleManager
from openNASR_api import CycleStore, create_app
from openNASR_archiver import publish_cycle
from openNASR_contract import LocalBucket

KEY = "local-mode-key"
ICAO = "(FPL-UAL123-IS-B738/M-S-KBWI1530-N0450F350 AABEE -KDCA0210 KIAD-PBN/A1)"


@pytest.fixture
def cache(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    return cache_root


def run(cache, capsys, *arguments):
    code = cli.main(["--cache-dir", str(cache), *arguments])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


@pytest.fixture
def api(cache):
    store = CycleStore(cache, today=lambda: date(2026, 8, 20))
    app = create_app(store, [KEY], rate_limit_per_minute=0)
    return TestClient(app), {"X-API-Key": KEY}


@pytest.mark.parametrize(
    "request_body",
    [
        {"route": "BWI AABEE DCA"},
        {"route": "BWI NOSUCHFIX DCA"},
        {"route": "BWI AABEE/N0450F350 DCA"},
        {"route": "BWI AABEE DCA", "max_segment_nm": 10},
        {"route": "BWI AABEE DCA", "cycle": "2026-08-06"},
        {"icao_message": ICAO},
    ],
    ids=[
        "complete",
        "unknown-fix",
        "ignored-group",
        "densified",
        "named-cycle",
        "icao",
    ],
)
def test_the_cli_and_the_api_return_the_same_body(cache, capsys, api, request_body):
    client, headers = api
    arguments = ["route"]
    if "icao_message" in request_body:
        arguments += ["--icao-message", request_body["icao_message"]]
    else:
        arguments += [request_body["route"]]
    if "cycle" in request_body:
        arguments += ["--cycle", request_body["cycle"]]
    if "max_segment_nm" in request_body:
        arguments += ["--max-segment-nm", str(request_body["max_segment_nm"])]

    code, out, _ = run(cache, capsys, *arguments)
    served = client.post("/v1/route/resolve", json=request_body, headers=headers)

    assert code == 0 and served.status_code == 200
    assert json.loads(out) == served.json()


def test_geojson_and_table_formats(cache, capsys):
    _, out, _ = run(cache, capsys, "route", "BWI AABEE DCA", "--format", "geojson")
    feature = json.loads(out)
    assert feature["geometry"]["type"] == "LineString"
    assert len(feature["geometry"]["coordinates"]) == 3

    _, out, _ = run(cache, capsys, "route", "BWI AABEE DCA", "--format", "table")
    rows = out.strip().splitlines()
    assert len(rows) == 3 and "AABEE" in rows[1] and "origin" in rows[0]


def test_strict_exits_nonzero_for_an_incomplete_route_only(cache, capsys):
    ok, _, _ = run(cache, capsys, "route", "BWI AABEE DCA", "--strict")
    bad, out, _ = run(cache, capsys, "route", "BWI NOSUCHFIX DCA", "--strict")
    lenient, _, _ = run(cache, capsys, "route", "BWI NOSUCHFIX DCA")

    assert (ok, bad, lenient) == (0, 1, 0)
    assert json.loads(out)["diagnostics"][0]["token"] == "NOSUCHFIX"


def test_the_route_can_come_from_stdin(cache, capsys, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("BWI AABEE DCA\n"))

    code, out, _ = run(cache, capsys, "route", "-")

    assert code == 0 and json.loads(out)["complete"] is True


def test_bad_input_and_an_empty_cache_are_clear_errors(cache, capsys, tmp_path):
    code, _, err = run(cache, capsys, "route", "--icao-message", "(ARR-X-Y)")
    assert code == cli.ExitCode.USAGE_ERROR and "only FPL" in err

    code, _, err = run(tmp_path / "empty", capsys, "route", "BWI DCA")
    assert code == cli.ExitCode.VALIDATION_ERROR and "opennasr fetch" in err


def test_fetch_gets_validated_cycles_from_a_bucket_and_route_uses_them(
    make_nasr_from_fixture, tmp_path, capsys, monkeypatch
):
    nasr, source_cache = make_nasr_from_fixture("schema_only/nasr_2026_09")
    bucket = LocalBucket(tmp_path / "bucket")
    publish_cycle(
        CycleManager(source_cache),
        date.fromisoformat(nasr.effective_date),
        bucket,
        required_tables=(),
    )
    monkeypatch.setenv("OPENNASR_S3_BUCKET", "nasr")
    monkeypatch.setattr(
        "openNASR_contract.s3.S3Bucket.from_env",
        classmethod(lambda cls, env, role: bucket),
    )
    fresh = tmp_path / "fresh"

    code, out, _ = run(fresh, capsys, "fetch", "all")
    assert code == 0 and "fetched: 2026-09-03" in out
    assert (fresh / "cycles" / "2026-09-03" / "manifest.json").is_file()
    assert not (fresh / "archives").exists()

    code, out, _ = run(fresh, capsys, "route", "A B", "--cycle", "2026-09-03")
    assert code == 0 and json.loads(out)["cycle"] == "2026-09-03"

    code, _, err = run(fresh, capsys, "fetch", "2020-01-02")
    assert code == cli.ExitCode.UNAVAILABLE and "no validated build" in err


def test_serve_refuses_no_auth_on_a_public_address(cache, capsys):
    code, _, err = run(cache, capsys, "serve", "--no-auth", "--host", "0.0.0.0")

    assert code == cli.ExitCode.USAGE_ERROR and "loopback" in err


def test_serve_prints_a_session_key_and_builds_the_app(cache, capsys, monkeypatch):
    started = {}
    monkeypatch.setattr(
        "uvicorn.run", lambda app, **options: started.update(app=app, **options)
    )

    code, out, _ = run(cache, capsys, "serve", "--port", "9123")

    assert code == 0 and started["port"] == 9123 and started["host"] == "127.0.0.1"
    session_key = out.split("API key for this session: ")[1].split()[0]
    client = TestClient(started["app"])
    body = {"route": "BWI AABEE DCA"}
    assert client.post("/v1/route/resolve", json=body).status_code == 401
    ok = client.post("/v1/route/resolve", json=body, headers={"X-API-Key": session_key})
    assert ok.status_code == 200 and ok.json()["complete"] is True


def test_serve_no_auth_on_loopback_needs_no_key(cache, capsys, monkeypatch):
    started = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **options: started.update(app=app))

    code, out, _ = run(cache, capsys, "serve", "--no-auth")

    assert code == 0 and "API key" not in out
    client = TestClient(started["app"])
    assert (
        client.post("/v1/route/resolve", json={"route": "BWI AABEE DCA"}).status_code
        == 200
    )
