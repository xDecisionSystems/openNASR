# Parachute Jump Area

A `ParachuteJumpArea` combines one published jump-area record with its contacts
and, when the FAA relationship is present, its associated airport.

## FAA source tables

| Table | Content |
| --- | --- |
| `PJA_BASE` | Identity, center point, radius, and operating data |
| `PJA_CON` | Contact records |
| `APT_BASE` | Optional airport relationship |

The lookup key is `PJA_ID`.

```python
area = nasr.parachute_jump_areas.get(pja_id)

area.record
area.contacts
area.airport
```

FAA jump areas are represented by center and radius data rather than a
published polygon table.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.ParachuteJumpArea
.. autoclass:: openNASR.airspace.ParachuteJumpAreaRecord
.. autoclass:: openNASR.airspace.ParachuteJumpAreaContactRecord
.. autoclass:: openNASR.airspace.ParachuteJumpAreaRepository
```
