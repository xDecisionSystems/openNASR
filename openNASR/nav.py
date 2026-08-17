from types import SimpleNamespace

from .basictypes import Raw
from .exceptions import AmbiguousRecordError, RecordNotFoundError
from .records import FaaRecord, coordinate, nullable_text


class NavaidRecord(FaaRecord):
    """Typed conveniences over a lossless navaid source row."""

    def _text(self, *columns: str) -> str | None:
        for column in columns:
            value = self._raw.get(column)
            if value is not None and value == value:
                return nullable_text(str(value))
        return None

    @property
    def identifier(self) -> str | None:
        return self._text("NAV_ID")

    @property
    def nav_type(self) -> str | None:
        return self._text("NAV_TYPE")

    @property
    def name(self) -> str | None:
        return self._text("NAME")

    @property
    def state(self) -> str | None:
        return self._text("STATE_CODE")

    @property
    def country(self) -> str | None:
        return self._text("COUNTRY_CODE", "COUNTRY_NAME")

    @property
    def high_artcc(self) -> str | None:
        return self._text("HIGH_ALT_ARTCC_ID")

    @property
    def low_artcc(self) -> str | None:
        return self._text("LOW_ALT_ARTCC_ID")

    @property
    def frequency(self) -> str | None:
        return self._text("FREQ")

    @property
    def latitude(self) -> float | None:
        value = self._text("LAT_DECIMAL")
        return None if value is None else coordinate(value)

    @property
    def longitude(self) -> float | None:
        value = self._text("LONG_DECIMAL")
        return None if value is None else coordinate(value)


class NAVAID(Raw):
    def __init__(
        self,
        navaid,
        NASR,
        inCenter=None,
        inState=None,
        inCountry=None,
        navType=None,
        *,
        nav_type=None,
    ):
        # If there are two NAVAIDs with the same name the first one will be selected
        # unless the state or type is provided.
        if NASR.isNavaid(navaid):
            if nav_type is not None:
                if navType is not None and navType != nav_type:
                    raise ValueError(
                        "navType and nav_type must agree when both are supplied"
                    )
                navType = nav_type
            self._addBASE(navaid, NASR, inCenter, inState, inCountry, navType)
        else:
            raise RecordNotFoundError(entity_type="Navaid", identifier=navaid)

    def _addBASE(
        self,
        navaid,
        nasr,
        inCenter=None,
        inState=None,
        inCountry=None,
        navType=None,
    ):
        if hasattr(nasr, "_legacy_normalized_rows"):
            NAV_BASE = nasr["NAV_BASE"]
            navRecs = nasr._legacy_normalized_rows("NAV_BASE", "NAV_ID", navaid)
        else:
            NAV_BASE = nasr["NAV_BASE"] if "NAV_BASE" in nasr else nasr
            navRecs = NAV_BASE[
                NAV_BASE["NAV_ID"].map(lambda value: str(value).strip().upper())
                == str(navaid).strip().upper()
            ]
        filters = {}
        if inCenter is not None:
            navCenterBool = (navRecs["HIGH_ALT_ARTCC_ID"] == inCenter) | (
                navRecs["LOW_ALT_ARTCC_ID"] == inCenter
            )
            navRecs = navRecs[navCenterBool]
            filters["in_center"] = inCenter
        if inState is not None:
            navRecs = navRecs[navRecs["STATE_CODE"] == inState]
            filters["in_state"] = inState
        if inCountry is not None:
            navRecs = navRecs[navRecs["COUNTRY_CODE"] == inCountry]
            filters["in_country"] = inCountry
        if navType is not None:
            navRecs = navRecs[navRecs["NAV_TYPE"] == navType]
            filters["nav_type"] = navType
        if len(navRecs) > 1:
            raise AmbiguousRecordError(
                entity_type="Navaid",
                identifier=navaid,
                filters=filters,
                candidates=navRecs.to_dict(orient="records"),
            )
        elif len(navRecs) == 1:
            super().__init__(SimpleNamespace(**navRecs.to_dict(orient="records")[0]))
        else:
            raise RecordNotFoundError(
                entity_type="Navaid", identifier=navaid, filters=filters
            )

    # @property
    # def lat(self):
    #     return self.base.LAT_DECIMAL

    # @property
    # def lon(self):
    #     return self.base.LONG_DECIMAL
