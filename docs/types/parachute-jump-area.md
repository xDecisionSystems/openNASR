# Parachute Jump Area

A `ParachuteJumpArea` combines one published jump-area record with its contacts
and, when the FAA relationship is present, its associated airport.

## FAA source tables

| Table | Content |
| --- | --- |
| `PJA_BASE` | Identity, center point, radius, and operating data |
| `PJA_CON` | Contact records |
| `APT_BASE` | Optional airport relationship |

The lookup key is `PJA_ID`.

```python
area = nasr.parachute_jump_areas.get(pja_id)

area.record
area.contacts
area.airport
```

FAA jump areas are represented by center and radius data rather than a
published polygon table.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} ParachuteJumpAreaRecord raw fields — PJA_BASE (30)
`ParachuteJumpAreaRecord` preserves one complete `PJA_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `PJA_ID` | PJA ID that uniquely identifies a Parachute Jump Area. |
| `NAV_ID` | NAVAID Facility Identifier with which PJA is Associated. |
| `NAV_TYPE` | NAVAID Facility Type with which the PJA is Associated. |
| `RADIAL` | Azimuth (Degrees) From NAVAID (0-359.99) |
| `DISTANCE` | Distance, In Nautical Miles, From NAVAID |
| `NAVAID_NAME` | Name of NAVAID with which PJA is Associated. |
| `STATE_CODE` | PJA State Abbreviation (Two-Letter Post Office) |
| `CITY` | PJA Associated City Name |
| `LATITUDE` | PJA Latitude (Formatted) |
| `LAT_DECIMAL` | PJA Latitude in Decimal Format |
| `LONGITUDE` | PJA Longitude (Formatted) |
| `LONG_DECIMAL` | PJA Longitude in Decimal Format |
| `ARPT_ID` | Landing Facility Identifier with which PJA is Associated. |
| `SITE_NO` | Site Number of Associated Landing Facility |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `DROP_ZONE_NAME` | PJA Drop Zone Name |
| `MAX_ALTITUDE` | PJA Maximum Altitude Allowed |
| `MAX_ALTITUDE_TYPE_CODE` | PJA Maximum Altitude Allowed Type (AGL, MSL, UNR) |
| `PJA_RADIUS` | PJA Area Radius, in Nautical Miles from Center Point |
| `CHART_REQUEST_FLAG` | Sectional Charting Required (Y/N) |
| `PUBLISH_CRITERIA` | PJA to be Published in Airport/Facility Directory (Y/N) |
| `DESCRIPTION` | Additional Descriptive Text for PJA Area |
| `TIME_OF_USE` | Times of Use Description |
| `FSS_ID` | FSS Ident with which PJA is Associated |
| `FSS_NAME` | FSS Name with which PJA is Associated |
| `PJA_USE` | PJA Use Description |
| `VOLUME` | PJA Area Volume |
| `PJA_USER` | PJA User Group Name and Description |
| `REMARK` | Remark Text (Free Form Text that further describes a PJA.) |

[Complete `PJA_BASE` column reference](../csv-tables/pja-base.md)
```

```{faa-dropdown} ParachuteJumpAreaContactRecord raw fields — PJA_CON (11)
`ParachuteJumpAreaContactRecord` preserves one complete `PJA_CON` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `PJA_ID` | PJA ID that uniquely identifies a Parachute Jump Area. |
| `FAC_ID` | Contact Facility Identifier |
| `FAC_NAME` | Contact Facility Name |
| `LOC_ID` | Related Location Identifier |
| `COMMERCIAL_FREQ` | Commercial Frequency |
| `COMMERCIAL_CHART_FLAG` | Commercial Chart Flag |
| `MIL_FREQ` | Military Frequency |
| `MIL_CHART_FLAG` | Military Chart Flag |
| `SECTOR` | Sector Description Text |
| `CONTACT_FREQ_ALTITUDE` | Altitude Description Text |

[Complete `PJA_CON` column reference](../csv-tables/pja-con.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.ParachuteJumpArea
.. autoclass:: openNASR.airspace.ParachuteJumpAreaRecord
.. autoclass:: openNASR.airspace.ParachuteJumpAreaContactRecord
.. autoclass:: openNASR.airspace.ParachuteJumpAreaRepository
```

