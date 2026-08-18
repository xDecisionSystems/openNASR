from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pandas import DataFrame

from .basictypes import Raw, RawDict
from .records import FaaRecord


class RunwayRecord(FaaRecord):
    """Lossless airport runway row with a plotting convenience."""

    def plot(
        self,
        nasr: Mapping[str, DataFrame],
        *,
        axes: Any | None = None,
        project_to_nm: bool = False,
        projection_center: tuple[float, float] | None = None,
        projection: Literal["geographic", "nautical_miles", "web_mercator"]
        | None = None,
        plot_legend: bool = True,
        index: Any | None = None,
    ) -> tuple[Any, Any]:
        """Plot this runway between its two surveyed threshold coordinates."""

        from .plotting import plot_runway

        return plot_runway(
            nasr,
            self,
            axes=axes,
            project_to_nm=project_to_nm,
            projection_center=projection_center,
            projection=projection,
            plot_legend=plot_legend,
            index=index,
        )


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
