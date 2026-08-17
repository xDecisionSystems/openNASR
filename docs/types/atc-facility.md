# ATC facility

An `AtcFacility` combines one ATC facility with its ATIS, remarks, and service
rows. Child records preserve their FAA source values and source-derived order.

## FAA source tables

| Table | Content |
| --- | --- |
| `ATC_BASE` | Facility identity and location |
| `ATC_ATIS` | ATIS services |
| `ATC_RMK` | Ordered remarks |
| `ATC_SVC` | Facility services |

The complete key is (`SITE_NO`, `SITE_TYPE_CODE`, `FACILITY_TYPE`,
`STATE_CODE`, `FACILITY_ID`, `CITY`, `COUNTRY_CODE`).

```python
facility = nasr.atc_facilities.get(atc_key)

facility.record
facility.atis_services
facility.remarks
facility.services
```

## Generated API

```{eval-rst}
.. autoclass:: openNASR.atc.AtcFacility
.. autoclass:: openNASR.atc.AtcFacilityRecord
.. autoclass:: openNASR.atc.AtisRecord
.. autoclass:: openNASR.atc.AtcRemarkRecord
.. autoclass:: openNASR.atc.AtcServiceRecord
.. autoclass:: openNASR.atc.AtcFacilityRepository
```

