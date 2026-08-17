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

## Generated API

```{eval-rst}
.. autoclass:: openNASR.weather.AutomatedWeatherStation
.. autoclass:: openNASR.weather.AutomatedWeatherStationRecord
.. autoclass:: openNASR.weather.AutomatedWeatherStationRepository
```
