# NASR cycle

`NASR` selects one exact locally cached FAA subscription cycle and lazily
exposes its tables and domain repositories. `CycleManager` performs explicit
cache, archive, download, extraction, and optional DuckDB operations.

## Data model

| Type | Purpose |
| --- | --- |
| `NASR` | Lazy table mapping and repository facade for one cycle |
| `Cycle` | Paths and effective date for one cached cycle |
| `RemoteCycle` | Effective date and archive URL discovered from the FAA |
| `UpdateStatus` | Result of an explicit update check |
| `RemovalResult` | Representations removed from the local cache |

## Select a local cycle

```python
from openNASR import NASR

nasr = NASR(cycle="2026-08-06")
airports = nasr["APT_BASE"]
```

Construction never downloads data or substitutes another explicitly requested
date.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.nasr.NASR
.. autoclass:: openNASR.cycles.CycleManager
.. autoclass:: openNASR.cycles.Cycle
.. autoclass:: openNASR.cycles.RemoteCycle
.. autoclass:: openNASR.cycles.UpdateStatus
.. autoclass:: openNASR.cycles.RemovalResult
.. autoclass:: openNASR.cycles.FaaCycleProvider
```

