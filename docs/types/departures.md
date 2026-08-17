# Departures

The departures API covers coded departure routes, departure procedures, and
preferred routes. Each repository preserves the FAA's complete identity key
and source-defined child ordering.

## Coded departure routes

`CDR` contains standalone routes keyed by `RCode`.

```python
coded_route = nasr.coded_departure_routes.get(route_code)
```

```{eval-rst}
.. autoclass:: openNASR.departure.CodedDepartureRoute
.. autoclass:: openNASR.departure.CodedDepartureRouteRecord
.. autoclass:: openNASR.departure.CodedDepartureRouteRepository
```

## Departure procedures

| Table | Content |
| --- | --- |
| `DP_BASE` | Procedure identity |
| `DP_APT` | Airport associations |
| `DP_RTE` | Ordered routes and points |

The composite key is (`DP_NAME`, `ARTCC`, `DP_COMPUTER_CODE`).

```python
procedure = nasr.departures.get((procedure_name, artcc, computer_code))
procedure.airports
procedure.routes
```

```{eval-rst}
.. autoclass:: openNASR.departure.DepartureProcedure
.. autoclass:: openNASR.departure.DepartureProcedureRecord
.. autoclass:: openNASR.departure.DepartureAirportRecord
.. autoclass:: openNASR.departure.DepartureRouteRecord
.. autoclass:: openNASR.departure.DepartureProcedureRepository
```

## Preferred routes

Preferred routes have their own source tables, composite lookup key, route
formats, and ordered segments. See the dedicated {doc}`preferred-route` page.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} CodedDepartureRouteRecord raw fields — CDR (12)
`CodedDepartureRouteRecord` preserves one complete `CDR` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `RCode` | Each CDR is uniquely identified by an eight-character alphanumeric code. The Route Code is a concatenation of the Origin, Destination and an alphanumeric route identifier. |
| `Orig` | The CDR Point of Origin is a 3 or 4 character departure airport designator. |
| `Dest` | The CDR Point of Destination is a 3 or 4 character arrival airport designator. |
| `DepFix` | The Departure Fix associated with a given CDR. |
| `Route String` | The preplanned route of flight associated with a given CDR. |
| `DCNTR` | Departure ARTCC associated with a given CDR. |
| `ACNTR` | Arrival ARTCC associated with a given CDR. |
| `TCNTRs` | A list of all Traversed ARTCCs for a given CDR. |
| `CoordReq` | Y/N indicator as to whether Coordination is required. |
| `Play` | The Playbook Play name for a given CDR. |
| `NavEqp` | Navigation Equipment Designator. |
| `Length` | Length of CDR in Nautical Miles |

[Complete `CDR` column reference](../csv-tables/cdr.md)
```

```{faa-dropdown} DepartureProcedureRecord raw fields — DP_BASE (9)
`DepartureProcedureRecord` preserves one complete `DP_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `DP_NAME` | Name Assigned to the Departure Procedure. |
| `AMENDMENT_NO` | Amendment Number (spelled out) of the DP that will be Active on the Effective Date. |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. |
| `DP_AMEND_EFF_DATE` | The First Effective Date for which the DP Amendment became Active. |
| `RNAV_FLAG` | Y/N Flag determines whether a DP is RNAV required. |
| `DP_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the DP. EX. ADELL6.ADELL |
| `GRAPHICAL_DP_TYPE` | Identifies whether the Graphical DP is type SID or OBSTACLE. |
| `SERVED_ARPT` | List of Airports Served by the DP. |

[Complete `DP_BASE` column reference](../csv-tables/dp-base.md)
```

```{faa-dropdown} DepartureAirportRecord raw fields — DP_APT (8)
`DepartureAirportRecord` preserves one complete `DP_APT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `DP_NAME` | Name Assigned to the Departure Procedure. |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. |
| `DP_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the DP. EX. ADELL6.ADELL |
| `BODY_NAME` | The Name of the Body for which the Airport/Runway End are associated. The Body Name is the first and last Fix of the Segment. |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given DP, the BODY_SEQ will uniquely identify the Segment. |
| `ARPT_ID` | The associated Airport Identifier. |
| `RWY_END_ID` | The Runway End Identifier if applicable. |

[Complete `DP_APT` column reference](../csv-tables/dp-apt.md)
```

```{faa-dropdown} DepartureRouteRecord raw fields — DP_RTE (14)
`DepartureRouteRecord` preserves one complete `DP_RTE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `DP_NAME` | Name Assigned to the Departure Procedure. |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. |
| `DP_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the DP. EX. ADELL6.ADELL |
| `ROUTE_PORTION_TYPE` | The Segment is identified as either a Transition or Body. |
| `ROUTE_NAME` | The Transition or Body Name. |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given DP, the BODY_SEQ will uniquely identify the Segment. |
| `TRANSITION_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the TRANSITION. |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Segment. |
| `POINT` | The FIX or NAVAID adapted on the Segment. |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Point Types only. |
| `POINT_TYPE` | Specific FIX or NAVAID Type. |
| `NEXT_POINT` | The Point that directly follows the current Point on an individual segment. |
| `ARPT_RWY_ASSOC` | The list of APT and/or APT/RWY associated with a given Segment. |

[Complete `DP_RTE` column reference](../csv-tables/dp-rte.md)
```

<!-- END GENERATED RECORD FIELDS -->
