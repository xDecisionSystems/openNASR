"""The HTTP application."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import asdict
import hashlib
import hmac
import json
import logging
from pathlib import Path
import re
import time
from typing import Annotated, Any, Literal
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from openNASR.exceptions import ConfigurationError
from openNASR.icaomessage import IcaoFlightPlan, IcaoMessageError
from openNASR.routejson import route_result_to_dict
from openNASR.routeresult import RouteResult

from . import lookups
from .airspace import AltitudeLimit
from .limits import RateLimiter
from .map_layers import LayerName
from .store import CycleStore, CycleUnavailableError

API_VERSION = "0.2.23"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
ACCESS_LOG = logging.getLogger("openNASR_api.access")
LOGGER = logging.getLogger("openNASR_api")

CycleParam = Annotated[
    str | None,
    Query(
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Effective date YYYY-MM-DD; default is the cycle in effect today",
    ),
]
MaxSegmentParam = Annotated[
    float | None,
    Query(
        ge=1,
        le=1000,
        description="Insert great-circle points so no leg exceeds this many nm",
    ),
]


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


class Problem(BaseModel):
    detail: str
    request_id: str | None = None


ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": Problem, "description": "Missing or invalid API key"},
    404: {"model": Problem, "description": "Unknown identifier or cycle"},
    422: {"model": Problem, "description": "Invalid input"},
    429: {"model": Problem, "description": "Rate limit exceeded; see Retry-After"},
    503: {"model": Problem, "description": "No cycle is available yet"},
}


class RouteRequest(BaseModel):
    route: str | None = Field(
        default=None,
        max_length=4096,
        description="FAA route text, e.g. 'KABQ.DOOKK3.TXO..KTYR'",
    )
    icao_message: str | None = Field(
        default=None,
        max_length=8192,
        description="An ICAO FPL message; the route and aerodromes are extracted",
    )
    cycle: str | None = Field(
        default=None, description="Effective date YYYY-MM-DD; default is today's cycle"
    )
    max_segment_nm: float | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Opt in to great-circle interpolation between points",
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
    name: str = Field(
        description="The identifier as filed; empty for interpolated points"
    )
    kind: str = Field(description="airport | fix | navaid | latlon | interpolated")
    via: str | None = Field(description="Airway or procedure that produced the point")
    segment: str = Field(
        description="origin | departure | enroute | arrival | destination"
    )


class Diagnostic(BaseModel):
    code: str
    severity: str = Field(
        description="'warning' = something is missing; 'info' = a note"
    )
    message: str
    token: str | None
    position: int | None = Field(description="Offset of the token in the route text")
    detail: dict[str, Any]


class Extracted(BaseModel):
    message_type: str
    aircraft_id: str
    departure: str
    destination: str
    route_field: str


class InputEcho(BaseModel):
    mode: str = Field(description="route | icao_message")
    extracted: Extracted | None = None


class RouteResponse(BaseModel):
    input: InputEcho
    route: str
    cycle: str | None
    complete: bool = Field(description="True when no warning diagnostics were raised")
    points: list[Point]
    geojson: dict[str, Any]
    diagnostics: list[Diagnostic]


class Position(BaseModel):
    lat: float
    lon: float


class Localizer(BaseModel):
    id: str | None
    runway_end: str | None
    position: Position | None
    wedge: list[Position] = Field(
        description="Vertices of the illustrative localizer course wedge"
    )


class AirportEntity(BaseModel):
    id: str | None
    icao_id: str | None
    position: Position | None
    base: dict[str, str]
    runways: list[dict[str, str]]
    runway_ends: list[dict[str, str]]
    localizers: list[Localizer]


class AirportMatch(BaseModel):
    id: str
    name: str
    city: str
    state: str


class AirportSearchResponse(BaseModel):
    cycle: str
    airports: list[AirportMatch]


class AirportResponse(BaseModel):
    cycle: str
    airport: AirportEntity


class FixEntity(BaseModel):
    id: str | None
    position: Position | None
    base: dict[str, str]


class FixesResponse(BaseModel):
    cycle: str
    fixes: list[FixEntity]


class NavaidEntity(FixEntity):
    type: str | None


class NavaidsResponse(BaseModel):
    cycle: str
    navaids: list[NavaidEntity]


class AirwayWaypoint(BaseModel):
    name: str
    position: Position | None
    issue: str | None


class AirwayPlotSegment(BaseModel):
    sequence: str
    start: AirwayWaypoint
    end: AirwayWaypoint | None
    gap: bool


class AirwayEntity(BaseModel):
    id: str
    base: dict[str, str]
    segments: list[dict[str, str]]
    plot_segments: list[AirwayPlotSegment]


class AirwaysResponse(BaseModel):
    cycle: str
    airways: list[AirwayEntity]


class ProcedureWaypoint(BaseModel):
    name: str
    sequence: str
    position: Position | None
    issue: str | None


class ProcedureBranch(BaseModel):
    kind: str
    name: str
    sequence: str
    transition: str
    waypoints: list[ProcedureWaypoint]


class AirportProceduresResponse(BaseModel):
    cycle: str
    branches: list[ProcedureBranch]


class ProcedureEntity(BaseModel):
    id: str
    name: str
    base: dict[str, str]
    airports: list[dict[str, str]]
    points: list[dict[str, str]]
    branches: list[ProcedureBranch]


class ProceduresResponse(BaseModel):
    cycle: str
    procedures: list[ProcedureEntity]


class CycleInfo(BaseModel):
    effective_date: str
    in_effect: bool
    schema_id: str | None
    zip_sha256: str | None


class CyclesResponse(BaseModel):
    default: str | None
    cycles: list[CycleInfo]


class AirspaceRegion(BaseModel):
    id: str = Field(description="FAA location id, e.g. ZAB")
    name: str
    kind: str = Field(description="ARTCC | FIR | CTA | UTA | CTA/FIR | CLASS")
    level: str = Field(description="low | high | unlimited, or empty for CLASS")
    airspace_class: str | None = Field(
        default=None, description="FAA class B, C, D or E"
    )
    local_type: str | None = None
    lower: AltitudeLimit | None = None
    upper: AltitudeLimit | None = None


class ArtccBoundary(BaseModel):
    id: str
    level: str
    rings: list[list[Position]]


class AirspaceBoundariesResponse(BaseModel):
    cycle: str
    boundaries: list[ArtccBoundary]
    centers: dict[str, str] | None = None


class MatchingBoundary(ArtccBoundary):
    kind: str


class AirspaceViewportResponse(BaseModel):
    cycle: str
    boundaries: list[MatchingBoundary]


class AirspaceResponse(BaseModel):
    cycle: str
    position: Position
    regions: list[AirspaceRegion]
    artcc_boundaries: list[ArtccBoundary]
    boundaries: list[MatchingBoundary] | None = None
    not_covered: str


class AirportMapPoint(Position):
    name: str


class AirspaceLayerResponse(BaseModel):
    cycle: str
    points: list[AirportMapPoint]
    lines: list[list[Position]]


class Health(BaseModel):
    status: str
    version: str


class Ready(BaseModel):
    status: str
    default_cycle: str


def _response(
    result: RouteResult,
    extracted: IcaoFlightPlan | None = None,
    max_segment_nm: float | None = None,
) -> RouteResponse:
    try:
        return RouteResponse(**route_result_to_dict(result, extracted, max_segment_nm))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def key_id(key: str) -> str:
    """A short, non-reversible label for logs; the key itself is never logged."""

    return hashlib.sha256(key.encode()).hexdigest()[:8]


def create_app(
    store: CycleStore,
    api_keys: Collection[str],
    *,
    rate_limit_per_minute: int = 120,
    rate_limit_burst: int | None = None,
    limiter: RateLimiter | None = None,
    require_auth: bool = True,
) -> FastAPI:
    """Build the app. ``api_keys`` are the accepted ``X-API-Key`` values."""

    keys = tuple(key.encode() for key in api_keys if key)
    limiter = limiter or RateLimiter(rate_limit_per_minute, rate_limit_burst)
    app = FastAPI(
        title="openNASR API",
        version=API_VERSION,
        description=(
            "Resolve FAA flight-plan routes to latitude/longitude paths using FAA "
            "NASR data, and look up airports, fixes, navaids and airways. Every "
            "response names the NASR cycle it used. Partial results are normal: "
            "check `complete` and `diagnostics`."
        ),
    )
    frontend = Path(__file__).with_name("frontend")
    app.mount("/ui", StaticFiles(directory=frontend), name="ui")

    @app.get("/", include_in_schema=False)
    def explorer() -> HTMLResponse:
        html = (frontend / "index.html").read_text(encoding="utf-8")
        for asset in ("explorer.css", "explorer.js"):
            html = html.replace(f'/ui/{asset}"', f'/ui/{asset}?v={API_VERSION}"')
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _REQUEST_ID.match(supplied) else uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        ACCESS_LOG.info(
            json.dumps(
                {
                    "event": "request",
                    "id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                    "key": getattr(request.state, "key_id", None),
                },
                sort_keys=True,
            )
        )
        return response

    @app.exception_handler(Exception)
    async def unexpected(request: Request, error: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        LOGGER.exception("unhandled error (request %s)", request_id)
        return JSONResponse(
            {"detail": "internal error", "request_id": request_id}, status_code=500
        )

    def require_key(
        request: Request,
        response: Response,
        x_api_key: Annotated[str | None, Depends(_api_key_header)] = None,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_bearer)
        ] = None,
    ) -> None:
        if not require_auth:
            # No keys: callers are told apart by address (the first hop of
            # X-Forwarded-For behind a proxy) so one client cannot use up the limit
            # for everyone. This is fairness, not security.
            forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            peer = forwarded or (request.client.host if request.client else "unknown")
            label = "ip-" + key_id(peer)
            request.state.key_id = label
            wait = limiter.check(label)
            if wait > 0:
                raise HTTPException(
                    429,
                    "rate limit exceeded",
                    headers={"Retry-After": str(max(1, int(wait + 0.999)))},
                )
            return
        supplied = x_api_key or (credentials.credentials if credentials else None)
        if supplied is None or not any(
            hmac.compare_digest(supplied.encode(), key) for key in keys
        ):
            raise HTTPException(401, "a valid API key is required")
        label = key_id(supplied)
        request.state.key_id = label
        wait = limiter.check(label)
        if wait > 0:
            raise HTTPException(
                429,
                "rate limit exceeded",
                headers={"Retry-After": str(max(1, int(wait + 0.999)))},
            )

    secured = [Depends(require_key)]

    def resolve(
        route: str | None,
        cycle: str | None,
        icao_message: str | None = None,
        max_segment_nm: float | None = None,
    ) -> RouteResponse:
        try:
            chosen, resolver = store.resolver(cycle)
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        try:
            if icao_message and icao_message.strip():
                try:
                    extracted, result = resolver.resolve_icao_message(icao_message)
                except IcaoMessageError as error:
                    raise HTTPException(422, str(error)) from error
                return _response(result, extracted, max_segment_nm)
            assert route is not None
            return _response(resolver.resolve(route), None, max_segment_nm)
        except ConfigurationError as error:
            raise HTTPException(
                500, f"cycle {chosen} cannot be used: {error}"
            ) from error

    @app.get("/health", response_model=Health, tags=["service"])
    def health() -> Health:
        """Liveness: the process is up."""

        return Health(status="ok", version=API_VERSION)

    @app.get(
        "/ready",
        response_model=Ready,
        responses={503: ERRORS[503]},
        tags=["service"],
    )
    def ready() -> Ready:
        """Readiness: at least one cycle in effect is available."""

        try:
            return Ready(status="ready", default_cycle=store.default_cycle())
        except CycleUnavailableError as error:
            raise HTTPException(503, str(error)) from error

    @app.post(
        "/v1/route/resolve",
        response_model=RouteResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["route"],
        summary="Resolve a route to points",
    )
    def resolve_post(request: RouteRequest) -> RouteResponse:
        """Resolve a route string or ICAO FPL message to an ordered list of points."""

        return resolve(
            request.route, request.cycle, request.icao_message, request.max_segment_nm
        )

    @app.get(
        "/v1/route/resolve",
        response_model=RouteResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["route"],
        summary="Resolve a route given in the query string",
    )
    def resolve_get(
        route: Annotated[str, Query(min_length=1, max_length=4096)],
        cycle: CycleParam = None,
        max_segment_nm: MaxSegmentParam = None,
    ) -> RouteResponse:
        if not route.strip():
            raise HTTPException(422, "route must not be blank")
        return resolve(route, cycle, None, max_segment_nm)

    def entity(
        kind: str,
        fetch,
        identifier: str,
        cycle: str | None,
        *,
        include_branches: bool = False,
        include_airway_plot: bool = False,
    ) -> dict[str, Any]:
        try:
            with store.lookup(cycle) as (chosen, query):
                found = fetch(query, identifier)
                if include_branches:
                    _, resolver = store.resolver(chosen)
                    for procedure in found:
                        procedure["branches"] = lookups.procedure_branches(
                            procedure["points"], resolver.procedure_waypoint
                        )
                if include_airway_plot:
                    _, resolver = store.resolver(chosen)
                    for airway in found:
                        airway["plot_segments"] = lookups.airway_plot_segments(
                            airway["segments"], resolver.procedure_waypoint
                        )
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        except lookups.NotFoundError as error:
            raise HTTPException(404, str(error)) from error
        return {"cycle": chosen, kind: found}

    @app.get(
        "/v1/airports/{identifier}/procedures/{kind}",
        response_model=AirportProceduresResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def airport_procedures(
        identifier: str,
        kind: Literal["arrivals", "departures"],
        cycle: CycleParam = None,
    ) -> dict[str, Any]:
        """Published procedure branches associated with an airport."""
        try:
            with store.lookup(cycle) as (chosen, query):
                rows = lookups.airport_procedure_rows(
                    query, identifier.strip().upper(), kind
                )
                branches = []
                if any(rows):
                    _, resolver = store.resolver(chosen)
                    for procedure in rows:
                        branches.extend(
                            lookups.procedure_branches(
                                procedure, resolver.procedure_waypoint
                            )
                        )
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        except lookups.NotFoundError as error:
            raise HTTPException(404, str(error)) from error
        return {"cycle": chosen, "branches": branches}

    @app.get(
        "/v1/airports/search",
        response_model=AirportSearchResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def airport_search(
        q: Annotated[str, Query(min_length=1, max_length=80)],
        cycle: CycleParam = None,
    ) -> dict[str, Any]:
        """Find airports by identifier, name, or city."""
        try:
            with store.lookup_nasr(cycle) as (chosen, nasr):
                frame = nasr.get("APT_BASE")
                fields = ["ARPT_ID", "ICAO_ID", "ARPT_NAME", "CITY", "STATE_CODE"]
                rows = (
                    frame.reindex(columns=fields).fillna("").to_dict(orient="records")
                    if frame is not None
                    else []
                )
                airports = lookups.search_airports(rows, q)
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        return {"cycle": chosen, "airports": airports}

    @app.get(
        "/v1/airports/{identifier}",
        response_model=AirportResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def get_airport(identifier: str, cycle: CycleParam = None) -> dict[str, Any]:
        """An airport by FAA or ICAO identifier, with its runways."""

        return entity("airport", lookups.airport, identifier, cycle)

    @app.get(
        "/v1/fixes/{identifier}",
        response_model=FixesResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def get_fix(identifier: str, cycle: CycleParam = None) -> dict[str, Any]:
        """Every fix record with this name."""

        return entity("fixes", lookups.fixes, identifier, cycle)

    @app.get(
        "/v1/navaids/{identifier}",
        response_model=NavaidsResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def get_navaid(identifier: str, cycle: CycleParam = None) -> dict[str, Any]:
        """Every navaid record with this identifier (several when a name is shared)."""

        return entity("navaids", lookups.navaids, identifier, cycle)

    @app.get(
        "/v1/airways/{identifier}",
        response_model=AirwaysResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def get_airway(identifier: str, cycle: CycleParam = None) -> dict[str, Any]:
        """An airway by designation, e.g. J74, with its segments in order."""

        return entity(
            "airways", lookups.airways, identifier, cycle, include_airway_plot=True
        )

    @app.get(
        "/v1/arrivals/{identifier}",
        response_model=ProceduresResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def get_arrival(identifier: str, cycle: CycleParam = None) -> dict[str, Any]:
        """Standard terminal arrivals by FAA name or computer code."""

        return entity(
            "procedures", lookups.arrivals, identifier, cycle, include_branches=True
        )

    @app.get(
        "/v1/departures/{identifier}",
        response_model=ProceduresResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def get_departure(identifier: str, cycle: CycleParam = None) -> dict[str, Any]:
        """Departure procedures by FAA name or computer code."""

        return entity(
            "procedures", lookups.departures, identifier, cycle, include_branches=True
        )

    @app.get(
        "/v1/airspace/at",
        response_model=AirspaceResponse,
        response_model_exclude_none=True,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def airspace_at(
        lat: Annotated[float, Query(ge=-90, le=90)],
        lon: Annotated[float, Query(ge=-180, le=180)],
        cycle: CycleParam = None,
        include_boundaries: bool = False,
    ) -> dict[str, Any]:
        """The FAA regions whose horizontal boundaries contain a point.

        Includes ARTCC, FIR, CTA and UTA boundaries, plus Class B/C/D/E
        polygons when available for the selected cycle. Class regions include
        FAA altitude limits as published.
        """

        try:
            chosen, index = store.airspace(cycle)
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        return {
            "cycle": chosen,
            "position": {"lat": lat, "lon": lon},
            "regions": [asdict(region) for region in index.at(lat, lon)],
            "artcc_boundaries": index.artcc_boundaries(lat, lon),
            "boundaries": index.boundaries_at(lat, lon) if include_boundaries else None,
            "not_covered": index.not_covered,
        }

    @app.get(
        "/v1/airspace/viewport",
        response_model=AirspaceViewportResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def airspace_viewport(
        west: Annotated[float, Query(ge=-180, le=180)],
        south: Annotated[float, Query(ge=-90, le=90)],
        span: Annotated[float, Query(gt=0, le=360)],
        north: Annotated[float, Query(ge=-90, le=90)],
        cycle: CycleParam = None,
        kind: Annotated[list[Literal["B", "C", "D", "E"]] | None, Query()] = None,
        artcc: Annotated[
            list[Annotated[str, Field(pattern=r"^[A-Z0-9]{3}$")]] | None, Query()
        ] = None,
    ) -> dict[str, Any]:
        """Published airspace boundary lines within a map viewport."""
        if south >= north:
            raise HTTPException(422, "south must be below north")
        try:
            chosen, index = store.airspace(cycle)
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        return {
            "cycle": chosen,
            "boundaries": index.boundaries_in_view(
                west, south, span, north, kinds=set(kind) if kind else None, artcc=artcc
            ),
        }

    @app.get(
        "/v1/airspace/boundaries",
        response_model=AirspaceBoundariesResponse,
        response_model_exclude_none=True,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def airspace_boundaries(
        kind: Literal[
            "ARTCC", "FIR", "CTA", "UTA", "CTA/FIR", "B", "C", "D", "E"
        ] = "ARTCC",
        cycle: CycleParam = None,
    ) -> dict[str, Any]:
        """Return published outlines of one airspace type for a cycle."""
        try:
            chosen, index = store.airspace(cycle)
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        return {
            "cycle": chosen,
            "boundaries": index.boundaries(kind),
            "centers": index.artcc_names() if kind == "ARTCC" else None,
        }

    @app.get(
        "/v1/airspace/layer",
        response_model=AirspaceLayerResponse,
        responses=ERRORS,
        dependencies=secured,
        tags=["lookup"],
    )
    def airspace_layer(
        layer: LayerName,
        lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
        lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
        cycle: CycleParam = None,
        artcc: Annotated[
            list[Annotated[str, Field(pattern=r"^[A-Z0-9]{3}$")]] | None, Query()
        ] = None,
    ) -> dict[str, Any]:
        """Map features in a selected ARTCC or the ARTCCs covering a point."""
        if artcc is None and (lat is None or lon is None):
            raise HTTPException(422, "provide an ARTCC code or both coordinates")
        if artcc is not None and (lat is not None or lon is not None):
            raise HTTPException(422, "provide either an ARTCC code or coordinates")
        try:
            chosen, features = store.map_layer(layer, lat, lon, cycle, artcc=artcc)
        except CycleUnavailableError as error:
            raise HTTPException(404 if cycle else 503, str(error)) from error
        return {"cycle": chosen, **features}

    @app.get(
        "/v1/cycles",
        response_model=CyclesResponse,
        responses={401: ERRORS[401], 429: ERRORS[429]},
        dependencies=secured,
        tags=["service"],
    )
    def cycles() -> dict[str, Any]:
        """The cycles this service holds and which one is the default."""

        rows = store.describe()
        try:
            default = store.default_cycle()
        except CycleUnavailableError:
            default = None
        return {"default": default, "cycles": rows}

    return app
