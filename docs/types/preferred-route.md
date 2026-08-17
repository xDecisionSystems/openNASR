# Preferred routes

A `PreferredRoute` combines one preferred-route identity record with its route
format records and FAA-ordered segments.

## FAA source tables and key

| Table | Content |
| --- | --- |
| `PFR_BASE` | Preferred-route identity |
| `PFR_RMT_FMT` | Route-format variants |
| `PFR_SEG` | Ordered route segments |

The composite key is (`ORIGIN_ID`, `DSTN_ID`, `PFR_TYPE_CODE`, `ROUTE_NO`).

```python
key = (origin, destination, route_type, route_number)
route = nasr.preferred_routes.get(key)

route.record
route.formats
route.segments
```

Use `find()` to enumerate preferred routes in FAA source order. Exact lookup
raises `RecordNotFoundError` for no match and `AmbiguousRecordError` if the
selected cycle contains duplicate complete keys.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} PreferredRouteRecord raw fields — PFR_BASE (22)
`PreferredRouteRecord` preserves one complete `PFR_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ORIGIN_ID` | Origin Facility Location Identifier (Depending on NAR Type and Direction, Origin ID Is either Coastal Fix or Inland NAV Facility or Fix) |
| `ORIGIN_CITY` | Origin Facility Associated City Name. |
| `ORIGIN_STATE_CODE` | This is the two letter state ID of the Origin Facility location. NULL if outside the US. |
| `ORIGIN_COUNTRY_CODE` | Country Code of the Origin Facility Located. |
| `DSTN_ID` | Destination Facility Location Identifier (Depending on NAR Type and Direction, Destination ID Is either Airport, Coastal Fix or Inland NAV Facility or Fix) |
| `DSTN_CITY` | Destination Facility Associated City Name. |
| `DSTN_STATE_CODE` | This is the two letter state ID of the Destination Facility location. NULL if outside the US. |
| `DSTN_COUNTRY_CODE` | Country Code of the Destination Facility Located. |
| `PFR_TYPE_CODE` | Type Code of Preferred Route Description. |
| `ROUTE_NO` | Route Identifier Sequence Number (1-99) |
| `SPECIAL_AREA_DESCRIP` | Preferred Route Area Description. |
| `ALT_DESCRIP` | Preferred Route Altitude Description. |
| `AIRCRAFT` | Aircraft Allowed/Limitations Description |
| `HOURS` | Effective Hours (GMT) Description * All Preferred IFR Routes are in Effect Continuously Unless Otherwise Noted. |
| `ROUTE_DIR_DESCRIP` | Route Direction Limitations Description |
| `DESIGNATOR` | Preferred Route Designator if applicable |
| `NAR_TYPE` | North American Route Type (COMMON, NON-COMMON) |
| `INLAND_FAC_FIX` | North American Route Inland NAV Facility or Fix is the Origin on COMMON EASTBOUND and NON-COMMON (Eastbound or Westbound) and the Destination on COMMON WESTBOUND. |
| `COASTAL_FIX` | North American Route Coastal Fix is the Origin on COMMON WESTBOUND and the Destination on COMMON EASTBOUND. |
| `DESTINATION` | North American Route Destination for NON_COMMON (Eastbound or Westbound). |
| `ROUTE_STRING` | Preferred Route String. *Canadian DPs and STARs will use the generic format of “-DP” and “-STAR”. See the Canadian Aeronautical Data for the correct amendment number for filing. |

[Complete `PFR_BASE` column reference](../csv-tables/pfr-base.md)
```

```{faa-dropdown} PreferredRouteFormatRecord raw fields — PFR_RMT_FMT (12)
`PreferredRouteFormatRecord` preserves one complete `PFR_RMT_FMT` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `Orig` | Origin Facility Location Identifier (Depending on NAR Type and Direction, Origin ID Is either Coastal Fix or Inland NAV Facility or Fix) |
| `Route String` | Preferred Route String which starts with Orig and ends with Dest. *Canadian DPs and STARs will use the generic format of “-DP” and “-STAR”. See the Canadian Aeronautical Data for the correct amendment number for filing. |
| `Dest` | Destination Facility Location Identifier (Depending on NAR Type and Direction, Destination ID Is either Airport, Coastal Fix or Inland NAV Facility or Fix) |
| `Hours1` | Effective Hours (GMT) Description * All Preferred IFR Routes are in Effect Continuously Unless Otherwise Noted. |
| `Type` | Type Code of Preferred Route Description. |
| `Area` | Preferred Route Area Description. |
| `Altitude` | Preferred Route Altitude Description. |
| `Aircraft` | Aircraft Allowed/Limitations Description |
| `Direction` | Route Direction Limitations Description |
| `Seq` | Route Identifier Sequence Number (1-99) |
| `DCNTR` | Departure ARTCC associated with a given PFR. |
| `ACNTR` | Arrival ARTCC associated with a given PFR. |

[Complete `PFR_RMT_FMT` column reference](../csv-tables/pfr-rmt-fmt.md)
```

```{faa-dropdown} PreferredRouteSegmentRecord raw fields — PFR_SEG (13)
`PreferredRouteSegmentRecord` preserves one complete `PFR_SEG` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ORIGIN_ID` | Origin Facility Location Identifier (Depending on NAR Type and Direction, Origin ID Is either Coastal Fix or Inland NAV Facility or Fix) |
| `DSTN_ID` | Destination Facility Location Identifier (Depending on NAR Type and Direction, Destination ID Is either Airport, Coastal Fix or Inland NAV Facility or Fix) |
| `PFR_TYPE_CODE` | Type Code of Preferred Route Description. |
| `ROUTE_NO` | Route Identifier Sequence Number (1-99) |
| `SEGMENT_SEQ` | A sequencing number in multiples of five for each SEG_VALUE. Segment Values are in order adapted for each Preferred Route. |
| `SEG_VALUE` | The Segment ID Value for each Element of the Route String from PFR_BASE. |
| `SEG_TYPE` | The Segment Type of the Segment ID Value. |
| `STATE_CODE` | This is the two letter state ID of the Segment Values that are within the US and are Type FIX, FRD, NAVAID or RADIAL. Segment Values outside the US or Types AIRWAY, DP or STAR are NULL. |
| `COUNTRY_CODE` | Country Code for Types FIX, FRD, NAVAID or RADIAL. Segment Value Types AIRWAY, DP or STAR are NULL. |
| `ICAO_REGION_CODE` | This is the two letter ICAO Region Code for FIX Segment Types only. |
| `NAV_TYPE` | Specific NAVAID Type for Segment Value Types NAVAID, RADIAL or FRD. |
| `NEXT_SEG` | The Segment ID Value of the Element that directly follows the current Segment Value. |

[Complete `PFR_SEG` column reference](../csv-tables/pfr-seg.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.departure.PreferredRoute
.. autoclass:: openNASR.departure.PreferredRouteRecord
.. autoclass:: openNASR.departure.PreferredRouteFormatRecord
.. autoclass:: openNASR.departure.PreferredRouteSegmentRecord
.. autoclass:: openNASR.departure.PreferredRouteRepository
```
