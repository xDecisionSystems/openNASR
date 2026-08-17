from types import SimpleNamespace
from .cfcn import ll2xy


class Raw:
    def __init__(self, sm):
        self._raw = sm

    def getRaw(self):
        return self._raw

    @property
    def lat(self):
        return self._raw.LAT_DECIMAL

    @property
    def lon(self):
        return self._raw.LONG_DECIMAL

    @property
    def lonlat(self):
        return [self._raw.LONG_DECIMAL, self._raw.LAT_DECIMAL]

    @property
    def elevation(self):
        if hasattr(self._raw, "SITE_ELEVATION"):
            return self._raw.SITE_ELEVATION
        elif hasattr(self._raw, "RWY_END_ELEV"):
            return self._raw.RWY_END_ELEV
        else:
            return None

    @property
    def len(self):
        if hasattr(self._raw, "RWY_LEN"):
            return self._raw.RWY_LEN
        else:
            return None

    @property
    def width(self):
        if hasattr(self._raw, "RWY_WIDTH"):
            return self._raw.RWY_WIDTH
        else:
            return None

    def xy(self, latc, lonc):
        x, y = ll2xy(lats=self.lat, lons=self.lon, latc=latc, lonc=lonc)[0:2]
        return x, y

    def __getattr__(self, name):
        try:
            return getattr(self._raw, name)
        except AttributeError as error:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from error


class RawDict(dict):
    def __init__(self, classType, useRWYID=False, *, cached_records=None):
        self._map = {}
        self._raw = {}
        records = [SimpleNamespace(**record) for record in cached_records or ()]
        for cRec in records:
            if useRWYID:
                record_id = str(cRec.RWY_ID)
            else:
                record_id = str(cRec.RWY_END_ID)
            record = classType(cRec)
            self[record_id] = record
            self._map[record_id] = record
            self._raw[record_id] = cRec

    def getRawByID(self, id):
        return self._raw.get(id)

    def getRaw(self):
        return self._raw

    @property
    def ids(self):
        return list(self.keys())
