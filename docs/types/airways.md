# Airways

An `Airway` combines one airway identity record with FAA-sequence-ordered
segments and their altitude constraints. Segment relationships may resolve to
a fix or navaid through the complete published key.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `AWY_BASE` | Airway identity |
| `AWY_SEG_ALT` | Ordered points and altitude constraints |

The composite key is (`REGULATORY`, `AWY_LOCATION`, `AWY_ID`).

```python
key = (regulatory, airway_location, airway_id)
airway = nasr.airways.get(key)

airway.record
airway.segments
```

Each segment exposes its point sequence, minimum enroute altitude, maximum
authorized altitude, and resolved navigation record when available.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airway.Airway
.. autoclass:: openNASR.airway.AirwayRecord
.. autoclass:: openNASR.airway.AirwaySegmentRecord
.. autoclass:: openNASR.airway.AirwayRepository
```

