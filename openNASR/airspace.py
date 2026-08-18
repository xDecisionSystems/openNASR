"""Rich objects for FAA airspace tables: airport-linked class airspace and
ARTCC boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pandas import DataFrame
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry

from .airport import AirportRecord
from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord, dms_coordinate, integer, nullable_text
from .relationships import related_record

AIRPORT_SITE_KEY = ("SITE_NO", "SITE_TYPE_CODE")
AIRSPACE_BOUNDARY_TYPES = frozenset({"ARTCC", "FIR", "CTA", "CTA/FIR", "UTA"})
_AIRSPACE_ENTITY_TYPES = {
    "airport": ("APT_BASE", "ARPT_NAME", "ARPT_ID"),
    "fix": ("FIX_BASE", "FIX_NAME", "FIX_ID"),
    "navaid": ("NAV_BASE", "NAME", "NAV_ID"),
}


def _normalized_entity_type(value: object) -> str:
    normalized = str(value).strip().lower().replace("_", "")
    aliases = {
        "airports": "airport",
        "fixes": "fix",
        "airnav": "navaid",
        "airnavs": "navaid",
        "navaids": "navaid",
        "airways": "airway",
    }
    return aliases.get(normalized, normalized)


def _text(value: object) -> str | None:
    if value is None or value != value:
        return None
    text = str(value).strip()
    return text or None


def _point(row: Mapping[str, object]) -> Point | None:
    try:
        longitude = float(str(row["LONG_DECIMAL"]).strip())
        latitude = float(str(row["LAT_DECIMAL"]).strip())
    except (KeyError, TypeError, ValueError):
        return None
    return Point(longitude, latitude)


def _print_entities_in_geometry(
    nasr: Mapping[str, DataFrame], geometry: BaseGeometry, data_type: object
) -> tuple[str, ...]:
    """Print and return named FAA entities contained by a boundary geometry."""

    entity_type = _normalized_entity_type(data_type)
    if entity_type in _AIRSPACE_ENTITY_TYPES:
        table, name_column, identifier_column = _AIRSPACE_ENTITY_TYPES[entity_type]
        labels = []
        for row in nasr[table].to_dict(orient="records"):
            point = _point(row)
            if point is None or not geometry.covers(point):
                continue
            label = _text(row.get(name_column)) or _text(row.get(identifier_column))
            if label is not None:
                labels.append(label)
    elif entity_type == "airway":
        labels = []
        coordinates: dict[str, list[Point]] = {}
        for table, identifier_column in (
            ("FIX_BASE", "FIX_ID"),
            ("NAV_BASE", "NAV_ID"),
        ):
            for row in nasr[table].to_dict(orient="records"):
                identifier = _text(row.get(identifier_column))
                point = _point(row)
                if identifier is not None and point is not None:
                    coordinates.setdefault(identifier, []).append(point)
        for key, rows in nasr["AWY_SEG_ALT"].groupby(
            ["REGULATORY", "AWY_LOCATION", "AWY_ID"], sort=False
        ):
            ordered_rows = sorted(
                rows.to_dict(orient="records"),
                key=lambda row: int(str(row["POINT_SEQ"])),
            )
            points = []
            for row in ordered_rows:
                candidates = coordinates.get(_text(row.get("FROM_POINT")) or "", [])
                points.append(candidates[0] if len(candidates) == 1 else None)
            if any(
                start is not None
                and end is not None
                and geometry.intersects(LineString((start, end)))
                for start, end in zip(points, points[1:])
            ):
                labels.append(_text(key[2]) or "unnamed airway")
    else:
        supported = "airport, fix, navaid (or airnav), airway"
        raise ValueError(f"data_type must be one of: {supported}")

    unique_labels = tuple(dict.fromkeys(labels))
    for label in unique_labels:
        print(label)
    return unique_labels


class Boundary:
    """Shapely boundary assembled from FAA longitude and latitude vertices.

    Explicitly closed rings are preserved as separate polygons. Geographic
    output is available in both ``lonlat`` and ``latlon`` ordering, and
    :attr:`getShape` exposes the underlying Shapely geometry.
    """

    def __init__(self, lons: Any = None, lats: Any = None) -> None:
        points = [(lon, lat) for lon, lat in zip(lons, lats)]
        parts = self._rings(points)
        polygons = [Polygon(part) for part in parts]
        self.__boundary = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)

    @staticmethod
    def _rings(points: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
        """Split explicitly closed source rings without joining disjoint parts."""

        rings = []
        current = []
        for point in points:
            current.append(point)
            if len(current) >= 4 and point == current[0]:
                rings.append(current)
                current = []
        if current:
            rings.append(current)
        return rings

    @property
    def lat(self) -> list[float]:
        return (
            self.__boundary.geoms[0].exterior.coords.xy[1].tolist()
            if isinstance(self.__boundary, MultiPolygon)
            else self.__boundary.exterior.coords.xy[1].tolist()
        )

    @property
    def lon(self) -> list[float]:
        return (
            self.__boundary.geoms[0].exterior.coords.xy[0].tolist()
            if isinstance(self.__boundary, MultiPolygon)
            else self.__boundary.exterior.coords.xy[0].tolist()
        )

    @property
    def latlon(self) -> list[tuple[float, float]]:
        """Boundary vertices as ``(latitude, longitude)`` pairs."""

        return [(lat, lon) for lat, lon in zip(self.lat, self.lon)]

    @property
    def lonlat(self) -> list[tuple[float, float]]:
        """Boundary vertices as ``(longitude, latitude)`` pairs."""

        return [(lon, lat) for lat, lon in zip(self.lat, self.lon)]

    @property
    def getShape(self) -> Polygon | MultiPolygon:
        """Return the underlying Shapely polygon or multipolygon."""

        return self.__boundary

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Return bounds as ``(min_lon, min_lat, max_lon, max_lat)``."""

        return self.__boundary.bounds


def _ends_in_a_closed_ring(points: list[tuple[float, float]]) -> bool:
    """Return whether ``points`` fully decomposes into closed rings under
    :meth:`Boundary._rings`, with no trailing unclosed tail.

    Used to decide whether a coordinate sequence is already in the
    explicitly-closed-ring form ``Boundary``/``ARB_SEG`` expect (so it
    should be passed through unchanged, preserving any multipart split) or
    still needs its final ring closed (the common ``MAA_SHP`` case, which
    publishes one flat, unclosed ring per area).
    """

    current: list[tuple[float, float]] = []
    for point in points:
        current.append(point)
        if len(current) >= 4 and point == current[0]:
            current = []
    return not current


class ClassAirspaceRecord(FaaRecord):
    """Typed conveniences for one airport-linked class-airspace row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def site_no(self) -> str | None:
        return self._text("SITE_NO")

    @property
    def site_type_code(self) -> str | None:
        return self._text("SITE_TYPE_CODE")

    @property
    def airport_id(self) -> str | None:
        return self._text("ARPT_ID")

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        """Verified key shared with the corresponding ``APT_BASE`` row."""

        if self.site_no is None or self.site_type_code is None:
            return None
        return self.site_no, self.site_type_code

    @property
    def classes(self) -> Mapping[str, str | None]:
        """Raw FAA class-airspace codes keyed by class letter."""

        return {
            letter: self._text(f"CLASS_{letter}_AIRSPACE")
            for letter in ("B", "C", "D", "E")
        }


class ClassAirspace:
    """Rich view of a ``CLS_ARSP`` row linked to one airport site."""

    def __init__(self, record: ClassAirspaceRecord) -> None:
        self.record = record

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        return self.record.airport_site_key

    @property
    def airport_id(self) -> str | None:
        return self.record.airport_id

    @property
    def classes(self) -> Mapping[str, str | None]:
        return self.record.classes


class ClassAirspaceRepository:
    """Lookup class-airspace records by their verified airport-site key."""

    entity_type = "ClassAirspace"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["CLS_ARSP"]

    def _site_key(self, identifier: object) -> tuple[object, object]:
        if not isinstance(identifier, tuple) or len(identifier) != len(
            AIRPORT_SITE_KEY
        ):
            columns = ", ".join(AIRPORT_SITE_KEY)
            raise ValueError(f"ClassAirspace identifiers require ({columns})")
        return identifier

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[ClassAirspace, ...]:
        """Return records matching a site key and every supported filter."""

        rows = self._table
        if identifier is not None:
            site_no, site_type_code = self._site_key(identifier)
            rows = rows[
                rows["SITE_NO"].map(self._normalized).eq(self._normalized(site_no))
                & rows["SITE_TYPE_CODE"]
                .map(self._normalized)
                .eq(self._normalized(site_type_code))
            ]
        for column, value in filters.items():
            if column not in {"airport_id", "state", "country"}:
                raise ValueError(f"Unsupported ClassAirspace filter: {column}")
            source_column = {
                "airport_id": "ARPT_ID",
                "state": "STATE_CODE",
                "country": "COUNTRY_CODE",
            }[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(
            ClassAirspace(ClassAirspaceRecord(row))
            for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object, **filters: object) -> ClassAirspace:
        """Return exactly one class-airspace record for a verified site key."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


class ArtccRecord(FaaRecord):
    """Typed conveniences for one ``ARB_BASE`` row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def location_id(self) -> str | None:
        return self._text("LOCATION_ID")

    @property
    def name(self) -> str | None:
        return self._text("LOCATION_NAME")

    @property
    def center_type(self) -> str | None:
        return self._text("LOCATION_TYPE")

    @property
    def city(self) -> str | None:
        return self._text("CITY")

    @property
    def state(self) -> str | None:
        return self._text("STATE")

    @property
    def country(self) -> str | None:
        return self._text("COUNTRY_CODE")

    @property
    def latitude(self) -> str | None:
        return self._text("LAT_DECIMAL")

    @property
    def longitude(self) -> str | None:
        return self._text("LONG_DECIMAL")


class ArtccBoundary:
    """Rich view of one ARTCC boundary (a single altitude/type group).

    Wraps :class:`Boundary`; ring splitting preserves disjoint source rings.
    """

    def __init__(self, boundary: Boundary) -> None:
        self._boundary = boundary

    @property
    def lat(self) -> list[float]:
        return self._boundary.lat

    @property
    def lon(self) -> list[float]:
        return self._boundary.lon

    @property
    def latlon(self) -> list[tuple[float, float]]:
        return self._boundary.latlon

    @property
    def lonlat(self) -> list[tuple[float, float]]:
        return self._boundary.lonlat

    @property
    def getShape(self):
        return self._boundary.getShape

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self._boundary.bbox


class AirspaceBoundary:
    """One FAA ``ARB_SEG`` boundary, such as an ARTCC, FIR, CTA, or UTA.

    The FAA identifies a boundary by its location identifier, boundary type,
    and altitude. The ordered vertices are retained as :attr:`boundary`.
    """

    def __init__(
        self,
        record: ArtccRecord,
        boundary: ArtccBoundary,
        *,
        boundary_type: str,
        altitude: str,
    ) -> None:
        self.record = record
        self.boundary = boundary
        self.boundary_type = boundary_type
        self.altitude = altitude

    @property
    def location_id(self) -> str | None:
        """FAA location identifier, such as ``"ZAN"``."""

        return self.record.location_id

    def __str__(self) -> str:
        """Return the boundary type and FAA location name."""

        name = self.record.name or self.location_id or "unnamed"
        return f"AirspaceBoundary ({self.boundary_type}): {name}"

    @property
    def geometry(self):
        """The boundary's Shapely polygon or multipolygon geometry."""

        return self.boundary.getShape

    def plot(self, nasr: Mapping[str, DataFrame], **kwargs: Any) -> tuple[Any, Any]:
        """Plot this boundary through :func:`openNASR.plotting.plot_airspace`.

        Boundary-only rendering is the default because FIR/CTA/UTA geometry
        can be oceanic or cross the antimeridian. Enable individual map layers
        explicitly (for example ``plot_low_airways=True``) when appropriate.
        """

        from .plotting import plot_airspace

        for option in (
            "plot_high_airways",
            "plot_low_airways",
            "plot_airports",
            "plot_fixes",
            "plot_airnavs",
        ):
            kwargs.setdefault(option, False)
        return plot_airspace(nasr, self.boundary, **kwargs)

    def print(
        self, nasr: Mapping[str, DataFrame], data_type: object
    ) -> tuple[str, ...]:
        """Print and return named entities of ``data_type`` within this boundary.

        Supported selectors are ``"airport"``, ``"fix"``, ``"navaid"``
        (also ``"airnav"``), and ``"airway"``; plural forms are accepted.
        """

        return _print_entities_in_geometry(nasr, self.geometry, data_type)


class AirspaceBoundaryRepository:
    """Look up every FAA ``ARB_SEG`` boundary type by its complete key."""

    entity_type = "AirspaceBoundary"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    def find(
        self,
        identifier: object | None = None,
        *,
        boundary_type: str | None = None,
        altitude: str | None = None,
    ) -> tuple[AirspaceBoundary, ...]:
        """Return boundaries matching a location ID, type, and/or altitude.

        ``boundary_type`` accepts ``ARTCC``, ``FIR``, ``CTA``, ``CTA/FIR``,
        and ``UTA``. Results retain FAA source-row order within each boundary.
        """

        segments = self._nasr["ARB_SEG"]
        rows = segments
        if identifier is not None:
            normalized = self._normalized(identifier)
            rows = rows[rows["LOCATION_ID"].map(self._normalized).eq(normalized)]
        if boundary_type is not None:
            normalized_type = self._normalized(boundary_type)
            if normalized_type not in AIRSPACE_BOUNDARY_TYPES:
                supported = ", ".join(sorted(AIRSPACE_BOUNDARY_TYPES))
                raise ValueError(f"boundary_type must be one of: {supported}")
            rows = rows[rows["TYPE"].map(self._normalized).eq(normalized_type)]
        if altitude is not None:
            rows = rows[
                rows["ALTITUDE"].map(self._normalized).eq(self._normalized(altitude))
            ]

        bases = self._nasr["ARB_BASE"]
        base_by_identifier = {
            self._normalized(row["LOCATION_ID"]): row
            for row in bases.to_dict(orient="records")
        }
        results = []
        for (location_id, type_name, level), group in rows.groupby(
            ["LOCATION_ID", "TYPE", "ALTITUDE"], sort=False
        ):
            base = base_by_identifier.get(self._normalized(location_id))
            if base is None:
                continue
            results.append(
                AirspaceBoundary(
                    ArtccRecord(base),
                    ArtccBoundary(
                        Boundary(group["LONG_DECIMAL"], group["LAT_DECIMAL"])
                    ),
                    boundary_type=self._normalized(type_name),
                    altitude=self._normalized(level),
                )
            )
        return tuple(results)

    def get(
        self,
        identifier: object,
        *,
        boundary_type: str,
        altitude: str | None = None,
    ) -> AirspaceBoundary:
        """Return exactly one boundary selected by its FAA location and type."""

        records = self.find(identifier, boundary_type=boundary_type, altitude=altitude)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters={"boundary_type": boundary_type, "altitude": altitude},
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters={"boundary_type": boundary_type, "altitude": altitude},
                candidates=records,
            )
        return records[0]


class Artcc:
    """Rich view of an ``ARB_BASE`` row plus its ``ARB_SEG`` boundaries."""

    def __init__(
        self,
        record: ArtccRecord,
        boundaries: Mapping[str, ArtccBoundary],
    ) -> None:
        self.record = record
        self.boundaries = boundaries

    @property
    def location_id(self) -> str | None:
        return self.record.location_id

    @property
    def name(self) -> str | None:
        return self.record.name

    @property
    def high(self) -> ArtccBoundary | None:
        return self.boundaries.get("high")

    @property
    def low(self) -> ArtccBoundary | None:
        return self.boundaries.get("low")

    def __str__(self) -> str:
        """Return the ARTCC type and FAA center name."""

        return f"Artcc: {self.name or self.location_id or 'unnamed'}"

    def plot(self, nasr: Mapping[str, DataFrame], **kwargs: Any) -> tuple[Any, Any]:
        """Plot this ARTCC's high- or low-altitude boundary and map layers.

        Additional keyword arguments are passed to
        :func:`openNASR.plotting.plot_artcc`. The high-altitude boundary is
        selected by default; pass ``level="low"`` for the low boundary.
        """

        from .plotting import plot_artcc

        return plot_artcc(nasr, self, **kwargs)

    def print(
        self, nasr: Mapping[str, DataFrame], data_type: object, *, level: str = "high"
    ) -> tuple[str, ...]:
        """Print and return entities within this ARTCC's selected boundary."""

        boundary = self.boundaries.get(str(level).strip().lower())
        if boundary is None:
            raise ValueError(f"ARTCC has no {level!r} boundary")
        return _print_entities_in_geometry(nasr, boundary.getShape, data_type)


class ArtccRepository:
    """Lookup ARTCCs by ``LOCATION_ID``, with their boundaries attached."""

    entity_type = "Artcc"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["ARB_BASE"]

    def _boundaries(self, location_id: str) -> dict[str, ArtccBoundary]:
        segments = self._nasr.get("ARB_SEG")
        if segments is None:
            return {}
        matching = segments[
            segments["LOCATION_ID"].map(self._normalized).eq(location_id)
        ]
        boundaries: dict[str, ArtccBoundary] = {}
        # Preserve FAA row order within each (ALTITUDE, TYPE) group: Boundary
        # relies on encountering a ring's points in source order to detect
        # where the ring closes, so groups must not be sorted or reordered.
        for (altitude, _boundary_type), group in matching.groupby(
            ["ALTITUDE", "TYPE"], sort=False
        ):
            key = str(altitude).strip().lower()
            boundaries[key] = ArtccBoundary(
                Boundary(group["LONG_DECIMAL"], group["LAT_DECIMAL"])
            )
        return boundaries

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[Artcc, ...]:
        """Return ARTCCs matching ``LOCATION_ID`` and every supported filter."""

        rows = self._table
        if identifier is not None:
            normalized = self._normalized(identifier)
            rows = rows[rows["LOCATION_ID"].map(self._normalized).eq(normalized)]
        for column, value in filters.items():
            if column not in {"state", "country"}:
                raise ValueError(f"Unsupported Artcc filter: {column}")
            source_column = {"state": "STATE", "country": "COUNTRY_CODE"}[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        results = []
        for row in rows.to_dict(orient="records"):
            record = ArtccRecord(row)
            results.append(
                Artcc(record, self._boundaries(self._normalized(row["LOCATION_ID"])))
            )
        return tuple(results)

    def get(self, identifier: object, **filters: object) -> Artcc:
        """Return exactly one ARTCC for a ``LOCATION_ID`` (and any filters)."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


class MaaRecord(FaaRecord):
    """Typed conveniences for one ``MAA_BASE`` row.

    ``MAA`` is the FAA's "Miscellaneous Activity Area" family (aerobatic
    practice, glider, hang glider, space launch, ultralight, and unmanned
    aircraft areas) as defined by the FAA's ``MAA DATA LAYOUT.pdf``. It is
    unrelated to military airspace.
    """

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def maa_id(self) -> str | None:
        return self._text("MAA_ID")

    @property
    def type_name(self) -> str | None:
        return self._text("MAA_TYPE_NAME")

    @property
    def name(self) -> str | None:
        return self._text("MAA_NAME")

    @property
    def city(self) -> str | None:
        return self._text("CITY")

    @property
    def state(self) -> str | None:
        return self._text("STATE_CODE")

    @property
    def max_altitude(self) -> str | None:
        return self._text("MAX_ALT")

    @property
    def min_altitude(self) -> str | None:
        return self._text("MIN_ALT")

    @property
    def radius(self) -> str | None:
        return self._text("MAA_RADIUS")

    @property
    def description(self) -> str | None:
        return self._text("DESCRIPTION")

    @property
    def use(self) -> str | None:
        return self._text("MAA_USE")

    @property
    def time_of_use(self) -> str | None:
        return self._text("TIME_OF_USE")

    @property
    def user_group_name(self) -> str | None:
        return self._text("USER_GROUP_NAME")

    @property
    def airport_ids(self) -> tuple[str, ...]:
        """FAA landing-facility identifiers associated with this area."""

        raw = self._text("ARPT_IDS")
        return tuple(raw.split()) if raw else ()


class MaaContactRecord(FaaRecord):
    """Typed conveniences for an ordered ``MAA_CON`` frequency-contact row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("FREQ_SEQ")
        return None if value is None else integer(value)

    @property
    def facility_id(self) -> str | None:
        return self._text("FAC_ID")

    @property
    def facility_name(self) -> str | None:
        return self._text("FAC_NAME")

    @property
    def commercial_frequency(self) -> str | None:
        return self._text("COMMERCIAL_FREQ")

    @property
    def military_frequency(self) -> str | None:
        return self._text("MIL_FREQ")


class MaaRemarkRecord(FaaRecord):
    """Typed conveniences for an ordered ``MAA_RMK`` remark row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def table_name(self) -> str | None:
        return self._text("TAB_NAME")

    @property
    def reference_column(self) -> str | None:
        return self._text("REF_COL_NAME")

    @property
    def sequence(self) -> int | None:
        value = self._text("REF_COL_SEQ_NO")
        return None if value is None else integer(value)

    @property
    def remark(self) -> str | None:
        return self._text("REMARK")


class MaaShapePointRecord(FaaRecord):
    """Typed conveniences for an ordered ``MAA_SHP`` polygon-point row."""

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def sequence(self) -> int | None:
        value = self._text("POINT_SEQ")
        return None if value is None else integer(value)

    @property
    def latitude(self) -> float | None:
        value = self._text("LATITUDE")
        return None if value is None else dms_coordinate(value)

    @property
    def longitude(self) -> float | None:
        value = self._text("LONGITUDE")
        return None if value is None else dms_coordinate(value)


class Maa:
    """One Miscellaneous Activity Area with its contacts, remarks, and shape."""

    def __init__(
        self,
        record: MaaRecord,
        *,
        contacts: tuple[MaaContactRecord, ...],
        remarks: tuple[MaaRemarkRecord, ...],
        shape_points: tuple[MaaShapePointRecord, ...],
    ) -> None:
        self.record = record
        self.contacts = contacts
        self.remarks = remarks
        self.shape_points = shape_points

    @property
    def maa_id(self) -> str | None:
        return self.record.maa_id

    @property
    def name(self) -> str | None:
        return self.record.name

    def __str__(self) -> str:
        """Return the activity-area type and published name."""

        return f"Maa: {self.name or self.maa_id or 'unnamed'}"

    @property
    def geometry(self):
        """A Shapely polygon (or multipolygon) built from the ordered
        ``MAA_SHP`` points.

        Returns ``None`` when the area has no published shape (some
        ``MAA_BASE`` rows describe only a center point and radius).
        ``MAA_SHP`` has no part/ring column -- every sampled real ``MAA_ID``
        is a single, flat, unclosed ring (unlike ``ARB_SEG``) -- so the
        common case closes it by appending its first point. If the points
        already contain one or more explicitly closed rings (each part
        repeating its own first point, the way ``ARB_SEG`` and
        ``Boundary._rings`` expect), they are passed through unchanged so a
        hypothetical multipart ``MAA_ID`` still splits correctly instead of
        gaining a spurious trailing point.
        """

        if not self.shape_points:
            return None
        points = [
            (point.longitude, point.latitude)
            for point in self.shape_points
            if point.longitude is not None and point.latitude is not None
        ]
        if not points:
            return None
        if not _ends_in_a_closed_ring(points):
            points = [*points, points[0]]
        lons, lats = zip(*points)
        return Boundary(lons, lats).getShape

    def print(
        self, nasr: Mapping[str, DataFrame], data_type: object
    ) -> tuple[str, ...]:
        """Print and return entities within this activity area's published shape."""

        geometry = self.geometry
        if geometry is None:
            raise ValueError("MAA has no published polygon geometry")
        return _print_entities_in_geometry(nasr, geometry, data_type)


class MaaRepository:
    """Lookup Miscellaneous Activity Areas by ``MAA_ID``."""

    entity_type = "Maa"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["MAA_BASE"]

    def _matching(self, frame: DataFrame, maa_id: str) -> DataFrame:
        return frame[frame["MAA_ID"].map(self._normalized).eq(maa_id)]

    @staticmethod
    def _contact_order(row: dict[str, object]) -> int:
        sequence = row.get("FREQ_SEQ")
        return int(str(sequence)) if sequence not in (None, "") else -1

    @staticmethod
    def _remark_order(row: dict[str, object]) -> tuple[str, str, int]:
        sequence = row.get("REF_COL_SEQ_NO")
        return (
            str(row.get("TAB_NAME", "")),
            str(row.get("REF_COL_NAME", "")),
            int(str(sequence)) if sequence not in (None, "") else -1,
        )

    @staticmethod
    def _point_order(row: dict[str, object]) -> int:
        sequence = row.get("POINT_SEQ")
        return int(str(sequence)) if sequence not in (None, "") else -1

    def _maa(self, row: dict[str, object]) -> Maa:
        maa_id = self._normalized(row["MAA_ID"])
        contacts = sorted(
            self._matching(self._nasr["MAA_CON"], maa_id).to_dict(orient="records"),
            key=self._contact_order,
        )
        remarks = sorted(
            self._matching(self._nasr["MAA_RMK"], maa_id).to_dict(orient="records"),
            key=self._remark_order,
        )
        shape_points = sorted(
            self._matching(self._nasr["MAA_SHP"], maa_id).to_dict(orient="records"),
            key=self._point_order,
        )
        return Maa(
            MaaRecord(row),
            contacts=tuple(MaaContactRecord(item) for item in contacts),
            remarks=tuple(MaaRemarkRecord(item) for item in remarks),
            shape_points=tuple(MaaShapePointRecord(item) for item in shape_points),
        )

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[Maa, ...]:
        """Return areas matching ``MAA_ID`` and every supported filter."""

        rows = self._table
        if identifier is not None:
            normalized = self._normalized(identifier)
            rows = rows[rows["MAA_ID"].map(self._normalized).eq(normalized)]
        for column, value in filters.items():
            if column not in {"state", "type_name"}:
                raise ValueError(f"Unsupported Maa filter: {column}")
            source_column = {"state": "STATE_CODE", "type_name": "MAA_TYPE_NAME"}[
                column
            ]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(self._maa(row) for row in rows.to_dict(orient="records"))

    def get(self, identifier: object, **filters: object) -> Maa:
        """Return exactly one area for a ``MAA_ID`` (and any filters)."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


class ParachuteJumpAreaRecord(FaaRecord):
    """Typed conveniences for one ``PJA_BASE`` row.

    ``PJA_BASE`` has no matching shape table -- unlike ``MAA_SHP``/
    ``ARB_SEG``, a parachute jump area is described by a center point and
    ``PJA_RADIUS``, not a polygon.
    """

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def pja_id(self) -> str | None:
        return self._text("PJA_ID")

    @property
    def drop_zone_name(self) -> str | None:
        return self._text("DROP_ZONE_NAME")

    @property
    def city(self) -> str | None:
        return self._text("CITY")

    @property
    def state(self) -> str | None:
        return self._text("STATE_CODE")

    @property
    def latitude(self) -> float | None:
        value = self._text("LAT_DECIMAL")
        return None if value is None else float(value)

    @property
    def longitude(self) -> float | None:
        value = self._text("LONG_DECIMAL")
        return None if value is None else float(value)

    @property
    def airport_id(self) -> str | None:
        return self._text("ARPT_ID")

    @property
    def airport_site_key(self) -> tuple[str, str] | None:
        """The linked airport's key, when this area has one (not every
        ``PJA_BASE`` row does -- ``SITE_NO`` is populated on roughly two
        thirds of rows in the verified sample cycle)."""

        site_no = self._text("SITE_NO")
        site_type_code = self._text("SITE_TYPE_CODE")
        if site_no is None or site_type_code is None:
            return None
        return site_no, site_type_code

    @property
    def max_altitude(self) -> str | None:
        return self._text("MAX_ALTITUDE")

    @property
    def radius(self) -> str | None:
        return self._text("PJA_RADIUS")

    @property
    def description(self) -> str | None:
        return self._text("DESCRIPTION")

    @property
    def use(self) -> str | None:
        return self._text("PJA_USE")

    @property
    def time_of_use(self) -> str | None:
        return self._text("TIME_OF_USE")

    @property
    def remark(self) -> str | None:
        return self._text("REMARK")


class ParachuteJumpAreaContactRecord(FaaRecord):
    """Typed conveniences for one ``PJA_CON`` contact row.

    Ordered by ``PJA_ID, FAC_NAME`` -- a name-based key, not the numeric
    ``*_SEQ`` pattern every other contact table in this codebase uses
    (verified against the real FAA archive, task 12.2).
    """

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None or value != value else nullable_text(str(value))

    @property
    def facility_id(self) -> str | None:
        return self._text("FAC_ID")

    @property
    def facility_name(self) -> str | None:
        return self._text("FAC_NAME")

    @property
    def location_id(self) -> str | None:
        return self._text("LOC_ID")

    @property
    def commercial_frequency(self) -> str | None:
        return self._text("COMMERCIAL_FREQ")

    @property
    def military_frequency(self) -> str | None:
        return self._text("MIL_FREQ")

    @property
    def sector(self) -> str | None:
        return self._text("SECTOR")


class ParachuteJumpArea:
    """One parachute jump area with its contacts and (optional) airport."""

    def __init__(
        self,
        record: ParachuteJumpAreaRecord,
        *,
        contacts: tuple[ParachuteJumpAreaContactRecord, ...],
        airport: AirportRecord | None,
    ) -> None:
        self.record = record
        self.contacts = contacts
        self.airport = airport

    @property
    def pja_id(self) -> str | None:
        return self.record.pja_id

    @property
    def drop_zone_name(self) -> str | None:
        return self.record.drop_zone_name

    def __str__(self) -> str:
        """Return the jump-area type and published drop-zone name."""

        return f"ParachuteJumpArea: {self.drop_zone_name or self.pja_id or 'unnamed'}"


class ParachuteJumpAreaRepository:
    """Lookup parachute jump areas by ``PJA_ID``."""

    entity_type = "ParachuteJumpArea"

    def __init__(self, nasr: Mapping[str, DataFrame]) -> None:
        self._nasr = nasr

    @staticmethod
    def _normalized(value: object) -> str:
        if value is None or value != value:
            return ""
        return str(value).strip().upper()

    @property
    def _table(self) -> DataFrame:
        return self._nasr["PJA_BASE"]

    def _matching(self, frame: DataFrame, pja_id: str) -> DataFrame:
        return frame[frame["PJA_ID"].map(self._normalized).eq(pja_id)]

    @staticmethod
    def _contact_order(row: dict[str, object]) -> tuple[str, str]:
        return (str(row.get("PJA_ID", "")), str(row.get("FAC_NAME", "")))

    def _parachute_jump_area(self, row: dict[str, object]) -> ParachuteJumpArea:
        pja_id = self._normalized(row["PJA_ID"])
        contacts = sorted(
            self._matching(self._nasr["PJA_CON"], pja_id).to_dict(orient="records"),
            key=self._contact_order,
        )
        return ParachuteJumpArea(
            ParachuteJumpAreaRecord(row),
            contacts=tuple(ParachuteJumpAreaContactRecord(item) for item in contacts),
            airport=related_record(
                self._nasr,
                source=row,
                target_table="APT_BASE",
                columns=(
                    ("SITE_NO", "SITE_NO"),
                    ("SITE_TYPE_CODE", "SITE_TYPE_CODE"),
                ),
                record_type=AirportRecord,
                relationship="parachute-jump-area airport",
            ),
        )

    def find(
        self, identifier: object | None = None, **filters: object
    ) -> tuple[ParachuteJumpArea, ...]:
        """Return areas matching ``PJA_ID`` and every supported filter."""

        rows = self._table
        if identifier is not None:
            normalized = self._normalized(identifier)
            rows = rows[rows["PJA_ID"].map(self._normalized).eq(normalized)]
        for column, value in filters.items():
            if column not in {"state", "airport_id"}:
                raise ValueError(f"Unsupported ParachuteJumpArea filter: {column}")
            source_column = {"state": "STATE_CODE", "airport_id": "ARPT_ID"}[column]
            rows = rows[
                rows[source_column].map(self._normalized).eq(self._normalized(value))
            ]
        return tuple(
            self._parachute_jump_area(row) for row in rows.to_dict(orient="records")
        )

    def get(self, identifier: object, **filters: object) -> ParachuteJumpArea:
        """Return exactly one area for a ``PJA_ID`` (and any filters)."""

        records = self.find(identifier, **filters)
        if not records:
            raise RecordNotFoundError(
                entity_type=self.entity_type, identifier=identifier, filters=filters
            )
        if len(records) > 1:
            raise AmbiguousRecordError(
                entity_type=self.entity_type,
                identifier=identifier,
                filters=filters,
                candidates=records,
            )
        return records[0]


__all__ = [
    "AIRSPACE_BOUNDARY_TYPES",
    "AirspaceBoundary",
    "AirspaceBoundaryRepository",
    "Artcc",
    "ArtccBoundary",
    "ArtccRecord",
    "ArtccRepository",
    "Boundary",
    "ClassAirspace",
    "ClassAirspaceRepository",
    "Maa",
    "MaaContactRecord",
    "MaaRecord",
    "MaaRemarkRecord",
    "MaaRepository",
    "MaaShapePointRecord",
    "ParachuteJumpArea",
    "ParachuteJumpAreaContactRecord",
    "ParachuteJumpAreaRecord",
    "ParachuteJumpAreaRepository",
]
