"""The HTTP application."""

from __future__ import annotations

from collections.abc import Collection
import hmac
import re
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from openNASR.exceptions import ConfigurationError
from openNASR.icaomessage import IcaoFlightPlan, IcaoMessageError
from openNASR.routeresult import RouteResult

from .store import CycleStore, CycleUnavailableError

API_VERSION = "0.1.0"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RouteRequest(BaseModel):
    route: str | None = Field(
        default=None, max_length=4096, description="FAA route text"
    )
    icao_message: str | None = Field(
        default=None,
        max_length=8192,
        description="An ICAO FPL message; the route and aerodromes are extracted",
    )
    cycle: str | None = Field(
        default=None, description="Effective date YYYY-MM-DD; default is today's cycle"
    )

    @model_validator(mode="after")
    def _exactly_one_input(self) -> "RouteRequest":
        given = [v for v in (self.route, self.icao_message) if v and v.strip()]
        if len(given) != 1:
            raise ValueError("give exactly one of 'route' or 'icao_message'")
        return self

    @field_validator("cycle")
    @classmethod
    def _date(cls, value: str | None) -> str | None:
        if value is not None and not _DATE.match(value):
            raise ValueError("cycle must be YYYY-MM-DD")
        return value


class Point(BaseModel):
    lat: float
    lon: float
    name: str
    kind: str
    via: str | None
    segment: str


class Diagnostic(BaseModel):
    code: str
    severity: str
    message: str
    token: str | None
    position: int | None
    detail: dict[str, Any]


class Extracted(BaseModel):
    message_type: str
    aircraft_id: str
    departure: str
    destination: str
    route_field: str


class InputEcho(BaseModel):
    mode: str  # "route" | "icao_message"
    extracted: Extracted | None = None


class RouteResponse(BaseModel):
    input: InputEcho
    route: str
    cycle: str | None
    complete: bool
    points: list[Point]
    geojson: dict[str, Any]
    diagnostics: list[Diagnostic]


def _geojson(result: RouteResult) -> dict[str, Any]:
    coordinates = [[p.lon, p.lat] for p in result.waypoints]  # GeoJSON is lon, lat
    geometry = (
        {"type": "LineString", "coordinates": coordinates}
        if len(coordinates) >= 2
        else None
    )
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "route": result.route,
            "cycle": result.cycle,
            "complete": result.complete,
        },
    }


def _response(
    result: RouteResult, extracted: IcaoFlightPlan | None = None
) -> RouteResponse:
    return RouteResponse(
        input=InputEcho(
            mode="icao_message" if extracted else "route",
            extracted=Extracted(
                message_type=extracted.message_type,
                aircraft_id=extracted.aircraft_id,
                departure=extracted.departure,
                destination=extracted.destination,
                route_field=extracted.route_field,
            )
            if extracted
            else None,
        ),
        route=result.route,
        cycle=result.cycle,
        complete=result.complete,
        points=[Point(**vars(p)) for p in result.waypoints],
        geojson=_geojson(result),
        diagnostics=[
            Diagnostic(
                code=d.code,
                severity=d.severity,
                message=d.message,
                token=d.token,
                position=d.position,
                detail=d.detail,
            )
            for d in result.diagnostics
        ],
    )


def create_app(store: CycleStore, api_keys: Collection[str]) -> FastAPI:
    """Build the app. ``api_keys`` are the accepted ``X-API-Key`` values."""

    keys = tuple(key.encode() for key in api_keys if key)
    app = FastAPI(title="openNASR API", version=API_VERSION)

    def require_key(
        x_api_key: Annotated[str | None, Header()] = None,
        authorization: Annotated[str | None, Header()] = None,
    ) -> None:
        supplied = x_api_key
        if supplied is None and authorization and authorization.startswith("Bearer "):
            supplied = authorization[7:]
        if supplied is None or not any(
            hmac.compare_digest(supplied.encode(), key) for key in keys
        ):
            raise HTTPException(401, "a valid API key is required")

    def resolve(
        route: str | None, cycle: str | None, icao_message: str | None = None
    ) -> RouteResponse:
        try:
            chosen, resolver = store.resolver(cycle)
        except CycleUnavailableError as error:
            status = 404 if cycle else 503
            raise HTTPException(status, str(error)) from error
        try:
            if icao_message and icao_message.strip():
                try:
                    extracted, result = resolver.resolve_icao_message(icao_message)
                except IcaoMessageError as error:
                    raise HTTPException(422, str(error)) from error
                return _response(result, extracted)
            assert route is not None
            return _response(resolver.resolve(route))
        except ConfigurationError as error:
            raise HTTPException(
                500, f"cycle {chosen} cannot be used: {error}"
            ) from error

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION}

    @app.get("/ready")
    def ready() -> dict[str, Any]:
        try:
            default = store.default_cycle()
        except CycleUnavailableError as error:
            raise HTTPException(503, str(error)) from error
        return {"status": "ready", "default_cycle": default}

    @app.post(
        "/v1/route/resolve",
        response_model=RouteResponse,
        dependencies=[Depends(require_key)],
    )
    def resolve_post(request: RouteRequest) -> RouteResponse:
        return resolve(request.route, request.cycle, request.icao_message)

    @app.get(
        "/v1/route/resolve",
        response_model=RouteResponse,
        dependencies=[Depends(require_key)],
    )
    def resolve_get(
        route: Annotated[str, Query(min_length=1, max_length=4096)],
        cycle: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    ) -> RouteResponse:
        if not route.strip():
            raise HTTPException(422, "route must not be blank")
        return resolve(route, cycle)

    @app.get("/v1/cycles", dependencies=[Depends(require_key)])
    def cycles() -> dict[str, Any]:
        rows = store.describe()
        try:
            default = store.default_cycle()
        except CycleUnavailableError:
            default = None
        return {"default": default, "cycles": rows}

    return app
