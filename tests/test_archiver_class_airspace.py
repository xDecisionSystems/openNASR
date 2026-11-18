"""The FAA Class B/C/D/E shapefile zip becomes a Parquet file of polygons."""

from datetime import date, datetime, timezone
from shutil import copyfile
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

shapefile = pytest.importorskip("shapefile")

from openNASR_archiver import classairspace  # noqa: E402
from openNASR.cycles import CycleManager  # noqa: E402
from openNASR_api import CycleStore, create_app  # noqa: E402
from openNASR_archiver import backfill, publish_cycle, rebuild_from_bucket, run_once  # noqa: E402
from openNASR_contract import LocalBucket, fetch_build, list_builds  # noqa: E402

FIELDS = (
    "IDENT",
    "NAME",
    "CLASS",
    "LOCAL_TYPE",
    "UPPER_VAL",
    "UPPER_UOM",
    "UPPER_CODE",
    "LOWER_VAL",
    "LOWER_UOM",
    "LOWER_CODE",
    "SHAPE_Leng",
)


def _square(x, y, size=1.0):
    return [
        [
            (x, y, 0),
            (x + size, y, 0),
            (x + size, y + size, 0),
            (x, y + size, 0),
            (x, y, 0),
        ]
    ]


def _zip(tmp_path, classes):
    base = tmp_path / "Class_Airspace"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYGONZ)
    for name in FIELDS:
        writer.field(name, "C", 40)
    for index, airspace_class in enumerate(classes):
        writer.polyz(_square(index * 2.0, 0.0))
        writer.record(
            f"ID{index}",
            f"AREA {index}",
            airspace_class,
            f"CLASS_{airspace_class}",
            "10000",
            "FT",
            "MSL",
            "700",
            "FT",
            "SFC",
            "1.0",
        )
    writer.close()
    archive = tmp_path / "shapes.zip"
    with ZipFile(archive, "w") as output:
        for suffix in ("shp", "shx", "dbf"):
            output.write(f"{base}.{suffix}", f"Shape_Files/Class_Airspace.{suffix}")
    return archive


@pytest.fixture(autouse=True)
def _small_minimum(monkeypatch):
    monkeypatch.setattr(classairspace, "MIN_ROWS", 4)


def test_polygons_and_attributes_are_written_as_published(tmp_path):
    import duckdb
    import shapely

    archive = _zip(tmp_path, ["B", "C", "D", "E", "E"])
    out = tmp_path / "class_airspace.parquet"

    summary = classairspace.build_class_airspace(archive, out)

    assert summary.rows == 5 and summary.repaired == 0
    assert summary.by_class == {"B": 1, "C": 1, "D": 1, "E": 2}
    rows = (
        duckdb.connect()
        .execute(f"SELECT * FROM read_parquet('{out}') ORDER BY NAME")
        .fetchall()
    )
    columns = [
        c[0]
        for c in duckdb.connect()
        .execute(f"SELECT * FROM read_parquet('{out}')")
        .description
    ]
    assert "SHAPE_LENG" not in [c.upper() for c in columns]  # derived field dropped
    first = dict(zip(columns, rows[0]))
    assert (
        first["NAME"] == "AREA 0"
        and first["CLASS"] == "B"
        and first["LOWER_VAL"] == "700"
    )
    geometry = shapely.from_wkb(first["GEOMETRY_WKB"])
    assert geometry.geom_type == "Polygon" and not shapely.has_z(geometry)
    assert geometry.contains(shapely.Point(0.5, 0.5))


def test_a_zip_without_the_shapefile_is_refused(tmp_path):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as output:
        output.writestr("readme.txt", "no shapes here")

    with pytest.raises(classairspace.ClassAirspaceError, match="no Class_Airspace.shp"):
        classairspace.build_class_airspace(archive, tmp_path / "x.parquet")


def test_too_few_or_missing_classes_are_refused(tmp_path):
    few = _zip(tmp_path, ["B", "C"])
    with pytest.raises(classairspace.ClassAirspaceError, match="only 2"):
        classairspace.build_class_airspace(few, tmp_path / "a.parquet")
    other = tmp_path / "other"
    other.mkdir()
    no_e = _zip(other, ["B", "C", "D", "D"])
    with pytest.raises(classairspace.ClassAirspaceError, match="Class E"):
        classairspace.build_class_airspace(no_e, tmp_path / "b.parquet")


def test_airspace_build_retries_and_backfills_over_b1(
    make_nasr_from_fixture, tmp_path, monkeypatch
):
    _, cache = make_nasr_from_fixture("schema_only/nasr_2026_09")
    cycle = date(2026, 9, 3)
    manager = CycleManager(cache)
    bucket = LocalBucket(tmp_path / "bucket")
    old = publish_cycle(manager, cycle, bucket, builder=1, required_tables=()).manifest
    store = CycleStore(tmp_path / "api", bucket, today=lambda: cycle)
    assert store.refresh().fetched == [cycle.isoformat()]
    client = TestClient(create_app(store, [], require_auth=False))
    endpoint = "/v1/airspace/at?lat=0.5&lon=0.5"
    before = client.get(endpoint).json()
    assert "Class B/C/D/E" in before["not_covered"] and before["regions"] == []
    zip_path = manager.airspace_archive_path(cycle)
    copyfile(_zip(tmp_path, ["B", "C", "D", "E"]), zip_path)

    def fail_manifest(*args):
        raise OSError("interrupted before commit")

    with monkeypatch.context() as patch:
        patch.setattr(bucket, "put_bytes", fail_manifest)
        (result,) = backfill(manager, bucket, [cycle], required_tables=())
        assert result.status == "failed"
        assert list_builds(bucket) == [old]
    (result,) = backfill(manager, bucket, [cycle], required_tables=())
    assert result.status == "published"
    first, new = list_builds(bucket)
    assert first == old
    assert new.builder == 2 and new.class_airspace.rows == 4
    assert store.refresh().fetched == [cycle.isoformat()]
    after = client.get(endpoint).json()
    assert (
        "Special-use" in after["not_covered"]
        and "Class B/C/D/E" not in after["not_covered"]
    )
    assert after["regions"] == [
        {
            "id": "ID0",
            "name": "AREA 0",
            "kind": "CLASS",
            "level": "",
            "airspace_class": "B",
            "local_type": "CLASS_B",
            "lower": {"value": "700", "unit": "FT", "code": "SFC"},
            "upper": {"value": "10000", "unit": "FT", "code": "MSL"},
        }
    ]
    (store.cache_dir / "cycles" / cycle.isoformat() / "class_airspace.parquet").unlink()
    assert store.refresh().fetched == [cycle.isoformat()]
    assert client.get(endpoint).json() == after
    output = tmp_path / "fetched"
    fetch_build(bucket, new, output)
    assert (output / "class_airspace.parquet").is_file()
    rebuilt = rebuild_from_bucket(bucket, new, tmp_path / "rebuild")
    assert rebuilt.ok and rebuilt.class_airspace_rows_match is True
    manager.store_sha256_metadata(zip_path)
    assert manager.remove(cycle).removed_archive
    assert not zip_path.exists()
    assert not zip_path.with_suffix(".zip.json").exists()


@pytest.mark.parametrize("invalid", [False, True])
def test_airspace_source_and_validation_errors_block_the_archiver(
    make_nasr_from_fixture, tmp_path, invalid
):
    from types import SimpleNamespace

    from openNASR.cycles import RemoteCycle

    _, cache = make_nasr_from_fixture("schema_only/nasr_2026_09")
    cycle = date(2026, 9, 3)
    provider = SimpleNamespace(discover=lambda: RemoteCycle(cycle, "unused"))
    manager = CycleManager(cache, provider=provider)
    if invalid:
        copyfile(_zip(tmp_path, ["B", "C", "D"]), manager.airspace_archive_path(cycle))
    bucket = LocalBucket(tmp_path / "bucket")
    alerts = []
    outcome = run_once(
        manager,
        bucket,
        tmp_path / "state.json",
        notifier=SimpleNamespace(notify=lambda *event: alerts.append(event)),
        now=lambda: datetime(2026, 9, 3, tzinfo=timezone.utc),
        required_tables=(),
    )
    expected = "validation_failed" if invalid else "source_unavailable"
    assert outcome.status == "failed" and outcome.kind == expected
    assert alerts[0][:2] == (expected, "firing")
    assert list(bucket.list_keys()) == []
