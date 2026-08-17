# Arrivals

The arrivals API models FAA Standard Terminal Arrival Routes (STARs). A
`StarProcedure` combines one published procedure with its airport associations
and FAA-ordered route points.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `STAR_BASE` | STAR identity |
| `STAR_APT` | Airport associations |
| `STAR_RTE` | Ordered routes and points |

The composite key is (`STAR_COMPUTER_CODE`, `ARTCC`).

```python
key = (computer_code, artcc)
arrival = nasr.stars.get(key)

arrival.record
arrival.airports
arrival.routes

# Plot only this STAR's uniquely resolved route legs.
figure, axes = arrival.plot(nasr)
```

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} StarProcedureRecord raw fields — STAR_BASE (8)
`StarProcedureRecord` preserves one complete `STAR_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ARRIVAL_NAME` | STAR Name. Name Assigned to the Standard Terminal Arrival. |
| `AMENDMENT_NO` | Amendment Number (spelled out) of the STAR that will be Active on the Effective Date. |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. |
| `STAR_AMEND_EFF_DATE` | The First Effective Date for which the STAR Amendment became Active. |
| `RNAV_FLAG` | Y/N Flag determines whether a STAR is RNAV required. |
| `STAR_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the STAR. EX. GLAND.BLUMS5 |
| `SERVED_ARPT` | List of Airports Served by the STAR. |

[Complete `STAR_BASE` column reference](../csv-tables/star-base.md)
```

```{faa-dropdown} StarAirportRecord raw fields — STAR_APT (7)
`StarAirportRecord` preserves one complete `STAR_APT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `STAR_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the STAR. EX. GLAND.BLUMS5 |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. |
| `BODY_NAME` | The Name of the Body for which the Airport/Runway End are associated. The Body Name is the first and last Fix of the Segment. |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given STAR, the BODY_SEQ will uniquely identify the Segment. |
| `ARPT_ID` | The associated Airport Identifier. |
| `RWY_END_ID` | The Runway End Identifier if applicable. |

[Complete `STAR_APT` column reference](../csv-tables/star-apt.md)
```

```{faa-dropdown} StarRouteRecord raw fields — STAR_RTE (13)
`StarRouteRecord` preserves one complete `STAR_RTE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `STAR_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the STAR. EX. GLAND.BLUMS5 |
| `ARTCC` | List of all Responsible ARTCCs based on Airports Served. |
| `ROUTE_PORTION_TYPE` | The Segment is identified as either a Transition or Body. |
| `ROUTE_NAME` | The Transition or Body Name. |
| `BODY_SEQ` | In the rare case that Body Name is not Unique for a given STAR, the BODY_SEQ will uniquely identify the Segment. |
| `TRANSITION_COMPUTER_CODE` | FAA-Assigned Computer Identifier for the TRANSITION. |
| `POINT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given Segment. |
| `POINT` | The FIX or NAVAID adapted on the Segment. |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Point Types only. |
| `POINT_TYPE` | Specific FIX or NAVAID Type. |
| `NEXT_POINT` | The Point that directly follows the current Point on an individual segment. |
| `ARPT_RWY_ASSOC` | The list of APT and/or APT/RWY associated with a given Segment. |

[Complete `STAR_RTE` column reference](../csv-tables/star-rte.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.arrivals.StarProcedure
.. autoclass:: openNASR.arrivals.StarProcedureRecord
.. autoclass:: openNASR.arrivals.StarAirportRecord
.. autoclass:: openNASR.arrivals.StarRouteRecord
.. autoclass:: openNASR.arrivals.StarProcedureRepository
```
