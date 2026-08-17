# Navaid

`NavaidRecord` preserves one `NAV_BASE` row and exposes common navigation-aid
identity, type, frequency, coordinate, and ARTCC fields.

## Lookup

The primary identifier is `NAV_ID`. State, country, ARTCC, and navaid type can
disambiguate identifiers that occur more than once.

```python
navaid = nasr.navaids.get("DCA", state="VA", nav_type="VOR/DME")

navaid.identifier
navaid.frequency
navaid.latitude
navaid.longitude
```

`NAVAID` is retained as the legacy adapter.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.nav.NavaidRecord
.. autoclass:: openNASR.repository.NavaidRepository
.. autoclass:: openNASR.nav.NAVAID
```
