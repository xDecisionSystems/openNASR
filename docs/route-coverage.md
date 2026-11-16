# Route construct coverage

What `RouteResolver.resolve()` does with each construct in a filed route, checked against
the 2026-10-29 cycle and a 46,580-route pool (70.5% usable; see REPLAN.md).

| Construct | Example | Status | Behavior |
|-----------|---------|--------|----------|
| Airport (FAA or ICAO id) | `KABQ`, `ABQ` | supported | Looked up in `APT_BASE`; preferred at the route's two ends. |
| Fix | `DOOKK` | supported | `FIX_BASE`. |
| Navaid | `TXO`, `ICT` | supported | `NAV_BASE`. VOT test facilities and fan markers are ignored as route points. |
| Lat/lon waypoint | `3800N07730W`, `37S078E` | supported | Decoded with range checks, used only when no NASR record has that name. |
| Direct | `..`, `DCT` | supported | Joins the points on either side. |
| Airway | `J74`, `V32`, `Q812` | supported | Expanded between the filed entry and exit points, forward or reverse. |
| SID / STAR by computer code | `SLC4.TCH`, `AMYLU.AMYLU3` | supported | Dotted codes are kept as one token. |
| SID / STAR transition | `LARGO3.GUP`, `VIEWS.DEHAN3` | supported | Body and transition in flight order; shared names narrowed by the route's end airports. |
| Bare SID / STAR name | `SHARED3` | supported | Resolved from the neighbouring route text. |
| Runway- or configuration-dependent branches | `GRNCH5`, `MONTN2.SEA` | partial | Only the portion common to all branches is included; `procedure_branches` warning lists the split and each branch. |
| Departure with no published points | `SLC4.TCH` | supported | Ends at the fix named by the computer code suffix; `procedure_geometry_unpublished` info note. |
| Speed / level group, `/` suffix | `/N0450F350`, `/0354` | supported | Ignored (not geometry). |
| Two identifiers, same name | `ZFP` (NDB and VOR/DME) | diagnostic | `AmbiguousRecordError`; the route text does not decide. Under discussion. |
| Identifier not in this cycle | `CHSLY7` | diagnostic | `RecordNotFoundError`; routes filed against another cycle. |
| Foreign airport, FIR airway, border point | `CYUL`, `UL6` | out of scope | `UnsupportedRouteContentError`. |
| FAA oceanic coordinate | `4300N/05000W` | out of scope | `UnsupportedRouteContentError`. |
| Radial/distance | `ABQ090020` | out of scope | `UnsupportedRouteContentError`. |
| Oceanic tracks (NAT), SID/STAR with runway | | out of scope | Not recognized; reported as an unknown identifier. |
