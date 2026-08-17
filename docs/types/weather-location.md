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

## Generated API

```{eval-rst}
.. autoclass:: openNASR.weather.WeatherLocation
.. autoclass:: openNASR.weather.WeatherLocationRecord
.. autoclass:: openNASR.weather.WeatherServiceRecord
.. autoclass:: openNASR.weather.WeatherLocationRepository
```
