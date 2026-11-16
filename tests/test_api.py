"""The HTTP API against a real (synthetic-fixture) cycle."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from openNASR_api import CycleStore, create_app

KEY = "test-key-1"
HEADERS = {"X-API-Key": KEY}
CYCLE = "2026-08-06"


@pytest.fixture
def client(make_nasr_from_fixture):
    _, cache_root = make_nasr_from_fixture("core/pre_2026_09")  # builds the cycle
    store = CycleStore(cache_root, today=lambda: date(2026, 8, 20))
    return TestClient(create_app(store, [KEY, "test-key-2"]))


def test_health_needs_no_key_and_ready_names_the_default_cycle(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json() == {"status": "ready", "default_cycle": CYCLE}


def test_resolve_requires_a_valid_key(client):
    body = {"route": "BWI AABEE DCA"}

    assert client.post("/v1/route/resolve", json=body).status_code == 401
    assert (
        client.post(
            "/v1/route/resolve", json=body, headers={"X-API-Key": "no"}
        ).status_code
        == 401
    )
    assert (
        client.post("/v1/route/resolve", json=body, headers=HEADERS).status_code == 200
    )
    bearer = {"Authorization": "Bearer test-key-2"}
    assert (
        client.post("/v1/route/resolve", json=body, headers=bearer).status_code == 200
    )


def test_resolve_returns_points_with_provenance_and_geojson(client):
    response = client.post(
        "/v1/route/resolve", json={"route": "BWI AABEE DCA"}, headers=HEADERS
    )

    data = response.json()
    assert data["cycle"] == CYCLE and data["complete"] is True
    assert [p["name"] for p in data["points"]] == ["BWI", "AABEE", "DCA"]
    assert data["points"][0] == {
        "lat": data["points"][0]["lat"],
        "lon": data["points"][0]["lon"],
        "name": "BWI",
        "kind": "airport",
        "via": None,
        "segment": "origin",
    }
    geometry = data["geojson"]["geometry"]
    assert geometry["type"] == "LineString"
    first = data["points"][0]
    assert geometry["coordinates"][0] == [first["lon"], first["lat"]]  # lon, lat
    assert data["diagnostics"] == []


def test_the_same_route_and_cycle_give_identical_output(client):
    body = {"route": "BWI AABEE DCA", "cycle": CYCLE}

    first = client.post("/v1/route/resolve", json=body, headers=HEADERS).json()
    second = client.post("/v1/route/resolve", json=body, headers=HEADERS).json()

    assert first == second


def test_get_form_matches_post(client):
    post = client.post(
        "/v1/route/resolve", json={"route": "BWI AABEE DCA"}, headers=HEADERS
    )
    get = client.get(
        "/v1/route/resolve", params={"route": "BWI AABEE DCA"}, headers=HEADERS
    )

    assert get.status_code == 200 and get.json() == post.json()


def test_unresolvable_routes_are_a_200_with_diagnostics_never_a_500(client):
    response = client.post(
        "/v1/route/resolve", json={"route": "BWI NOSUCHFIX DCA"}, headers=HEADERS
    )

    data = response.json()
    assert response.status_code == 200
    assert data["complete"] is False and data["points"] == []
    assert data["geojson"]["geometry"] is None
    assert data["diagnostics"][0]["code"] == "RecordNotFoundError"
    assert data["diagnostics"][0]["token"] == "NOSUCHFIX"


def test_input_errors_are_422_and_an_unknown_cycle_is_404(client):
    assert (
        client.post(
            "/v1/route/resolve", json={"route": " "}, headers=HEADERS
        ).status_code
        == 422
    )
    assert client.post("/v1/route/resolve", json={}, headers=HEADERS).status_code == 422
    assert (
        client.post(
            "/v1/route/resolve",
            json={"route": "BWI DCA", "cycle": "2020-01-02"},
            headers=HEADERS,
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/v1/route/resolve",
            json={"route": "BWI DCA", "cycle": "bad"},
            headers=HEADERS,
        ).status_code
        == 422
    )


def test_cycles_lists_what_is_available(client):
    data = client.get("/v1/cycles", headers=HEADERS).json()

    assert data["default"] == CYCLE
    assert data["cycles"][0]["effective_date"] == CYCLE
    assert data["cycles"][0]["in_effect"] is True


def test_no_cycles_means_not_ready(tmp_path):
    empty = TestClient(create_app(CycleStore(tmp_path / "empty"), [KEY]))

    assert empty.get("/ready").status_code == 503
    assert (
        empty.post(
            "/v1/route/resolve", json={"route": "A B"}, headers=HEADERS
        ).status_code
        == 503
    )


def test_an_icao_message_is_accepted_and_reports_what_was_extracted(client):
    message = (
        "(FPL-UAL123-IS-B738/M-SDE2FGHIRWY/LB1-KBWI1530-N0450F350 AABEE "
        "-KDCA0210 KIAD-PBN/A1)"
    )

    response = client.post(
        "/v1/route/resolve", json={"icao_message": message}, headers=HEADERS
    )

    assert response.status_code == 200
    data = response.json()
    assert data["input"] == {
        "mode": "icao_message",
        "extracted": {
            "message_type": "FPL",
            "aircraft_id": "UAL123",
            "departure": "KBWI",
            "destination": "KDCA",
            "route_field": "N0450F350 AABEE",
        },
    }
    assert data["route"] == "KBWI AABEE KDCA"
    assert [p["name"] for p in data["points"]] == ["KBWI", "AABEE", "KDCA"]
    assert data["complete"] is True


def test_route_mode_echoes_its_mode(client):
    data = client.post(
        "/v1/route/resolve", json={"route": "BWI AABEE DCA"}, headers=HEADERS
    ).json()

    assert data["input"] == {"mode": "route", "extracted": None}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"route": "BWI AABEE DCA", "icao_message": "(FPL-A-B-C-D-E-F-G)"},
        {"route": "  ", "icao_message": ""},
    ],
)
def test_exactly_one_input_is_required(client, body):
    assert (
        client.post("/v1/route/resolve", json=body, headers=HEADERS).status_code == 422
    )


def test_a_bad_icao_message_is_a_422_with_the_reason(client):
    response = client.post(
        "/v1/route/resolve",
        json={"icao_message": "(ARR-UAL123-KAAA-KBBB)"},
        headers=HEADERS,
    )

    assert response.status_code == 422
    assert "only FPL" in response.json()["detail"]
