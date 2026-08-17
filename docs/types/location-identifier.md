# Location identifier

A `LocationIdentifier` wraps one standalone `LID` row. The FAA publishes a
multi-column identity because a short location code alone is not globally
unique across facility groups and locations.

## Composite key

(`COUNTRY_CODE`, `LOC_ID`, `REGION_CODE`, `STATE`, `CITY`, `LID_GROUP`,
`FAC_TYPE`)

```python
location = nasr.location_identifiers.get(location_identifier_key)
record = location.record
```

## Generated API

```{eval-rst}
.. autoclass:: openNASR.locations.LocationIdentifier
.. autoclass:: openNASR.locations.LocationIdentifierRecord
.. autoclass:: openNASR.locations.LocationIdentifierRepository
```
