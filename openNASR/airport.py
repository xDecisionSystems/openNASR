from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .basictypes import Raw, getAirportRecord
from .ils import ILSBase, ILSitem, ILSDME, DMEitem, ILSGS, GSitem, ILSMKR, MKRitem
from .rwy import RWY, RWYitem, RWYEnd, RWYEnditem
from .exceptions import RecordNotFoundError
from .records import (
    DmeRecord,
    FaaRecord,
    FieldContext,
    GlideSlopeRecord,
    IlsRecord,
    MarkerRecord,
    RunwayEndRecord,
    RunwayRecord,
    coordinate,
    float_value,
    nullable_text,
)

# import wmm2020
from shapely.geometry import LineString

if TYPE_CHECKING:
    from .airspace import ClassAirspace
    from .military import MilitaryOperation


class AirportRecord(FaaRecord):
    """Airport record with nullable typed conveniences over lossless FAA fields."""

    def __init__(
        self,
        raw: Mapping[str, object],
        *,
        runways: tuple[RunwayRecord, ...] = (),
        runway_ends: tuple[RunwayEndRecord, ...] = (),
        ils: tuple[IlsRecord, ...] = (),
        dmes: tuple[DmeRecord, ...] = (),
        glide_slopes: tuple[GlideSlopeRecord, ...] = (),
        markers: tuple[MarkerRecord, ...] = (),
        class_airspace: ClassAirspace | None = None,
        military_operations: tuple[MilitaryOperation, ...] = (),
    ) -> None:
        super().__init__(raw)
        self._runways = runways
        self._runway_ends = runway_ends
        self._ils = ils
        self._dmes = dmes
        self._glide_slopes = glide_slopes
        self._markers = markers
        self._class_airspace = class_airspace
        self._military_operations = military_operations

    @property
    def runways(self) -> tuple[RunwayRecord, ...]:
        return self._runways

    @property
    def runway_ends(self) -> tuple[RunwayEndRecord, ...]:
        return self._runway_ends

    @property
    def ils(self) -> tuple[IlsRecord, ...]:
        return self._ils

    @property
    def dmes(self) -> tuple[DmeRecord, ...]:
        return self._dmes

    @property
    def glide_slopes(self) -> tuple[GlideSlopeRecord, ...]:
        return self._glide_slopes

    @property
    def markers(self) -> tuple[MarkerRecord, ...]:
        return self._markers

    @property
    def class_airspace(self) -> ClassAirspace | None:
        return self._class_airspace

    @property
    def military_operations(self) -> tuple[MilitaryOperation, ...]:
        return self._military_operations

    def _field_context(self, column: str) -> FieldContext:
        return FieldContext(
            table="APT_BASE", column=column, record_identity=self._raw.get("ARPT_ID")
        )

    def _text(self, column: str) -> str | None:
        value = self._raw.get(column)
        return None if value is None else nullable_text(str(value))

    @property
    def faa_id(self) -> str | None:
        return self._text("ARPT_ID")

    @property
    def icao_id(self) -> str | None:
        return self._text("ICAO_ID")

    @property
    def name(self) -> str | None:
        return self._text("ARPT_NAME")

    @property
    def latitude(self) -> float | None:
        value = self._raw.get("LAT_DECIMAL")
        return (
            None
            if value is None
            else coordinate(str(value), context=self._field_context("LAT_DECIMAL"))
        )

    @property
    def longitude(self) -> float | None:
        value = self._raw.get("LONG_DECIMAL")
        return (
            None
            if value is None
            else coordinate(str(value), context=self._field_context("LONG_DECIMAL"))
        )

    @property
    def elevation_ft(self) -> float | None:
        value = self._raw.get("ELEV")
        return (
            None
            if value is None
            else float_value(str(value), context=self._field_context("ELEV"))
        )


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
