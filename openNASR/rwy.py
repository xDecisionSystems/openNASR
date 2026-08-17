from .basictypes import Raw, RawDict
from .records import FaaRecord


class RunwayRecord(FaaRecord):
    """Lossless typed marker for an airport runway row."""


class RunwayEndRecord(FaaRecord):
    """Lossless typed marker for an airport runway-end row."""


# ---------------------------------------
# ---------------------------------------
class RWYEnditem(Raw):
    @property
    def bearing(self):
        if hasattr(self._raw, "TRUE_ALIGNMENT"):
            return self._raw.TRUE_ALIGNMENT
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
