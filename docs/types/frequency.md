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

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} FrequencyRecord raw fields — FRQ (21)
`FrequencyRecord` preserves one complete `FRQ` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `FACILITY` | Contains FACILITY ID except for FACILITY TYPE AFIS, CTAF, GCO, UNICOM and RCAG which do not contain FACILITY IDs in NASR. The FACILITY NAME is used for RCAG sites. AFIS, CTAF, GCO and UNICOM are NULL since they do not contain either a FACILITY ID or FACILITY NAME in NASR. |
| `FAC_NAME` | Official Facility Name. AFIS, CTAF, GCO and UNICOM FACILITY TYPEs are NULL since they do not contain either a FACILITY ID or FACILITY NAME in NASR. ASOS/AWOS FACILITY TYPEs are NULL since they do not contain a FACILITY NAME in NASR. |
| `FACILITY_TYPE` | All records contain a FACILITY TYPE. Please note that RCO or RCO1 both are the same and serve the same function; a remote communication outlet. An RCO1 may exist if two separate sites |
| `ARTCC_OR_FSS_ID` | FACILITY TYPE RCAG contain an identified ARTCC ID and FACILITY TYPE RCO/RCO1 contain an identified FSS ID. The ARTCC ID for an RCAG and the FSS ID for an RCO/RCO1 is included for convenience since that is the resource in NASR you must open to view specific RCAG or RCO/RCO1 information. |
| `CPDLC` | A Controller Pilot Data Link Communications (CPDLC) remark associated with a FACILITY is listed here. |
| `TOWER_HRS` | Only listed for ATCT FACILITY TYPEs where the FACILITY equals the SERVICED FACILITY. |
| `SERVICED_FACILITY` | The FACILITY ID (or FACILITY NAME if FACILITY TYPE is RCAG) that is serviced by the frequencies listed. This is a NON-NULL field. |
| `SERVICED_FAC_NAME` | The FACILITY NAME that is serviced by the frequencies listed. |
| `SERVICED_SITE_TYPE` | Facility Type of SERVICED FACILITY. |
| `LAT_DECIMAL` | Facility Reference Point Latitude in Decimal Format. |
| `LONG_DECIMAL` | Facility Reference Point Longitude in Decimal Format. |
| `SERVICED_CITY` | Serviced Facility Associated City Name. |
| `SERVICED_STATE` | This is the two letter state ID of the SERVICED FACILITY. |
| `SERVICED_COUNTRY` | Country Post Office Code Serviced Facility Located |
| `TOWER_OR_COMM_CALL` | Radio call used by pilot to contact ATC or FSS facility. |
| `PRIMARY_APPROACH_RADIO_CALL` | Radio call of facility that furnishes primary approach control. |
| `FREQ` | Frequency for SERVICED FACILITY use. In the case of a NAVAID with DME/TACAN Channel, the Frequency is displayed with the Channel – FREQ/CHAN. |
| `SECTORIZATION` | Sectorization based on SERVICED FACILITY or airway boundaries, or limitations based on runway usage. For ARTCC and RCAG, Sectorization identifies the Frequency Altitude as Low, High, Low/High or Ultra-High. |
| `FREQ_USE` | SERVICED FACILITY frequency use description. |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) |

[Complete `FRQ` column reference](../csv-tables/frq.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.communications.Frequency
.. autoclass:: openNASR.communications.FrequencyRecord
.. autoclass:: openNASR.communications.FrequencyRepository
```

