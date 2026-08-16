from .basictypes import Raw, RawDict


# ---------------------------------------
# ---------------------------------------
class RWYEnditem(Raw):
    @property
    def bearing(self, id):
        if hasattr(self._raw, "TRUE_ALIGNMENT"):
            return self._raw.TRUE_ALIGNMENT
        else:
            return None

    @property
    def glidepath(self, id):
        if hasattr(self._raw, "VISUAL_GLIDE_PATH_ANGLE"):
            return self._raw.VISUAL_GLIDE_PATH_ANGLE
        else:
            return None

    @property
    def id(self):
        return self._raw.RWY_END_ID

    @property
    def rwy(self):
        return self._raw.RWY_ID

    @property
    def trueBearing(self):
        return self._raw.TRUE_ALIGNMENT

    @property
    def trueAngle(self):
        return 90 - self._raw.TRUE_ALIGNMENT


class RWYEnd(RawDict):
    pass


# ---------------------------------------
# ---------------------------------------


class RWYitem(Raw):
    @property
    def rwyType(self):
        return self._raw.SITE_TYPE_CODE

    @property
    def trueBearing(self):
        return self._raw.TRUE_ALIGNMENT

    @property
    def trueAngle(self):
        return 90 - self._raw.TRUE_ALIGNMENT

    @property
    def width(self):
        return self._raw.RWY_WIDTH

    @property
    def length(self):
        return self._raw.RWY_LEN

    @property
    def RWYbndXY(self):
        return self.bnds.exterior.xy


class RWY(RawDict):
    pass
    # def __init__(self,airport,nasrDF,airportIDCol):
    #     super().__init__(airport,nasrDF,airportIDCol, useRWYID=True)
    #     self._map_ends=dict()
    #     for cRWYinfo in [(idx,cRec.RWY_ID.split('/')) for idx,cRec in enumerate(self._raw)]:
    #         for cRWY in cRWYinfo[1]:
    #             self._map_ends[cRWY]=cRWYinfo[0]
