"""The FAA Class B/C/D/E shapefile zip becomes a Parquet file of polygons."""

from zipfile import ZipFile

import pytest

shapefile = pytest.importorskip("shapefile")

from openNASR_archiver import classairspace  # noqa: E402

FIELDS = ("NAME", "UPPER_VAL", "LOWER_VAL", "CLASS", "SHAPE_Leng")


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
        writer.record(f"AREA {index}", "10000", "700", airspace_class, "1.0")
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
