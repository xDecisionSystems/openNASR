# Communication outlet

A `CommunicationOutlet` combines one standalone `COM` row with an optional
navaid relationship resolved through the complete FAA navigation key.

## Lookup

The search identifier is `COMM_LOC_ID`. Because a location identifier is not
guaranteed unique, `get()` can raise `AmbiguousRecordError`; use `find()` when
multiple matches are valid.

```python
outlets = nasr.communication_outlets.find("ABC")

for outlet in outlets:
    print(outlet.record.identifier, outlet.navaid)
```

## Generated API

```{eval-rst}
.. autoclass:: openNASR.communications.CommunicationOutlet
.. autoclass:: openNASR.communications.CommunicationOutletRecord
.. autoclass:: openNASR.communications.CommunicationOutletRepository
```
