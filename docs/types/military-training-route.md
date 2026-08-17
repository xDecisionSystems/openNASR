# Military training route

A `MilitaryTrainingRoute` combines one route identity with FAA-ordered agency,
point, procedure, terrain, and width records.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `MTR_BASE` | Route identity |
| `MTR_AGY` | Responsible agencies |
| `MTR_PT` | Ordered route points |
| `MTR_SOP` | Standard operating procedures |
| `MTR_TERR` | Terrain-following operations |
| `MTR_WDTH` | Route widths |

The composite key is (`ROUTE_TYPE_CODE`, `ROUTE_ID`).

```python
route = nasr.military_training_routes.get((route_type_code, route_id))

route.record
route.agencies
route.points
route.procedures
route.terrain
route.widths
```

Point identity uses `ROUTE_PT_ID`; `ROUTE_PT_SEQ` controls display order.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.military.MilitaryTrainingRoute
.. autoclass:: openNASR.military.MilitaryTrainingRouteRecord
.. autoclass:: openNASR.military.MilitaryTrainingRouteAgencyRecord
.. autoclass:: openNASR.military.MilitaryTrainingRoutePointRecord
.. autoclass:: openNASR.military.MilitaryTrainingRouteProcedureRecord
.. autoclass:: openNASR.military.MilitaryTrainingRouteTerrainRecord
.. autoclass:: openNASR.military.MilitaryTrainingRouteWidthRecord
.. autoclass:: openNASR.military.MilitaryTrainingRouteRepository
```
