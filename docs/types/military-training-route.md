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

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} MilitaryTrainingRouteRecord raw fields — MTR_BASE (6)
`MilitaryTrainingRouteRecord` preserves one complete `MTR_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ROUTE_TYPE_CODE` | MTR Type Code. |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. |
| `ARTCC` | List of ARTCC Idents that MTR traverses. |
| `FSS` | All Flight Service Station (FSS) Idents Within 150 Nautical Miles of The Route. |
| `TIME_OF_USE` | Published time-of-use information for the military training route. |

[Complete `MTR_BASE` column reference](../csv-tables/mtr-base.md)
```

```{faa-dropdown} MilitaryTrainingRouteAgencyRecord raw fields — MTR_AGY (14)
`MilitaryTrainingRouteAgencyRecord` preserves one complete `MTR_AGY` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ROUTE_TYPE_CODE` | MTR Type Code. |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. |
| `ARTCC` | List of ARTCC Idents that MTR traverses. |
| `AGENCY_TYPE` | MTR Agency Type Code. |
| `AGENCY_NAME` | Agency Organization Name |
| `STATION` | Agency Station |
| `ADDRESS` | Agency Address |
| `CITY` | Agency City |
| `STATE_CODE` | Agency State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ZIP_CODE` | Agency ZIP Code |
| `COMMERCIAL_NO` | Agency Commercial Phone Number |
| `DSN_NO` | Agency DSN Phone Number |
| `HOURS` | Agency Hours |

[Complete `MTR_AGY` column reference](../csv-tables/mtr-agy.md)
```

```{faa-dropdown} MilitaryTrainingRoutePointRecord raw fields — MTR_PT (21)
`MilitaryTrainingRoutePointRecord` preserves one complete `MTR_PT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ROUTE_TYPE_CODE` | MTR Type Code. |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. |
| `ARTCC` | List of ARTCC Idents that MTR traverses. |
| `ROUTE_PT_SEQ` | Sequencing number in multiples of ten. Points are in order adapted for given MTR. |
| `ROUTE_PT_ID` | Route Point Identifier. |
| `NEXT_ROUTE_PT_ID` | The Next Sequential ROUTE_PT_ID. |
| `SEGMENT_TEXT` | Concatenation of Segment Text preceded by the Segment Text Sequence Number. |
| `LAT_DEG` | MTR Route Point Latitude Degrees |
| `LAT_MIN` | MTR Route Point Latitude Minutes |
| `LAT_SEC` | MTR Route Point Latitude Seconds |
| `LAT_HEMIS` | MTR Route Point Latitude Hemisphere |
| `LAT_DECIMAL` | MTR Route Point Latitude in Decimal Format |
| `LONG_DEG` | MTR Route Point Longitude Degrees |
| `LONG_MIN` | MTR Route Point Longitude Minutes |
| `LONG_SEC` | MTR Route Point Longitude Seconds |
| `LONG_HEMIS` | MTR Route Point Longitude Hemisphere |
| `LONG_DECIMAL` | MTR Route Point Longitude in Decimal Format |
| `NAV_ID` | Identifier of related NAVAID |
| `NAVAID_BEARING` | Bearing of NAVAID from Point |
| `NAVAID_DIST` | Distance of NAVAID from Point |

[Complete `MTR_PT` column reference](../csv-tables/mtr-pt.md)
```

```{faa-dropdown} MilitaryTrainingRouteProcedureRecord raw fields — MTR_SOP (6)
`MilitaryTrainingRouteProcedureRecord` preserves one complete `MTR_SOP` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ROUTE_TYPE_CODE` | MTR Type Code. |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. |
| `ARTCC` | List of ARTCC Idents that MTR traverses. |
| `SOP_SEQ_NO` | SOP Text Computer assigned Sequence Number |
| `SOP_TEXT` | Standard Operating Procedure Text |

[Complete `MTR_SOP` column reference](../csv-tables/mtr-sop.md)
```

```{faa-dropdown} MilitaryTrainingRouteTerrainRecord raw fields — MTR_TERR (6)
`MilitaryTrainingRouteTerrainRecord` preserves one complete `MTR_TERR` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ROUTE_TYPE_CODE` | MTR Type Code. |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. |
| `ARTCC` | List of ARTCC Idents that MTR traverses. |
| `TERRAIN_SEQ_NO` | TERRAIN Text Computer assigned Sequence Number |
| `TERRAIN_TEXT` | Terrain Following Operations Text |

[Complete `MTR_TERR` column reference](../csv-tables/mtr-terr.md)
```

```{faa-dropdown} MilitaryTrainingRouteWidthRecord raw fields — MTR_WDTH (6)
`MilitaryTrainingRouteWidthRecord` preserves one complete `MTR_WDTH` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ROUTE_TYPE_CODE` | MTR Type Code. |
| `ROUTE_ID` | Route Identifier. Along with the ROUTE_TYPE_CODE creates a unique MTR identifier. |
| `ARTCC` | List of ARTCC Idents that MTR traverses. |
| `WIDTH_SEQ_NO` | WIDTH Text Computer assigned Sequence Number |
| `WIDTH_TEXT` | Route Width Description Text |

[Complete `MTR_WDTH` column reference](../csv-tables/mtr-wdth.md)
```

<!-- END GENERATED RECORD FIELDS -->

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
