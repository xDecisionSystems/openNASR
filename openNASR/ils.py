from __future__ import annotations

from collections.abc import Mapping
from math import cos, isfinite, pi, radians, sin, tan
from typing import Any, Literal

from pandas import DataFrame

from .basictypes import Raw, RawDict
from .records import FaaRecord


FEET_PER_NAUTICAL_MILE = 6076.12
LOCALIZER_THRESHOLD_WIDTH_FT = 700.0
LOCALIZER_HALF_ANGLE_DEG = 2.5
DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM = 20.0


def localizer_wedge_xy(
    threshold_x: float,
    threshold_y: float,
    true_approach_bearing: float,
    *,
    distance_nm: float = DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return a standard localizer wedge in east/north nautical miles.

    The narrow end is 700 feet wide at the runway threshold. Each side then
    expands by 2.5 degrees away from the inbound course centerline for
    ``distance_nm`` into the approach area.
    """

    distance = float(distance_nm)
    if distance <= 0:
        raise ValueError("localizer wedge distance_nm must be greater than zero")
    bearing = float(true_approach_bearing)
    if not isfinite(distance) or not isfinite(bearing):
        raise ValueError("localizer wedge distance and bearing must be finite")

    outbound = radians((bearing + 180.0) % 360.0)
    direction_x, direction_y = sin(outbound), cos(outbound)
    perpendicular_x, perpendicular_y = direction_y, -direction_x
    threshold_half_width = LOCALIZER_THRESHOLD_WIDTH_FT / (2.0 * FEET_PER_NAUTICAL_MILE)
    far_half_width = threshold_half_width + distance * tan(
        radians(LOCALIZER_HALF_ANGLE_DEG)
    )
    far_x = float(threshold_x) + distance * direction_x
    far_y = float(threshold_y) + distance * direction_y

    x_values = (
        float(threshold_x) + threshold_half_width * perpendicular_x,
        far_x + far_half_width * perpendicular_x,
        far_x - far_half_width * perpendicular_x,
        float(threshold_x) - threshold_half_width * perpendicular_x,
    )
    y_values = (
        float(threshold_y) + threshold_half_width * perpendicular_y,
        far_y + far_half_width * perpendicular_y,
        far_y - far_half_width * perpendicular_y,
        float(threshold_y) - threshold_half_width * perpendicular_y,
    )
    return x_values, y_values


class IlsRecord(FaaRecord):
    """Lossless airport ILS row with a localizer plotting convenience."""

    def plot(
        self,
        nasr: Mapping[str, DataFrame],
        *,
        axes: Any | None = None,
        side_axes: Any | None = None,
        plot_wedge: bool = True,
        wedge_distance_nm: float = DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM,
        plot_glide_slope: bool = True,
        glide_slope_distance_nm: float = 15.0,
        project_to_nm: bool = False,
        projection_center: tuple[float, float] | None = None,
        projection: Literal["geographic", "nautical_miles", "web_mercator"]
        | None = None,
        basemap: Literal["usgs_imagery"] | None = None,
        kilometers: bool = False,
        plot_legend: bool = True,
        index: Any | None = None,
    ) -> tuple[Any, Any]:
        """Plot this localizer and optionally its standard course wedge.

        ``plot_wedge=True`` draws the localizer course 700 feet wide at the
        runway threshold, expanding at a 2.5-degree half-angle.
        ``wedge_distance_nm`` controls its distance into the approach area and
        defaults to 20 NM. Supply ``side_axes`` to add the runway elevation
        profile and FAA-published glide-slope angle; the top view also includes
        the surveyed glide-slope site when available. Projection, axes, legend,
        and reusable plotting index options match the other modern methods.
        """

        from .plotting import plot_ils_localizer

        return plot_ils_localizer(
            nasr,
            self,
            axes=axes,
            side_axes=side_axes,
            plot_wedge=plot_wedge,
            wedge_distance_nm=wedge_distance_nm,
            plot_glide_slope=plot_glide_slope,
            glide_slope_distance_nm=glide_slope_distance_nm,
            project_to_nm=project_to_nm,
            projection_center=projection_center,
            projection=projection,
            basemap=basemap,
            kilometers=kilometers,
            plot_legend=plot_legend,
            index=index,
        )


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

    def _estimated_threshold_xy(self, latc, lonc):
        """Estimate threshold position when no surveyed runway end is supplied."""

        x0, y0 = self.xy(latc, lonc)
        runway_length_nm = float(getattr(self._raw, "RWY_LEN", 0.0) or 0.0) / (
            FEET_PER_NAUTICAL_MILE
        )
        outbound = radians((self.trueBearing + 180.0) % 360.0)
        return (
            x0 + runway_length_nm * sin(outbound),
            y0 + runway_length_nm * cos(outbound),
        )

    def plot(
        self,
        ax,
        latc,
        lonc,
        pltILSBnd=False,
        *,
        plot_wedge: bool | None = None,
        wedge_distance_nm: float = DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM,
        threshold_xy: tuple[float, float] | None = None,
    ):
        x0, y0 = self.xy(latc, lonc)
        ax.scatter(x0, y0, color="blue", marker="h")

        ang = self.trueAngle
        dx = -cos(ang * pi / 180)
        dy = -sin(ang * pi / 180)
        ax.arrow(x0, y0, dx, dy, color="red")

        wedge_enabled = pltILSBnd if plot_wedge is None else plot_wedge
        if wedge_enabled:
            threshold_x, threshold_y = threshold_xy or self._estimated_threshold_xy(
                latc, lonc
            )
            xs, ys = localizer_wedge_xy(
                threshold_x,
                threshold_y,
                self.trueBearing,
                distance_nm=wedge_distance_nm,
            )
            self.pWedge = ax.fill(xs, ys, color="silver", alpha=0.3)

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
    def plot(
        self,
        ax,
        lonc,
        latc,
        pltILSBnd=False,
        *,
        plot_wedge: bool | None = None,
        wedge_distance_nm: float = DEFAULT_LOCALIZER_WEDGE_DISTANCE_NM,
        threshold_coordinates: Mapping[str, tuple[float, float]] | None = None,
    ):
        for cID in self.ids:
            self[cID].plot(
                ax,
                lonc,
                latc,
                pltILSBnd=pltILSBnd,
                plot_wedge=plot_wedge,
                wedge_distance_nm=wedge_distance_nm,
                threshold_xy=(threshold_coordinates or {}).get(cID),
            )


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
