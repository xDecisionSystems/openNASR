"""The published API contract (docs/openapi.json) is current and well formed."""

import json

import pytest

from tools.export_openapi import OUTPUT, build_document, render

OPEN = {"/health", "/ready"}


def test_the_committed_openapi_document_matches_the_code():
    assert OUTPUT.read_text(encoding="utf-8") == render(), (
        "the API changed: run `python tools/export_openapi.py` and commit "
        "docs/openapi.json"
    )


def test_every_path_except_health_and_ready_requires_a_key():
    document = build_document()
    schemes = document["components"]["securitySchemes"]
    assert {"APIKeyHeader", "HTTPBearer"} <= set(schemes)

    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            secured = bool(operation.get("security"))
            assert secured is (path not in OPEN), f"{method.upper()} {path}"


def test_secured_operations_document_their_failure_modes():
    document = build_document()

    for path, operations in document["paths"].items():
        if path in OPEN:
            continue
        for method, operation in operations.items():
            responses = set(operation["responses"])
            assert {"200", "401", "429"} <= responses, f"{method.upper()} {path}"


def test_every_success_response_has_a_named_schema():
    document = build_document()

    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            schema = operation["responses"]["200"]["content"]["application/json"][
                "schema"
            ]
            assert "$ref" in schema, (
                f"{method.upper()} {path} has an anonymous response"
            )


def test_the_route_request_contract():
    document = build_document()
    request = document["components"]["schemas"]["RouteRequest"]["properties"]

    assert set(request) == {"route", "icao_message", "cycle", "max_segment_nm"}
    response = document["components"]["schemas"]["RouteResponse"]
    assert {
        "input",
        "route",
        "cycle",
        "complete",
        "points",
        "geojson",
        "diagnostics",
    } <= set(response["required"])
    point = document["components"]["schemas"]["Point"]["properties"]
    assert set(point) == {"lat", "lon", "name", "kind", "via", "segment"}


def test_the_document_is_valid_json_with_the_expected_paths():
    document = json.loads(OUTPUT.read_text(encoding="utf-8"))

    assert document["openapi"].startswith("3.")
    assert {
        "/v1/route/resolve",
        "/v1/airports/{identifier}",
        "/v1/fixes/{identifier}",
        "/v1/navaids/{identifier}",
        "/v1/airways/{identifier}",
        "/v1/cycles",
        "/health",
        "/ready",
    } <= set(document["paths"])
    assert document["info"]["version"]


@pytest.mark.parametrize("name", ["Problem", "Diagnostic", "RouteResponse"])
def test_shared_schemas_are_defined(name):
    assert name in build_document()["components"]["schemas"]
