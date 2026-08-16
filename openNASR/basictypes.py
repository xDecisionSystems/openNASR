from types import SimpleNamespace
from .cfcn import ll2xy

# class Point(object):
#     @property
#     def lat(self):
#         return self.base.LAT_DECIMAL

#     @property
#     def lon(self):
#         return self.base.LONG_DECIMAL

def getAirportRecords(airport,nasrDF,airportIDCol):
    return [SimpleNamespace( **cRecord ) for cRecord in nasrDF[nasrDF[airportIDCol]==airport].to_dict(orient='records')]

def getAirportRecord(airport,nasrDF,airportIDCol):
    return SimpleNamespace(  **nasrDF[nasrDF[airportIDCol]==airport].to_dict(orient='records')[0]  )


class Point():
    def __init__(self,sm):
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
        return [self._raw.LONG_DECIMAL,self._raw.LAT_DECIMAL]

class Raw():
    def __init__(self,sm):
        self._raw = sm
        # self._raw = SimpleNamespace(  **nasrDF[nasrDF[airportIDCol]==airport].to_dict(orient='records')[0]  )

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
        return [self._raw.LONG_DECIMAL,self._raw.LAT_DECIMAL]

    @property
    def elev(self):
        if hasattr(self._raw, 'SITE_ELEVATION'):
            return self._raw.SITE_ELEVATION
        elif hasattr(self._raw, 'RWY_END_ELEV'):
            return self._raw.RWY_END_ELEV
        else:
            return None

    @property
    def elevation(self):
        if hasattr(self._raw, 'SITE_ELEVATION'):
            return self._raw.SITE_ELEVATION
        elif hasattr(self._raw, 'RWY_END_ELEV'):
            return self._raw.RWY_END_ELEV
        else:
            return None

    @property
    def len(self):
        if hasattr(self._raw,'RWY_LEN'):
            return self._raw.RWY_LEN
        else:
            return None

    @property
    def width(self):
        if hasattr(self._raw,'RWY_WIDTH'):
            return self._raw.RWY_WIDTH
        else:
            return None

    def xy(self,latc,lonc):
        x,y = ll2xy(lats=self.lat,lons=self.lon,latc=latc,lonc=lonc)[0:2]
        return x,y

    def __getattr__(self, name):
        try:
            return getattr(self._raw, name)
        except AttributeError as error:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from error


class RawDict(dict):
    def __init__(self,classType,airport,nasrDF,airportIDCol, useRWYID=False):
        self._map = {}
        self._raw = {}
        for cRec in getAirportRecords(airport,nasrDF,airportIDCol):
            if useRWYID:
                record_id = str(cRec.RWY_ID)
            else:
                record_id = str(cRec.RWY_END_ID)
            record = classType(cRec)
            self[record_id] = record
            self._map[record_id] = record
            self._raw[record_id] = cRec

    def getRawByID(self,id):
        return self._raw.get(id)

    def getRaw(self):
        return self._raw

    @property
    def ids(self):
        return list(self.keys())
