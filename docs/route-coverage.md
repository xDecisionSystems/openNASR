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
| Bare SID / STAR name | `SHARED3`, `ROKNN4` | supported | Resolved from the neighbouring route text. A STAR whose code is `ENTRY.NAME` (`ROKNN.ROKNN4`) is also found by its short name (2.1.36): joined at the preceding fix when that fix is on it, otherwise flown from its body (from its named fix). |
| Runway- or configuration-dependent branches | `GRNCH5`, `MONTN2.SEA` | partial | Only the portion common to all branches is included; `procedure_branches` warning lists the split and each branch. |
| Departure with no published points | `SLC4.TCH` | supported | Ends at the fix named by the computer code suffix; `procedure_geometry_unpublished` info note. |
| Speed / level group, `/` suffix | `/N0450F350`, `/0354` | supported | Ignored (not geometry). |
| Two identifiers, same name | `ZFP` (NDB and VOR/DME) | diagnostic | `AmbiguousRecordError`; the resolver does not pick one. The diagnostic's `detail.candidates` lists every candidate with name, kind, type (for navaids) and lat/lon so the caller can choose (owner decision, 2026-11-18). |
| Identifier not in this cycle | `CHSLY7`, `ZWE280024` | partial (2.1.36) | `RecordNotFoundError` with `detail.skipped` true: the identifier is skipped and its neighbours are joined directly, so the rest of the route is still returned (not `complete`). Up to 25 per route (5 before 2.1.38); before 2.1.36 the route came back without points. |
| Foreign airport, FIR airway, border point | `CYUL`, `UL6` | out of scope | `UnsupportedRouteContentError`. |
| FAA lat/lon point with slash | `2706N/09216W` | supported (2.1.34) | Decoded like `2706N09216W`; FAA SWIM (ERAM) writes Gulf of Mexico points this way. |
| Fix-radial-distance | `MOL057057`, `BAIRN170010` | supported (2.1.34) | Base fix, navaid or airport; magnetic radial converted to true with the magnetic variation of the nearest navaid or airport in the cycle; distance in NM along a great circle. Point `kind` `radial_distance`. |
| ERAM `./.` separator | `KORD./.OBK131026..SEWTO` | supported (2.1.34) | Read as a plain separator (FAA SWIM SFDPS amended routes). |
| STAR joined at a fix on it | `SCHUL.OZZZI2` | supported (2.1.35) | ERAM names the join fix and the STAR; the STAR is flown from the fix (on a transition or the body), then its body. Several transitions through the fix with different paths give `AmbiguousRecordError`. |
| ERAM unknown portion | `XXX` | partial (2.1.36) | Not a fix: ERAM's mark for a part of the route it does not know. The route is returned up to the last point before it and stops there, with an `unknown_route_portion` warning at the `XXX` position; nothing after it is placed (where the flight rejoins is not known). In 2.1.35 the points on either side were joined directly. |
| Oceanic tracks (NAT), SID/STAR with runway | | out of scope | Not recognized; reported as an unknown identifier. |
