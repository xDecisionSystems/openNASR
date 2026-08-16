from types import SimpleNamespace
from .exceptions import RecordNotFoundError


class Departure(object):
    def __init__(self, departure,NASR):
        if NASR.isDeparture(departure):
            self._addBASE(departure,NASR['DP_BASE'])
            self._addROUTE(departure,NASR['DP_RTE'])

        else:
            raise RecordNotFoundError(entity_type="Departure", identifier=departure)

    def _addBASE(self,departure,DP_BASE):
        self.base = SimpleNamespace( **DP_BASE[DP_BASE['DP_COMPUTER_CODE'].apply(lambda dpCode: dpCode.split('.')[0])==departure].to_dict(orient='records')[0] )

    def _addROUTE(self,departure,DP_RTE):
        self.route = SimpleNamespace( **DP_RTE[DP_RTE['DP_COMPUTER_CODE'].apply(lambda dpCode: dpCode.split('.')[0])==departure].to_dict(orient='records')[0] )
