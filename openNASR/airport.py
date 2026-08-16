from .basictypes import Raw, getAirportRecord
from .ils import ILSBase, ILSitem, ILSDME, DMEitem, ILSGS, GSitem, ILSMKR, MKRitem
from .rwy import RWY, RWYitem, RWYEnd, RWYEnditem
from .exceptions import RecordNotFoundError

# import wmm2020
from shapely.geometry import LineString


class AirportBase(Raw):
    def __init__(self, airport, nasrDF, airportIDCol):
        super().__init__(getAirportRecord(airport, nasrDF, airportIDCol))

    @property
    def elevation(self):
        return self._raw.ELEV

    @property
    def icao_id(self):
        return self._raw.ICAO_ID

    @property
    def faa_id(self):
        return self._raw.ARPT_ID


class Airport:
    def __init__(self, airport, nasr):
        isAirport, airportIDCol, airport = nasr.isAirport(airport, forceFAA=True)
        if isAirport:
            self.base = AirportBase(airport, nasr["APT_BASE"], airportIDCol)
            # self.decl = wmm2020.wmm_point(self.lat,self.lon, self.elevation,NASR.yearDecimal)['decl']
            self.rwy = RWY(
                RWYitem, airport, nasr["APT_RWY"], airportIDCol, useRWYID=True
            )
            self.ils = ILSBase(ILSitem, airport, nasr["ILS_BASE"], airportIDCol)
            # self.ils.setDecl(self.decl)
            self.dme = ILSDME(DMEitem, airport, nasr["ILS_DME"], airportIDCol)
            self.gs = ILSGS(GSitem, airport, nasr["ILS_GS"], airportIDCol)
            marker_table = nasr.get("ILS_MKR", nasr["ILS_BASE"].iloc[0:0])
            self.mkr = ILSMKR(MKRitem, airport, marker_table, airportIDCol)
            self.rwyend = RWYEnd(RWYEnditem, airport, nasr["APT_RWY_END"], airportIDCol)
            self.makeRWYbnds()

        else:
            raise RecordNotFoundError(entity_type="Airport", identifier=airport)

    @property
    def elevation(self):
        return self.base.elevation

    @property
    def lat(self):
        return self.base.lat

    @property
    def lon(self):
        return self.base.lon

    @property
    def icao_id(self):
        return self.base.icao_id

    @property
    def faa_id(self):
        return self.base.faa_id

    def plot(self, closeFigs=False, pltILSBnd=False):
        from matplotlib import pyplot as plt

        if closeFigs:
            plt.close("all")
        self.fig, self.ax = plt.subplots()
        self.plotRWY()
        self.ils.plot(self.ax, self.lat, self.lon, pltILSBnd=pltILSBnd)
        self.gs.plot(self.ax, self.lat, self.lon)
        self.ax.set_title(self.icao_id)
        self.ax.set_aspect("equal")
        return self.fig, self.ax

    def makeRWYbnds(self):
        for cRWY in self.rwy.ids:
            rwyEnds = cRWY.split("/")
            if len(rwyEnds) == 2:
                x0, y0 = self.rwyend[rwyEnds[0]].xy(self.lat, self.lon)
                x1, y1 = self.rwyend[rwyEnds[1]].xy(self.lat, self.lon)
                self.rwy[cRWY].bnds = makeRWYpoly(
                    [x0, y0], [x1, y1], width=self.rwy[cRWY].width
                )

    def plotRWY(self):
        for cRWY in self.rwy.ids:
            rwyEnds = cRWY.split("/")
            if len(rwyEnds) == 2:
                x0, y0 = self.rwyend[rwyEnds[0]].xy(self.lat, self.lon)
                x1, y1 = self.rwyend[rwyEnds[1]].xy(self.lat, self.lon)
                xp, yp = self.rwy[cRWY].RWYbndXY
                self.ax.fill(xp, yp, alpha=0.5, fc="black", edgecolor="black")

    def removePlt(self, lineRef):
        line = lineRef.pop(0)
        line.remove()
        self.fig.canvas.flush_events()


def makeRWYpoly(xy_start, xy_end, width):
    # Create a LineString from the start and end points
    line = LineString([xy_start, xy_end])

    # Create a buffered polygon around the line
    polygon = line.buffer(width / 6076.1 / 2)  # Buffering by half the width

    # return polygon.exterior.xy
    return polygon

    # x,y=self.xy
    # axs.scatter(x,y,color='blue',marker='x')
