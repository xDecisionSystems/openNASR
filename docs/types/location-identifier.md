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

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} LocationIdentifierRecord raw fields — LID (12)
`LocationIdentifierRecord` preserves one complete `LID` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `COUNTRY_CODE` | Country Code Associated with The Location Identifier. |
| `LOC_ID` | Location Identifier. 3-4 character alphanumeric identifier. |
| `REGION_CODE` | FAA Region Code Associated with The Location Identifier |
| `STATE` | State or territory name associated with the location identifier. |
| `CITY` | City Name Associated with The Location Identifier. |
| `LID_GROUP` | Logical grouping of LID entries. CONTROL FACILITY FLIGHT SERVICE STATION INSTRUMENT LANDING FACILITY LANDING FACILITY NAVIGATION AID REMOTE COMMINICATION OUTLET SPECIAL USE RESOURCE WEATHER REPORTING STATION WEATHER SENSOR |
| `FAC_TYPE` | Facility Type of Location Identifier Record |
| `FAC_NAME` | Official Facility Name. Instrument Landing System Facility Name is a concatenation of the Associated Landing Facility Name, ID and Runway End ID (e.g. ATLANTIC CITY INTL(ACY) ILS RWY 31) LID |
| `RESP_ARTCC_ID` | Responsible FAA Air Route Traffic Control Center (ARTCC) Identifier |
| `ARTCC_COMPUTER_ID` | Responsible ARTCC Computer Identifier |
| `FSS_ID` | Tie-In Flight Service Station (FSS) Identifier |

[Complete `LID` column reference](../csv-tables/lid.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.locations.LocationIdentifier
.. autoclass:: openNASR.locations.LocationIdentifierRecord
.. autoclass:: openNASR.locations.LocationIdentifierRepository
```

