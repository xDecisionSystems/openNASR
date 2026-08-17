# Miscellaneous Activity Area

A `Maa` represents an FAA Miscellaneous Activity Area, such as an aerobatic,
glider, space-launch, ultralight, or unmanned-aircraft activity area. It is not
a military-airspace abbreviation.

## FAA source tables

| Table | Content |
| --- | --- |
| `MAA_BASE` | Identity, activity type, location, and operating data |
| `MAA_CON` | Contacts |
| `MAA_RMK` | Remarks |
| `MAA_SHP` | Ordered geometry points |

The lookup key is `MAA_ID`.

```python
area = nasr.maas.get(maa_id)

area.record
area.contacts
area.remarks
area.geometry
```

`geometry` is `None` for radius-only areas without published shape rows.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.Maa
.. autoclass:: openNASR.airspace.MaaRecord
.. autoclass:: openNASR.airspace.MaaContactRecord
.. autoclass:: openNASR.airspace.MaaRemarkRecord
.. autoclass:: openNASR.airspace.MaaShapePointRecord
.. autoclass:: openNASR.airspace.MaaRepository
```
