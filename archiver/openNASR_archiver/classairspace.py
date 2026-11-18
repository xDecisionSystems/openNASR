"""Turn the FAA Class B/C/D/E shapefile zip into the Parquet file the API reads.

The FAA publishes one shapefile (``Class_Airspace``) per 28-day cycle with a
polygon for every Class B, C, D and E area and its altitude limits. This keeps
every FAA attribute as text, exactly as published, and stores the outline as
2D WKB in ``GEOMETRY_WKB``. Invalid outlines are repaired and counted, never
silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from zipfile import ZipFile

from openNASR.cycles import check_archive_members

GEOMETRY_COLUMN = "GEOMETRY_WKB"
CLASSES = ("B", "C", "D", "E")
DROPPED = ("SHAPE_LENG", "SHAPE_AREA")  # derived by the FAA tooling, in degrees
MIN_ROWS = 100  # a real cycle has thousands; far fewer means a bad download


class ClassAirspaceError(RuntimeError):
    """Raised when the shapefile zip is missing, malformed or implausible."""


@dataclass(frozen=True)
class ClassAirspaceSummary:
    rows: int
    repaired: int
    by_class: dict[str, int]


def build_class_airspace(zip_path: Path, parquet_path: Path) -> ClassAirspaceSummary:
    """Write ``parquet_path`` from the FAA shapefile zip and describe the result."""

    import duckdb
    import pandas
    import shapefile
    import shapely
    from shapely.geometry import shape as to_shapely
    from shapely.validation import make_valid

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    # Extract beside the output: the system temp directory can be a small RAM disk.
    with tempfile.TemporaryDirectory(dir=parquet_path.parent, prefix=".shp-") as work:
        directory = Path(work)
        try:
            with ZipFile(zip_path) as archive:
                check_archive_members(archive)
                members = [
                    name
                    for name in archive.namelist()
                    if Path(name).stem.lower() == "class_airspace"
                    and Path(name).suffix.lower() in {".shp", ".shx", ".dbf"}
                ]
                if not any(name.lower().endswith(".shp") for name in members):
                    raise ClassAirspaceError("the zip has no Class_Airspace.shp")
                for name in members:
                    target = directory / Path(name).name.lower()
                    with archive.open(name) as source, target.open("wb") as output:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
            reader = shapefile.Reader(str(directory / "class_airspace"))
        except ClassAirspaceError:
            raise
        except Exception as error:
            raise ClassAirspaceError(
                f"cannot read the shapefile zip: {error}"
            ) from error

        names = [field[0].upper() for field in reader.fields[1:]]
        if "CLASS" not in names:
            raise ClassAirspaceError("the shapefile has no CLASS field")
        rows: list[dict[str, object]] = []
        repaired = 0
        for record in reader.iterShapeRecords():
            geometry = shapely.force_2d(to_shapely(record.shape.__geo_interface__))
            if not geometry.is_valid:
                geometry = make_valid(geometry)
                repaired += 1
            if geometry.is_empty:
                continue
            row: dict[str, object] = {
                name: ("" if value is None else str(value).strip())
                for name, value in zip(names, record.record)
                if name not in DROPPED
            }
            row[GEOMETRY_COLUMN] = geometry.wkb
            rows.append(row)

    by_class = {c: sum(1 for r in rows if r["CLASS"] == c) for c in CLASSES}
    if len(rows) < MIN_ROWS:
        raise ClassAirspaceError(
            f"the shapefile holds only {len(rows)} usable polygons; expected thousands"
        )
    missing = [c for c, n in by_class.items() if n == 0]
    if missing:
        raise ClassAirspaceError(f"no Class {', '.join(missing)} polygons were found")

    frame = pandas.DataFrame(rows)
    temporary = parquet_path.with_name(f".{parquet_path.name}.tmp")
    connection = duckdb.connect()
    try:
        connection.register("class_airspace", frame)
        connection.execute(
            f"COPY class_airspace TO '{temporary.as_posix()}' "
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    finally:
        connection.close()
    temporary.replace(parquet_path)
    return ClassAirspaceSummary(len(rows), repaired, by_class)
