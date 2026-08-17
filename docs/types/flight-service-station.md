# Flight Service Station

A `FlightServiceStation` combines one `FSS_BASE` station record with its
source-ordered `FSS_RMK` remarks.

## Composite key

(`FSS_ID`, `NAME`, `CITY`, `STATE_CODE`, `COUNTRY_CODE`)

```python
station = nasr.flight_service_stations.get(fss_key)

station.record
station.remarks
```

Using the complete key avoids treating a short station identifier as globally
unique.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} FlightServiceStationRecord raw fields — FSS_BASE (25)
`FlightServiceStationRecord` preserves one complete `FSS_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `FSS_ID` | Flight Service Station Identifier |
| `NAME` | Flight Service Station Name |
| `UPDATE_DATE` | Last Date on which the Record was updated. |
| `FSS_FAC_TYPE` | Facility Type: Flight Service Station (FSS), FS21 HUB Station (HUB) or FS21 Radio Service Area (RADIO). |
| `VOICE_CALL` | FSS Voice Call |
| `CITY` | Associated City Name |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `LAT_DEG` | Flight Service Station Latitude Degrees |
| `LAT_MIN` | Flight Service Station Latitude Minutes |
| `LAT_SEC` | Flight Service Station Latitude Seconds |
| `LAT_HEMIS` | Flight Service Station Latitude Hemisphere |
| `LAT_DECIMAL` | Flight Service Station Latitude in Decimal Format |
| `LONG_DEG` | Flight Service Station Longitude Degrees |
| `LONG_MIN` | Flight Service Station Longitude Minutes |
| `LONG_SEC` | Flight Service Station Longitude Seconds |
| `LONG_HEMIS` | Flight Service Station Longitude Hemisphere |
| `LONG_DECIMAL` | Flight Service Station Longitude in Decimal Format |
| `OPR_HOURS` | FSS Hours of Operation |
| `FAC_STATUS` | Status of Facility |
| `ALTERNATE_FSS` | If the Record Facility does not have Circuit B Teletype Capable of Transmitting/Receiving Flight Plan Messages then Alternate FSS with this Capability listed. |
| `WEA_RADAR_FLAG` | Availability of Weather Radar |
| `PHONE_NO` | Telephone Number used to reach FSS. |
| `TOLL_FREE_NO` | Toll Free Telephone Number used to reach FSS. |

[Complete `FSS_BASE` column reference](../csv-tables/fss-base.md)
```

```{faa-dropdown} FlightServiceStationRemarkRecord raw fields — FSS_RMK (9)
`FlightServiceStationRemarkRecord` preserves one complete `FSS_RMK` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `FSS_ID` | Flight Service Station Identifier |
| `NAME` | Flight Service Station Name |
| `CITY` | Associated City Name |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `REF_COL_NAME` | NASR Column name associated with Remark. Non-specific remarks identified as GENERAL_REMARK. |
| `REF_COL_SEQ_NO` | Sequence number assigned to Reference Column Remark |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) |

[Complete `FSS_RMK` column reference](../csv-tables/fss-rmk.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.fss.FlightServiceStation
.. autoclass:: openNASR.fss.FlightServiceStationRecord
.. autoclass:: openNASR.fss.FlightServiceStationRemarkRecord
.. autoclass:: openNASR.fss.FlightServiceStationRepository
```

