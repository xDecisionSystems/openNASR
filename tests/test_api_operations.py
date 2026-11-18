"""Rate limiting, request logging, error handling and the densify option."""

from datetime import date
import json
import logging

import pytest
from fastapi.testclient import TestClient

from openNASR.routeresult import RoutePoint
from openNASR_api import CycleStore, create_app
from openNASR.geo import MAX_POINTS, densify, distance_nm, intermediate
from openNASR_api.limits import RateLimiter

KEY = "operations-test-key"
HEADERS = {"X-API-Key": KEY}


@pytest.fixture
def store(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")
    return CycleStore(cache_root, today=lambda: date(2026, 8, 20))


def _client(store, **options):
    return TestClient(
        create_app(store, [KEY], **options), raise_server_exceptions=False
    )


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_the_limiter_allows_a_burst_then_refills_over_time():
    clock = FakeClock()
    limiter = RateLimiter(60, 3, clock=clock)  # 1 request a second, burst of 3

    assert [limiter.check("a") for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.check("a") == pytest.approx(1.0)
    assert limiter.check("b") == 0.0  # keys are independent
    clock.now += 2
    assert limiter.check("a") == 0.0
    assert RateLimiter(0).check("a") == 0.0  # disabled


def test_too_many_requests_get_429_with_retry_after(store):
    client = _client(store, rate_limit_per_minute=60, rate_limit_burst=2)
    body = {"route": "BWI AABEE DCA"}

    statuses = [
        client.post("/v1/route/resolve", json=body, headers=HEADERS).status_code
        for _ in range(4)
    ]
    limited = client.post("/v1/route/resolve", json=body, headers=HEADERS)

    assert statuses[:2] == [200, 200] and statuses[2:] == [429, 429]
    assert int(limited.headers["Retry-After"]) >= 1
    assert client.get("/health").status_code == 200  # never limited
    assert (
        client.post("/v1/route/resolve", json=body, headers=HEADERS).status_code == 429
    )


def test_requests_are_logged_without_secrets_and_carry_a_request_id(store, caplog):
    client = _client(store, rate_limit_per_minute=0)
    caplog.set_level(logging.INFO, logger="openNASR_api.access")

    response = client.post(
        "/v1/route/resolve",
        json={"route": "BWI AABEE DCA"},
        headers={**HEADERS, "X-Request-ID": "trace-42"},
    )

    assert response.headers["X-Request-ID"] == "trace-42"
    record = json.loads(caplog.records[-1].getMessage())
    assert record["id"] == "trace-42" and record["status"] == 200
    assert record["method"] == "POST" and record["path"] == "/v1/route/resolve"
    assert record["ms"] >= 0 and len(record["key"]) == 8
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert KEY not in logged and "AABEE" not in logged  # no key, no route text


def test_an_unsafe_request_id_is_replaced_and_failed_auth_logs_no_key(store, caplog):
    client = _client(store)
    caplog.set_level(logging.INFO, logger="openNASR_api.access")

    response = client.get("/v1/cycles", headers={"X-Request-ID": "bad id\n"})

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] != "bad id\n"
    assert len(response.headers["X-Request-ID"]) == 32
    assert json.loads(caplog.records[-1].getMessage())["key"] is None


def test_an_unexpected_error_is_a_clean_500_with_a_request_id(store, monkeypatch):
    client = _client(store, rate_limit_per_minute=0)

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(store, "resolver", boom)
    response = client.post("/v1/route/resolve", json={"route": "A B"}, headers=HEADERS)

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "internal error" and body["request_id"]
    assert "secret" not in response.text


def test_densify_keeps_the_filed_points_and_adds_great_circle_points():
    a = RoutePoint(40.0, -100.0, "AAA", "airport", None, "origin")
    b = RoutePoint(40.0, -90.0, "BBB", "airport", None, "destination")
    leg = distance_nm(40.0, -100.0, 40.0, -90.0)  # about 458 nm

    dense = densify([a, b], 100)

    assert dense[0] == a and dense[-1] == b
    assert len(dense) == 6 and 4.5 < leg / 100 < 5
    assert all(p.kind == "interpolated" and p.name == "" for p in dense[1:-1])
    gaps = [distance_nm(p.lat, p.lon, q.lat, q.lon) for p, q in zip(dense, dense[1:])]
    assert max(gaps) <= 100 and max(gaps) - min(gaps) < 0.01  # even spacing
    assert dense[1].lat > 40.0  # a great circle bows north of the parallel
    assert intermediate(40, -100, 40, -90, 0.5)[1] == pytest.approx(-95.0, abs=0.01)


def test_densify_checks_capacity_before_interpolating(monkeypatch):
    a = RoutePoint(0.0, 0.0, "A", "fix", None, "origin")
    b = RoutePoint(0.0, 179.0, "B", "fix", None, "destination")

    def unexpected_interpolation(*args):
        pytest.fail("point limit should be checked before interpolation")

    monkeypatch.setattr("openNASR.geo.intermediate", unexpected_interpolation)
    with pytest.raises(ValueError, match=str(MAX_POINTS)):
        densify([a, b], 1)
    with pytest.raises(ValueError, match=str(MAX_POINTS)):
        densify([a] * (MAX_POINTS + 1), 1)
    assert len(densify([a] * MAX_POINTS, 1)) == MAX_POINTS


def test_the_api_densifies_only_when_asked(store):
    client = _client(store, rate_limit_per_minute=0)
    plain = client.post(
        "/v1/route/resolve", json={"route": "BWI AABEE DCA"}, headers=HEADERS
    ).json()
    dense = client.post(
        "/v1/route/resolve",
        json={"route": "BWI AABEE DCA", "max_segment_nm": 5},
        headers=HEADERS,
    ).json()
    via_get = client.get(
        "/v1/route/resolve",
        params={"route": "BWI AABEE DCA", "max_segment_nm": 5},
        headers=HEADERS,
    ).json()

    assert [p["name"] for p in plain["points"]] == ["BWI", "AABEE", "DCA"]
    assert len(dense["points"]) > 3 and dense == via_get
    assert [p["name"] for p in dense["points"] if p["name"]] == ["BWI", "AABEE", "DCA"]
    assert len(dense["geojson"]["geometry"]["coordinates"]) == len(dense["points"])


@pytest.mark.parametrize("value", [0, 0.5, 5000, "x"])
def test_max_segment_nm_is_bounded(store, value):
    client = _client(store, rate_limit_per_minute=0)

    response = client.post(
        "/v1/route/resolve",
        json={"route": "BWI AABEE DCA", "max_segment_nm": value},
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_without_keys_clients_are_told_apart_by_address_for_rate_limiting(store):
    client = _client(
        store, require_auth=False, rate_limit_per_minute=60, rate_limit_burst=2
    )
    body = {"route": "BWI AABEE DCA"}

    def post(forwarded):
        return client.post(
            "/v1/route/resolve", json=body, headers={"X-Forwarded-For": forwarded}
        ).status_code

    assert [post("10.0.0.1"), post("10.0.0.1"), post("10.0.0.1")] == [200, 200, 429]
    assert post("10.0.0.2") == 200  # another client is unaffected
    assert (
        client.post("/v1/route/resolve", json=body).status_code == 200
    )  # no key needed


def test_the_service_refuses_to_start_without_keys_unless_open_access_is_explicit(
    tmp_path, monkeypatch, caplog
):
    from openNASR_api import cli

    started = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **options: started.update(options))
    monkeypatch.setattr(
        cli.CycleStore, "refresh", lambda self: type("R", (), {"fetched": []})()
    )
    base = {"OPENNASR_API_CACHE_DIR": str(tmp_path)}
    for name in ("OPENNASR_API_KEYS", "OPENNASR_API_AUTH"):
        monkeypatch.delenv(name, raising=False)

    for name, value in base.items():
        monkeypatch.setenv(name, value)
    assert cli.main([]) == 2 and started == {}

    monkeypatch.setenv("OPENNASR_API_AUTH", "none")
    monkeypatch.setenv("OPENNASR_API_HOST", "0.0.0.0")
    with caplog.at_level(logging.WARNING, logger="openNASR_api"):
        assert cli.main([]) == 0
    assert started["host"] == "0.0.0.0"
    assert "KEYS ARE OFF" in caplog.text
