from shapely.geometry import Polygon


class Boundary():
    def __init__(self, lons = None, lats = None):
        self.__boundary = Polygon(  [(lon,lat) for lon,lat in zip(lons,lats)]   )
        
    @property
    def lat(self):
        return self.__boundary.exterior.coords.xy[1].tolist()

    @property
    def lon(self):
        return self.__boundary.exterior.coords.xy[0].tolist()        

    @property
    def latlon(self):
        return [(lat,lon) for lat, lon in zip(self.lat,self.lon)]

    @property
    def lonlat(self):
        return [(lon,lat) for lat, lon in zip(self.lat,self.lon)]

    @property
    def getShape(self):
        return self.__boundary
    
    @property
    def bbox(self):
        return min(self.lon),min(self.lat),max(self.lon),max(self.lat)

class ARTCC():
    def __init__(self, id, name, centerType, city, state, country, lat, lon):
        self.id = id
        self.name = name
        self.centerType = centerType
        self.city = city
        self.state = state
        self.country = country
        self.lat = lat
        self.lon = lon
        self.boundaryTypes = list()
        
    def addboundary(self,boundaryType,altitude,lons,lats):
        setattr(  self, altitude.lower(), Boundary(lons,lats)  )
        self.boundaryTypes.append(altitude.lower())
        
    # @property
    # def boundaryTypes(self):
    #     return list(self.keys())
    

    
class ARB():
    def __init__(self, nasr):
        arb_base = nasr['ARB_BASE']
        arb_seg = nasr['ARB_SEG']
        
        
        self.centers=list()
        for index, cARB in arb_base.iterrows():
            cLocID=cARB['LOCATION_ID']
            setattr(  self, cLocID, 
                    ARTCC(id=cARB['LOCATION_ID'],
                          name=cARB['LOCATION_NAME'],
                          centerType=cARB['LOCATION_TYPE'],
                          city=cARB['CITY'],
                          state=cARB['STATE'],
                          country=cARB['COUNTRY_CODE'],
                          lat=cARB['LAT_DECIMAL'],
                          lon=cARB['LONG_DECIMAL'])  )
            self.centers.append(  cLocID  )
            
        for index, row in arb_seg[['LOCATION_ID','ALTITUDE','TYPE']].drop_duplicates().iterrows():
            cLocID=row['LOCATION_ID']
            cLocAlt=row['ALTITUDE']
            cLocType=row['TYPE']                
            tmpDF = arb_seg[(arb_seg['LOCATION_ID']==cLocID) & (arb_seg['ALTITUDE']==cLocAlt) & (arb_seg['TYPE']==cLocType)  ]
            cARTCC=getattr(  self, cLocID)
            cARTCC.addboundary(cLocType, cLocAlt,tmpDF['LONG_DECIMAL'],tmpDF['LAT_DECIMAL'])

    def getARTCC(self,artcc):
        if artcc in self.centers:
            return getattr(  self, artcc)
        else:
            print('Cannot find center %s'%artcc)
            print('Select from one of the following:%s'%(','.join(self.centers)))
            return None
            
        