"""The bucket contract: key layout and manifest."""

import json

import pytest

from openNASR_contract import (
    ArtifactRef,
    BucketKeyError,
    Manifest,
    ManifestError,
    build_keys,
    parse_manifest_key,
)

ZIP_SHA = "a" * 64
DB_SHA = "b" * 64
FINGERPRINT = "c" * 64


def _manifest(**overrides):
    keys = build_keys("2026-10-29", ZIP_SHA, 1)
    fields = dict(
        effective_date="2026-10-29",
        builder=1,
        zip=ArtifactRef(keys.zip, ZIP_SHA, 248_000_000),
        duckdb=ArtifactRef(keys.duckdb, DB_SHA, 560_000_000),
        sidecar=ArtifactRef(keys.sidecar, DB_SHA, 1_000),
        duckdb_version="1.4.4",
        schema_id="nasr_2026_09",
        procedure_order="flight_order",
        source_schema_fingerprint=FINGERPRINT,
        tables={"APT_BASE": 19434},
        created_at="2026-11-16T12:00:00+00:00",
        archiver_version="0.1.0",
    )
    fields.update(overrides)
    return Manifest(**fields)


def test_keys_follow_the_documented_layout():
    keys = build_keys("2026-10-29", ZIP_SHA, 2)

    assert keys.zip == f"2026/2026-10-29_{ZIP_SHA}.zip"
    assert keys.duckdb == f"2026/2026-10-29_{ZIP_SHA}.b2.duckdb"
    assert keys.manifest == f"2026/2026-10-29_{ZIP_SHA}.b2.json"


@pytest.mark.parametrize(
    ("date", "sha", "builder"),
    [
        ("2026-10-2", ZIP_SHA, 1),
        ("2026/10/29", ZIP_SHA, 1),
        ("2026-10-29", "A" * 64, 1),
        ("2026-10-29", "a" * 63, 1),
        ("2026-10-29", ZIP_SHA, 0),
        ("2026-10-29", ZIP_SHA, True),
        ("../2026-10-29", ZIP_SHA, 1),
    ],
)
def test_invalid_key_parts_are_rejected(date, sha, builder):
    with pytest.raises(BucketKeyError):
        build_keys(date, sha, builder)


def test_manifest_key_round_trips():
    keys = build_keys("2026-10-29", ZIP_SHA, 3)

    assert parse_manifest_key(keys.manifest) == keys


@pytest.mark.parametrize(
    "key",
    [
        f"2026/2026-10-29_{ZIP_SHA}.zip",
        f"2025/2026-10-29_{ZIP_SHA}.b1.json",
        f"2026/2026-10-29_{ZIP_SHA}.b0.json",
        f"../2026/2026-10-29_{ZIP_SHA}.b1.json",
        "manifest.json",
    ],
)
def test_non_manifest_keys_are_rejected(key):
    with pytest.raises(BucketKeyError):
        parse_manifest_key(key)


def test_manifest_round_trips_through_json():
    original = _manifest()

    assert Manifest.from_json(original.to_json()) == original
    assert original.keys().manifest.endswith(".b1.json")


def test_manifest_artifact_keys_must_match_the_layout():
    with pytest.raises(ManifestError, match="do not match"):
        _manifest(duckdb=ArtifactRef("2026/other.duckdb", DB_SHA, 1))


def test_manifest_rejects_an_unsupported_layout_version():
    with pytest.raises(ManifestError, match="layout version"):
        _manifest(layout_version=2)


@pytest.mark.parametrize("field", ["effective_date", "zip", "tables", "schema_id"])
def test_manifest_requires_every_field(field):
    value = json.loads(_manifest().to_json())
    del value[field]

    with pytest.raises(ManifestError, match=field):
        Manifest.from_dict(value)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda v: v.update(builder="1"),
        lambda v: v.update(tables={"APT_BASE": -1}),
        lambda v: v["zip"].update(size=True),
        lambda v: v["duckdb"].update(sha256="xyz"),
        lambda v: v.update(source_schema_fingerprint="short"),
    ],
)
def test_manifest_rejects_wrong_types_and_values(mutate):
    value = json.loads(_manifest().to_json())
    mutate(value)

    with pytest.raises(ManifestError):
        Manifest.from_dict(value)


def test_manifest_rejects_non_json_and_non_objects():
    for text in ("not json", "[]", b"\xff\xfe"):
        with pytest.raises(ManifestError):
            Manifest.from_json(text)
