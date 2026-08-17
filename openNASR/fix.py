from types import SimpleNamespace

from .basictypes import Raw
from .exceptions import RecordNotFoundError
from .records import FaaRecord, coordinate, nullable_text


class FixRecord(FaaRecord):
    """Fix record with nullable typed conveniences over lossless FAA fields."""

    def _text_from(self, *columns: str) -> str | None:
        for column in columns:
            if column in self._raw:
                value = self._raw[column]
                if value is None or value != value:
                    return None
                return nullable_text(str(value))
        return None

    @property
    def identifier(self) -> str | None:
        return self._text_from("FIX_ID")

    @property
    def name(self) -> str | None:
        return self._text_from("FIX_NAME", "NAME")

    @property
    def latitude(self) -> float | None:
        value = self._text_from("LAT_DECIMAL")
        return None if value is None else coordinate(value)

    @property
    def longitude(self) -> float | None:
        value = self._text_from("LONG_DECIMAL")
        return None if value is None else coordinate(value)

    @property
    def state(self) -> str | None:
        return self._text_from("STATE_CODE", "STATE")

    @property
    def country(self) -> str | None:
        return self._text_from("COUNTRY_CODE", "COUNTRY_NAME")

    @property
    def high_artcc(self) -> str | None:
        return self._text_from("ARTCC_ID_HIGH")

    @property
    def low_artcc(self) -> str | None:
        return self._text_from("ARTCC_ID_LOW")


class FIX(Raw):
    def __init__(self, fix, NASR):
        if NASR.isFix(fix):
            self._addBASE(fix, NASR["FIX_BASE"])
        else:
            raise RecordNotFoundError(entity_type="Fix", identifier=fix)

    def _addBASE(self, fix, FIX_BASE):
        normalized_fix = str(fix).strip().upper()
        matches = FIX_BASE["FIX_ID"].map(lambda value: str(value).strip().upper()) == (
            normalized_fix
        )
        super().__init__(
            SimpleNamespace(**FIX_BASE[matches].to_dict(orient="records")[0])
        )
