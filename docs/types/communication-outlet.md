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

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} CommunicationOutletRecord raw fields — COM (28)
`CommunicationOutletRecord` preserves one complete `COM` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `COMM_LOC_ID` | Communications Outlet Ident. A 3-4 character alphanumeric identifier. COMM_TYPE RCAG do not currently have a 3-4 character identifier stored in NASR. |
| `COMM_TYPE` | Communication Outlet Type – RCAG, RCO or RCO1. RCAG is a Remote Communications, Air/Ground. RCO and RCO1 are the same and Serve the Same Function; A Remote Communication Outlet. An RCO1 may exist if two separate sites share the same identifier, e.g. one is collocated with a NAVAID, the Other Is Physically on Airport Property. |
| `NAV_ID` | Associated NAVAID Ident - Applies to RCO/RCO1 types only. |
| `NAV_TYPE` | Associated NAVAID Type - Applies to RCO/RCO1 types only. |
| `CITY` | Communications Outlet City Name. RCAG do not have an Associated City stored in NASR. |
| `STATE_CODE` | Associated State Code standard two letter abbreviation for US States and Territories. |
| `REGION_CODE` | FAA Region responsible for Communications Outlet (code) |
| `COUNTRY_CODE` | Country Code Communications Outlet is Located. |
| `COMM_OUTLET_NAME` | Communications Outlet Name. The Communications Outlet Name is also used as the Communications Outlet Call. |
| `LAT_DEG` | Communications Outlet Latitude Degrees |
| `LAT_MIN` | Communications Outlet Latitude Minutes |
| `LAT_SEC` | Communications Outlet Latitude Seconds |
| `LAT_HEMIS` | Communications Outlet Latitude Hemisphere |
| `LAT_DECIMAL` | Communications Outlet Latitude in Decimal Format |
| `LONG_DEG` | Communications Outlet Longitude Degrees |
| `LONG_MIN` | Communications Outlet Longitude Minutes |
| `LONG_SEC` | Communications Outlet Longitude Seconds |
| `LONG_HEMIS` | Communications Outlet Longitude Hemisphere |
| `LONG_DECIMAL` | Communications Outlet Longitude in Decimal Format |
| `FACILITY_ID` | For RCO and RCO1, the Facility ID is the Associated Flight Service Station Ident. For RCAG, the Facility ID is the Associated ARTCC. |
| `FACILITY_NAME` | For RCO and RCO1, the Facility Name is the Associated Flight Service Station Name. For RCAG, the Facility Name is the Associated ARTCC Name. |
| `ALT_FSS_ID` | Associated Alternate Flight Service Station Ident - Applies to RCO/RCO1 types only. |
| `ALT_FSS_NAME` | Associated Alternate Flight Service Station Name - Applies to RCO/RCO1 types only. |
| `OPR_HRS` | Standard Time Zone - Applies to RCO/RCO1 types only. |
| `COMM_STATUS_CODE` | Communication Outlet Status - Applies to RCO/RCO1 types only. |
| `COMM_STATUS_DATE` | STATUS Date of Communications Outlet - Applies to RCO/RCO1 types only. |
| `REMARK` | Remark associated with Communications Outlet. |

[Complete `COM` column reference](../csv-tables/com.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.communications.CommunicationOutlet
.. autoclass:: openNASR.communications.CommunicationOutletRecord
.. autoclass:: openNASR.communications.CommunicationOutletRepository
```
