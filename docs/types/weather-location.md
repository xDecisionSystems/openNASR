# Weather location

A `WeatherLocation` combines one `WXL_BASE` location with its associated
`WXL_SVC` weather-service rows.

## Composite key

(`WEA_ID`, `CITY`, `STATE_CODE`, `COUNTRY_CODE`)

```python
location = nasr.weather_locations.get(weather_location_key)

location.record
location.services
```

Services are returned as an immutable tuple of lossless
`WeatherServiceRecord` objects.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} WeatherLocationRecord raw fields — WXL_BASE (17)
`WeatherLocationRecord` preserves one complete `WXL_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `WEA_ID` | Weather Reporting Location Identifier |
| `CITY` | Associated City Name |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `LAT_DEG` | Weather Reporting Location Latitude Degrees |
| `LAT_MIN` | Weather Reporting Location Latitude Minutes |
| `LAT_SEC` | Weather Reporting Location Latitude Seconds |
| `LAT_HEMIS` | Weather Reporting Location Latitude Hemisphere |
| `LAT_DECIMAL` | Weather Reporting Location Latitude in Decimal Format |
| `LONG_DEG` | Weather Reporting Location Longitude Degrees |
| `LONG_MIN` | Weather Reporting Location Longitude Minutes |
| `LONG_SEC` | Weather Reporting Location Longitude Seconds |
| `LONG_HEMIS` | Weather Reporting Location Longitude Hemisphere |
| `LONG_DECIMAL` | Weather Reporting Location Longitude in Decimal Format |
| `ELEV` | Weather Reporting Location Elevation - Value (Whole Feet MSL). |
| `SURVEY_METHOD_CODE` | Weather Reporting Location Elevation - Accuracy |

[Complete `WXL_BASE` column reference](../csv-tables/wxl-base.md)
```

```{faa-dropdown} WeatherServiceRecord raw fields — WXL_SVC (7)
`WeatherServiceRecord` preserves one complete `WXL_SVC` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `WEA_ID` | Weather Reporting Location Identifier |
| `CITY` | Associated City Name |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `COUNTRY_CODE` | Country Post Office Code |
| `WEA_SVC_TYPE_CODE` | Weather Services Available at Location |
| `WEA_AFFECT_AREA` | Affected State/Area. An Alphabetically Ordered Series of Two Character US State Post Office Abbreviations Separated by Commas. Values May Also Include LE, LH, LM, LO, LS for the Great Lakes (Erie, Huron, Michigan, Ontario, Superior) |

[Complete `WXL_SVC` column reference](../csv-tables/wxl-svc.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.weather.WeatherLocation
.. autoclass:: openNASR.weather.WeatherLocationRecord
.. autoclass:: openNASR.weather.WeatherServiceRecord
.. autoclass:: openNASR.weather.WeatherLocationRepository
```

