# Class airspace

`ClassAirspace` models the airport-linked `CLS_ARSP` family. Relationships use
the complete FAA site key rather than a potentially non-unique display ID.

## FAA source table and key

| Table | Composite key |
| --- | --- |
| `CLS_ARSP` | (`SITE_NO`, `SITE_TYPE_CODE`) |

```python
airspace = nasr.class_airspaces.get((site_no, site_type_code))

airspace.record
airspace.airport_site_key
airspace.classes
```

Use `find(airport_id=...)` for a non-unique short airport-ID search.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} ClassAirspaceRecord raw fields — CLS_ARSP (13)
`ClassAirspaceRecord` preserves one complete `CLS_ARSP` row. These fields are
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
| `CLASS_B_AIRSPACE` | Terminal Communication Facility containing Class B Airspace with be designated with ‘Y’ else null. |
| `CLASS_C_AIRSPACE` | Terminal Communication Facility containing Class C Airspace with be designated with ‘Y’ else null. |
| `CLASS_D_AIRSPACE` | Terminal Communication Facility containing Class D Airspace with be designated with ‘Y’ else null. |
| `CLASS_E_AIRSPACE` | Terminal Communication Facility containing Class E Airspace with be designated with ‘Y’ else null. |
| `AIRSPACE_HRS` | Airspace Hours of Terminal Communication Facility. |
| `REMARK` | Remark associated with Class Airspace. |

[Complete `CLS_ARSP` column reference](../csv-tables/cls-arsp.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.ClassAirspace
.. autoclass:: openNASR.airspace.ClassAirspaceRecord
.. autoclass:: openNASR.airspace.ClassAirspaceRepository
```

