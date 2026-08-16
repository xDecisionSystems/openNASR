from .basictypes import Raw, RawDict   
from .cfcn import ll2xy   
from math import pi, cos, sin, radians

class ILSitem(Raw):
    def category(self):
        if hasattr(self._raw,'CATEGORY'):
            return self._raw.CATEGORY
        else:
            return None

    @property            
    def trueBearing(self):
        magBearing=self.magBearing
        # magVar=self.decl
        magVar=self.magVar

        if (magBearing is not None) and (magVar is not None):
            return magBearing+magVar
        else:
            return None

    @property            
    def trueAngle(self):
        return 90-self.trueBearing

    @property            
    def magBearing(self):
        if hasattr(self._raw,'APCH_BEAR'):
            return self._raw.APCH_BEAR
        else:
            return None

    @property            
    def magVar(self):
        if hasattr(self._raw,'MAG_VAR'):
            if self._raw.MAG_VAR_HEMIS =='E':
                return self._raw.MAG_VAR
            else:
                return -self._raw.MAG_VAR
        else:
            return None

    def calcBnd(self,latc,lonc,distance,halfWdith):
        x0,y0=self.xy(latc,lonc)
        xL=x0-distance*cos(radians(self.trueAngle+halfWdith))
        yL=y0-distance*sin(radians(self.trueAngle+halfWdith))

        xR=x0-distance*cos(radians(self.trueAngle-halfWdith))
        yR=y0-distance*sin(radians(self.trueAngle-halfWdith))
        return [x0,xL,xR],[y0,yL,yR] 

        
    def plot(self,ax,latc,lonc,pltILSBnd=False):
        x0,y0=self.xy(latc,lonc)
        ax.scatter(x0,y0,color='blue',marker='h')
        
        ang = self.trueAngle
        dx=-cos(ang*pi/180)
        dy=-sin(ang*pi/180)    
        ax.arrow(x0,y0, dx, dy, color='red')
        
        if pltILSBnd: self.plotShortBnd(ax, latc, lonc)
        if pltILSBnd: self.plotLongBnd(ax, latc, lonc)
        

    def pltBnd(self,ax,latc,lonc,distance,halfWdith):
        xs,ys = self.calcBnd(latc, lonc, distance,halfWdith)
        return ax.fill(xs,ys,color='silver',alpha=.3)

        
    def plotShortBnd(self,ax,latc,lonc, distance=10,halfWdith=35):
        self.pShort = self.pltBnd(ax, latc, lonc, distance=distance, halfWdith=halfWdith)

    def plotLongBnd(self,ax,latc,lonc, distance=18,halfWdith=5):
        self.pLong = self.pltBnd(ax, latc, lonc, distance=distance, halfWdith=halfWdith)

      

class ILSBase(RawDict):
    def plot(self,ax,lonc,latc,pltILSBnd=False):
        for cID in self.ids:
            self[cID].plot(ax,lonc,latc,pltILSBnd=pltILSBnd)
            
    def setDecl(self,decl):
        for cID in self.ids:
            self[cID].decl=decl
            
# --------------------------------------- 
# --------------------------------------- 
class DMEitem(Raw):
    pass
     
class ILSDME(RawDict): 
    pass
# --------------------------------------- 
# --------------------------------------- 
class GSitem(Raw):
    @property            
    def angle(self):
        if hasattr(self._raw,'G_S_ANGLE'):
            return self._raw.G_S_ANGLE
        else:
            return None

    def plot(self,ax,latc,lonc,rwyTrueAngle=None):
        x0,y0=self.xy(latc,lonc)
        ax.scatter(x0,y0,color='blue',marker='x')
        
        # ang = self.trueAngle
        # dx=-cos(ang*pi/180)
        # dy=-sin(ang*pi/180)    
        # ax.quiver(x0,y0, dx, dy, scale=4,color='red')

class ILSGS(RawDict):
    def plot(self,ax,lonc,latc):
        for cID in self.ids:
            self[cID].plot(ax,lonc,latc)

# --------------------------------------- 
# --------------------------------------- 
class MKRitem(Raw):
    pass

class ILSMKR(RawDict): 
    pass