# Holding pattern

A `HoldingPattern` groups one published pattern with ordered charts, remarks,
speed/altitude restrictions, and an optional fully resolved fix.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `HPF_BASE` | Holding-pattern identity and geometry |
| `HPF_CHRT` | Chart references |
| `HPF_RMK` | Remarks |
| `HPF_SPD_ALT` | Speed and altitude restrictions |

The composite key is (`HP_NAME`, `HP_NO`, `STATE_CODE`, `COUNTRY_CODE`).

```python
key = (name, number, state, country)
pattern = nasr.holding_patterns.get(key)

pattern.record
pattern.charts
pattern.remarks
pattern.speed_altitude_limits
pattern.fix
```

## Generated API

```{eval-rst}
.. autoclass:: openNASR.holding.HoldingPattern
.. autoclass:: openNASR.holding.HoldingPatternRecord
.. autoclass:: openNASR.holding.HoldingPatternChartRecord
.. autoclass:: openNASR.holding.HoldingPatternRemarkRecord
.. autoclass:: openNASR.holding.HoldingPatternSpeedAltitudeRecord
.. autoclass:: openNASR.holding.HoldingPatternRepository
```
