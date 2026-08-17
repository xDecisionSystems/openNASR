# Military operation

A `MilitaryOperation` models one airport-linked `MIL_OPS` row. It joins to an
airport through the complete FAA site identity rather than a short airport ID.

## FAA source table and key

| Table | Composite key |
| --- | --- |
| `MIL_OPS` | (`SITE_NO`, `SITE_TYPE_CODE`) |

```python
operation = nasr.military_operations.get((site_no, site_type_code))

operation.record
operation.airport_site_key
operation.airport_id
```

Use `find(airport_id=...)` when searching by a potentially non-unique short
identifier.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} MilitaryOperationRecord raw fields — MIL_OPS (13)
`MilitaryOperationRecord` preserves one complete `MIL_OPS` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `MIL_OPS_OPER_CODE` | Military Agency Type Code that Operates the Control Facility. |
| `MIL_OPS_CALL` | Radio Call Name for Military Operations at this Control Facility. |
| `MIL_OPS_HRS` | Hours of Military Operations Conducted each Day. |
| `AMCP_HRS` | Hours of Operation of the Military Aircraft Command Post (AMCP) Located at the Facility. |
| `PMSV_HRS` | Hours of Operation of The Military Pilot-To-Metro Service (PMSV) Located at the Facility. |
| `REMARK` | Remark associated with Military Operations. |

[Complete `MIL_OPS` column reference](../csv-tables/mil-ops.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.military.MilitaryOperation
.. autoclass:: openNASR.military.MilitaryOperationRecord
.. autoclass:: openNASR.military.MilitaryOperationRepository
```

