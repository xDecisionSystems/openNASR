from types import SimpleNamespace
from .exceptions import RecordNotFoundError


class Airway(object):
    def __init__(self, airway, NASR):
        if NASR.isAirway(airway):
            self._addBASE(airway, NASR["AWY_BASE"])
        else:
            raise RecordNotFoundError(entity_type="Airway", identifier=airway)

    def _addBASE(self, airway, AWY_BASE):
        self.base = SimpleNamespace(
            **AWY_BASE[AWY_BASE["AWY_ID"] == airway].to_dict(orient="records")[0]
        )

    @property
    def waypts(self):
        return self.base.AIRWAY_STRING.split(" ")
