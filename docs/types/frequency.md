# Frequency

A `Frequency` wraps one standalone FAA frequency-assignment row. Exact lookup
uses the complete facility context and never joins on a display name alone.

## FAA source table and key

The `FRQ` composite key is:

1. `FACILITY`
2. `SERVICED_FACILITY`
3. `SERVICED_SITE_TYPE`
4. `SERVICED_STATE`
5. `SERVICED_COUNTRY`
6. `FREQ`
7. `SECTORIZATION`
8. `FREQ_USE`

```python
frequency = nasr.frequencies.get(frequency_key)
record = frequency.record
```

`find(serviced_facility=(name, site_type, state, country))` supports searches
using the complete serviced-facility context.

## Generated API

```{eval-rst}
.. autoclass:: openNASR.communications.Frequency
.. autoclass:: openNASR.communications.FrequencyRecord
.. autoclass:: openNASR.communications.FrequencyRepository
```
