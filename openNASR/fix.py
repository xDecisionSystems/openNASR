from types import SimpleNamespace
from .basictypes import Raw
from .exceptions import RecordNotFoundError


class FIX(Raw):
    def __init__(self, fix, NASR):
        if NASR.isFix(fix):
            self._addBASE(fix, NASR["FIX_BASE"])
        else:
            raise RecordNotFoundError(entity_type="Fix", identifier=fix)

    def _addBASE(self, fix, FIX_BASE):
        super().__init__(
            SimpleNamespace(
                **FIX_BASE[FIX_BASE["FIX_ID"] == fix].to_dict(orient="records")[0]
            )
        )
        # self.base = SimpleNamespace( **FIX_BASE[FIX_BASE['FIX_ID']==fix].to_dict(orient='records')[0] )
