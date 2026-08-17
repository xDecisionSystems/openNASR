from .basictypes import Raw, RawDict
from math import pi, cos, sin, radians

from .records import FaaRecord


class IlsRecord(FaaRecord):
    """Lossless typed marker for an airport ILS row."""


class DmeRecord(FaaRecord):
    """Lossless typed marker for an airport ILS DME row."""


class GlideSlopeRecord(FaaRecord):
    """Lossless typed marker for an airport ILS glide-slope row."""


class MarkerRecord(FaaRecord):
    """Lossless typed marker for an airport ILS marker row."""

    @property
    def marker_id_beacon(self) -> str | None:
        """The marker's identifier/beacon code (FAA column ``MARKER_ID_BEACON``)."""
        value = self._raw.get("MARKER_ID_BEACON")
        return None if value is None or str(value) == "" else str(value)

    @property
    def compass_locator_name(self) -> str | None:
        """The compass locator name, when the marker doubles as one."""
        value = self._raw.get("COMPASS_LOCATOR_NAME")
        return None if value is None or str(value) == "" else str(value)


class ILSitem(Raw):
    @property
    def trueBearing(self):
        magBearing = self.magBearing
        # magVar=self.decl
        magVar = self.magVar

        if (magBearing is not None) and (magVar is not None):
            return magBearing + magVar
        else:
            return None

    @property
    def trueAngle(self):
        return 90 - self.trueBearing

    @property
    def magBearing(self):
        if hasattr(self._raw, "APCH_BEAR"):
            return self._raw.APCH_BEAR
        else:
            return None

    @property
    def magVar(self):
        if hasattr(self._raw, "MAG_VAR"):
            if self._raw.MAG_VAR_HEMIS == "E":
                return self._raw.MAG_VAR
            else:
                return -self._raw.MAG_VAR
        else:
            return None

    def calcBnd(self, latc, lonc, distance, halfWdith):
        x0, y0 = self.xy(latc, lonc)
        xL = x0 - distance * cos(radians(self.trueAngle + halfWdith))
        yL = y0 - distance * sin(radians(self.trueAngle + halfWdith))

        xR = x0 - distance * cos(radians(self.trueAngle - halfWdith))
        yR = y0 - distance * sin(radians(self.trueAngle - halfWdith))
        return [x0, xL, xR], [y0, yL, yR]

    def plot(self, ax, latc, lonc, pltILSBnd=False):
        x0, y0 = self.xy(latc, lonc)
        ax.scatter(x0, y0, color="blue", marker="h")

        ang = self.trueAngle
        dx = -cos(ang * pi / 180)
        dy = -sin(ang * pi / 180)
        ax.arrow(x0, y0, dx, dy, color="red")

        if pltILSBnd:
            self.plotShortBnd(ax, latc, lonc)
        if pltILSBnd:
            self.plotLongBnd(ax, latc, lonc)

    def pltBnd(self, ax, latc, lonc, distance, halfWdith):
        xs, ys = self.calcBnd(latc, lonc, distance, halfWdith)
        return ax.fill(xs, ys, color="silver", alpha=0.3)

    def plotShortBnd(self, ax, latc, lonc, distance=10, halfWdith=35):
        self.pShort = self.pltBnd(
            ax, latc, lonc, distance=distance, halfWdith=halfWdith
        )

    def plotLongBnd(self, ax, latc, lonc, distance=18, halfWdith=5):
        self.pLong = self.pltBnd(ax, latc, lonc, distance=distance, halfWdith=halfWdith)


class ILSBase(RawDict):
    def plot(self, ax, lonc, latc, pltILSBnd=False):
        for cID in self.ids:
            self[cID].plot(ax, lonc, latc, pltILSBnd=pltILSBnd)


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
        if hasattr(self._raw, "G_S_ANGLE"):
            return self._raw.G_S_ANGLE
        else:
            return None

    def plot(self, ax, latc, lonc):
        x0, y0 = self.xy(latc, lonc)
        ax.scatter(x0, y0, color="blue", marker="x")


class ILSGS(RawDict):
    def plot(self, ax, lonc, latc):
        for cID in self.ids:
            self[cID].plot(ax, lonc, latc)


# ---------------------------------------
# ---------------------------------------
class MKRitem(Raw):
    pass


class ILSMKR(RawDict):
    pass
