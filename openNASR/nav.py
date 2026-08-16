from types import SimpleNamespace
from .basictypes import Raw
from .exceptions import AmbiguousRecordError, RecordNotFoundError

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
                    raise ValueError("navType and nav_type must agree when both are supplied")
                navType = nav_type
            self._addBASE(navaid,NASR['NAV_BASE'],inCenter,inState,inCountry, navType)
        else:
            raise RecordNotFoundError(entity_type="Navaid", identifier=navaid)

    def _addBASE(self,navaid,NAV_BASE,inCenter=None,inState=None,inCountry=None, navType=None):
        navBool = NAV_BASE['NAV_ID']==navaid
        filters = {}
        if inCenter is not None:
            navCenterBool = (NAV_BASE['HIGH_ALT_ARTCC_ID']==inCenter) | (NAV_BASE['LOW_ALT_ARTCC_ID']==inCenter)
            navBool = navBool & navCenterBool
            filters["in_center"] = inCenter
        if inState is not None:
            navBool = navBool & (NAV_BASE['STATE_CODE']==inState)
            filters["in_state"] = inState
        if inCountry is not None:
            navBool = navBool & (NAV_BASE['COUNTRY_NAME']==inCountry)
            filters["in_country"] = inCountry
        if navType is not None:
            navBool = navBool & (NAV_BASE['NAV_TYPE']==navType)
            filters["nav_type"] = navType
        navRecs = NAV_BASE[navBool]
        if len(navRecs)>1:
            raise AmbiguousRecordError(
                entity_type="Navaid",
                identifier=navaid,
                filters=filters,
                candidates=navRecs.to_dict(orient="records"),
            )
        elif len(navRecs)==1:
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
