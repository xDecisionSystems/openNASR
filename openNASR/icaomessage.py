"""Extract the route from an ICAO flight-plan message.

Only the fields route resolution needs are read: the departure aerodrome
(field 13), the route (field 15) and the destination aerodrome (field 16).
The cruise speed and level that open field 15 are not geometry and are
dropped. Everything extracted is returned so a caller can check it.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_AERODROME = re.compile(r"^[A-Z]{4}$")
_SPEED_LEVEL = re.compile(r"^[NKM]\d{3,4}(?:[FSAM]\d{3,4}|VFR)$")


class IcaoMessageError(ValueError):
    """Raised when a message is not a usable ICAO flight plan."""


@dataclass(frozen=True)
class IcaoFlightPlan:
    message_type: str
    aircraft_id: str
    departure: str
    destination: str
    route_field: str
    """Field 15 as filed, including the opening speed/level group."""
    route: str
    """What is resolved: departure, the route without its opening group, destination."""


def parse_icao_flight_plan(message: str) -> IcaoFlightPlan:
    text = message.strip()
    if not text:
        raise IcaoMessageError("the message is empty")
    text = text.removeprefix("(").removesuffix(")")
    fields = [part.strip() for part in text.split("-")]
    if fields[0].upper() != "FPL":
        raise IcaoMessageError("only FPL messages are supported (expected '(FPL-...')")
    # FPL, 7 id, 8 rules/type, 9 aircraft, 10 equipment, 13 departure,
    # 15 route, 16 destination, then 18 and beyond.
    if len(fields) < 8:
        raise IcaoMessageError(
            "an FPL needs at least fields 7 to 16 (aircraft id through destination)"
        )
    aircraft_id = fields[1].upper()
    departure = fields[5][:4].upper()
    route_field = " ".join(fields[6].upper().split())
    destination = fields[7][:4].upper()
    for name, code in (("departure", departure), ("destination", destination)):
        if not _AERODROME.match(code):
            raise IcaoMessageError(
                f"the {name} aerodrome {code!r} is not a four-letter ICAO location"
            )
    if not route_field:
        raise IcaoMessageError("field 15 (route) is empty")
    parts = route_field.split()
    if _SPEED_LEVEL.match(parts[0].split("/")[0]):
        parts = parts[1:]
    if not parts:
        raise IcaoMessageError("field 15 has a speed and level but no route")
    return IcaoFlightPlan(
        message_type="FPL",
        aircraft_id=aircraft_id,
        departure=departure,
        destination=destination,
        route_field=route_field,
        route=" ".join([departure, *parts, destination]),
    )
