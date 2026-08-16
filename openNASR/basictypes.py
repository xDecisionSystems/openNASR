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
        # Return the value of the attribute if it exists, otherwise raise an AttributeError
        if name in self._attributes:
            return self._attributes[name]
        raise AttributeError(f"'CatchAll' object has no attribute '{name}'")
    

class RawDict(dict):
    def __init__(self,classType,airport,nasrDF,airportIDCol, useRWYID=False):
        for cRec in getRecords(airport,nasrDF,airportIDCol):            
            if useRWYID:
                self[cRec.RWY_ID]=classType(cRec)
            else:
                self[cRec.RWY_END_ID]=classType(cRec)
                
        #     rwys = [cRec.RWY_END_ID for cRec in self._raw]            
        # self._map = dict(zip(rwys, range(len(rwys)) ))
        
    def getRawByID(self,id):
        if id in self._map.keys():
            return self._raw[ self._map[id] ]
        else:
            print('Unable to find', id)
            return None
    
    def getRaw(self):
        return self._raw
    
    @property
    def ids(self):
        return list(self.keys())