# Airspace boundaries

`AirspaceBoundary` represents any ordered boundary published in the FAA
`ARB_SEG` table. It has a `Boundary` geometry and a `.plot(nasr)` convenience
method. The supported FAA boundary types are:

- `ARTCC` — Air Route Traffic Control Center;
- `FIR` — Flight Information Region;
- `CTA` — Control Area;
- `CTA/FIR` — combined Control Area / Flight Information Region; and
- `UTA` — Upper Control Area.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `ARB_BASE` | Location identity and reference position |
| `ARB_SEG` | Ordered vertices, boundary type, and altitude |

The complete boundary key is `LOCATION_ID`, `TYPE`, and `ALTITUDE`.

```python
# Anchorage's published unlimited CTA/FIR boundary.
boundary = nasr.airspace_boundaries.get(
    "ZAN", boundary_type="CTA/FIR", altitude="UNLIMITED"
)

figure, axes = boundary.plot(nasr, projection="geographic")

# Find every FIR regardless of altitude.
firs = nasr.airspace_boundaries.find(boundary_type="FIR")
```

`AirspaceBoundary.plot()` draws only the selected boundary by default. This is
safe for oceanic and antimeridian-crossing geometries; enable airport, fix,
navaid, or airway layers explicitly when they are meaningful for the selected
area.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.AirspaceBoundary
.. autoclass:: openNASR.airspace.AirspaceBoundaryRepository
```
