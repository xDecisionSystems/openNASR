from shapely.geometry import MultiPolygon, Polygon


class Boundary:
    def __init__(self, lons=None, lats=None):
        points = [(lon, lat) for lon, lat in zip(lons, lats)]
        parts = self._rings(points)
        polygons = [Polygon(part) for part in parts]
        self.__boundary = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)

    @staticmethod
    def _rings(points):
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
    def lat(self):
        return (
            self.__boundary.geoms[0].exterior.coords.xy[1].tolist()
            if isinstance(self.__boundary, MultiPolygon)
            else self.__boundary.exterior.coords.xy[1].tolist()
        )

    @property
    def lon(self):
        return (
            self.__boundary.geoms[0].exterior.coords.xy[0].tolist()
            if isinstance(self.__boundary, MultiPolygon)
            else self.__boundary.exterior.coords.xy[0].tolist()
        )

    @property
    def latlon(self):
        """Boundary vertices as ``(latitude, longitude)`` pairs."""
        return [(lat, lon) for lat, lon in zip(self.lat, self.lon)]

    @property
    def lonlat(self):
        """Boundary vertices as ``(longitude, latitude)`` pairs."""
        return [(lon, lat) for lat, lon in zip(self.lat, self.lon)]

    @property
    def getShape(self):
        return self.__boundary

    @property
    def bbox(self):
        """Return bounds as ``(min_lon, min_lat, max_lon, max_lat)``."""
        return self.__boundary.bounds


class ARTCC:
    def __init__(self, id, name, centerType, city, state, country, lat, lon):
        self.id = id
        self.name = name
        self.centerType = centerType
        self.city = city
        self.state = state
        self.country = country
        self.lat = lat
        self.lon = lon
        self.boundaries = {}

    def addboundary(self, altitude, lons, lats):
        key = altitude.lower()
        boundary = Boundary(lons, lats)
        self.boundaries[key] = boundary
        setattr(self, key, boundary)

    @property
    def boundaryTypes(self):
        """Compatibility list of available boundary mapping keys."""
        return list(self.boundaries)


class ARB:
    def __init__(self, nasr):
        arb_base = nasr["ARB_BASE"]
        arb_seg = nasr["ARB_SEG"]

        self.centers = list()
        for index, cARB in arb_base.iterrows():
            cLocID = cARB["LOCATION_ID"]
            setattr(
                self,
                cLocID,
                ARTCC(
                    id=cARB["LOCATION_ID"],
                    name=cARB["LOCATION_NAME"],
                    centerType=cARB["LOCATION_TYPE"],
                    city=cARB["CITY"],
                    state=cARB["STATE"],
                    country=cARB["COUNTRY_CODE"],
                    lat=cARB["LAT_DECIMAL"],
                    lon=cARB["LONG_DECIMAL"],
                ),
            )
            self.centers.append(cLocID)

        for index, row in (
            arb_seg[["LOCATION_ID", "ALTITUDE", "TYPE"]].drop_duplicates().iterrows()
        ):
            cLocID = row["LOCATION_ID"]
            cLocAlt = row["ALTITUDE"]
            cLocType = row["TYPE"]
            tmpDF = arb_seg[
                (arb_seg["LOCATION_ID"] == cLocID)
                & (arb_seg["ALTITUDE"] == cLocAlt)
                & (arb_seg["TYPE"] == cLocType)
            ]
            cARTCC = getattr(self, cLocID)
            cARTCC.addboundary(cLocAlt, tmpDF["LONG_DECIMAL"], tmpDF["LAT_DECIMAL"])

    def getARTCC(self, artcc):
        if artcc in self.centers:
            return getattr(self, artcc)
        else:
            return None
