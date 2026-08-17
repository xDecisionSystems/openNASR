# Automated weather station

An `AutomatedWeatherStation` wraps one standalone FAA `AWOS` row representing
an ASOS/AWOS installation.

## Composite key

(`ASOS_AWOS_ID`, `ASOS_AWOS_TYPE`, `STATE_CODE`, `CITY`, `COUNTRY_CODE`)

```python
station = nasr.weather_stations.get(weather_station_key)
record = station.record
```

The complete key prevents collisions between similarly named stations in
different locations or of different published types.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} AutomatedWeatherStationRecord raw fields — AWOS (25)
`AutomatedWeatherStationRecord` preserves one complete `AWOS` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `ASOS_AWOS_ID` | Weather System Identifier. Unique 3-4 character alphanumeric identifier. |
| `ASOS_AWOS_TYPE` | Weather System Type. |
| `STATE_CODE` | Associated State Code standard two letter abbreviation for US States and Territories. |
| `CITY` | Weather System associated City Name. |
| `COUNTRY_CODE` | Country Code Weather System is Located. |
| `COMMISSIONED_DATE` | Decommissioned Weather systems are not included so Dates given are for Commissioning Dates. |
| `NAVAID_FLAG` | Weather associated with NAVAID – Y/N Flag. |
| `LAT_DEG` | Weather System Latitude Degrees |
| `LAT_MIN` | Weather System Latitude Minutes |
| `LAT_SEC` | Weather System Latitude Seconds |
| `LAT_HEMIS` | Weather System Latitude Hemisphere |
| `LAT_DECIMAL` | Weather System Latitude in Decimal Format |
| `LONG_DEG` | Weather System Longitude Degrees |
| `LONG_MIN` | Weather System Longitude Minutes |
| `LONG_SEC` | Weather System Longitude Seconds |
| `LONG_HEMIS` | Weather System Longitude Hemisphere |
| `LONG_DECIMAL` | Weather System Longitude in Decimal Format |
| `ELEV` | Weather System Elevation (Nearest Tenth of a Foot) |
| `SURVEY_METHOD_CODE` | Weather System Location Determination Method |
| `PHONE_NO` | Weather System Telephone Number |
| `SECOND_PHONE_NO` | Weather System Second Telephone Number |
| `SITE_NO` | Landing Facility Site Number when Weather System Located at Airport. |
| `SITE_TYPE_CODE` | Landing Facility Type Code when Weather System Located at Airport. |
| `REMARK` | Remark associated with Weather System. |

[Complete `AWOS` column reference](../csv-tables/awos.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.weather.AutomatedWeatherStation
.. autoclass:: openNASR.weather.AutomatedWeatherStationRecord
.. autoclass:: openNASR.weather.AutomatedWeatherStationRepository
```

