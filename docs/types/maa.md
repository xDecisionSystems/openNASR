# Miscellaneous Activity Area

A `Maa` represents an FAA Miscellaneous Activity Area, such as an aerobatic,
glider, space-launch, ultralight, or unmanned-aircraft activity area. It is not
a military-airspace abbreviation.

## FAA source tables

| Table | Content |
| --- | --- |
| `MAA_BASE` | Identity, activity type, location, and operating data |
| `MAA_CON` | Contacts |
| `MAA_RMK` | Remarks |
| `MAA_SHP` | Ordered geometry points |

The lookup key is `MAA_ID`.

```python
area = nasr.maas.get(maa_id)

area.record
area.contacts
area.remarks
area.geometry
```

`geometry` is `None` for radius-only areas without published shape rows.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} MaaRecord raw fields — MAA_BASE (24)
`MaaRecord` preserves one complete `MAA_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. |
| `MAA_TYPE_NAME` | Type of Miscellaneous Activity Area |
| `NAV_ID` | NAVAID Facility Identifier with which MAA is Associated. |
| `NAV_TYPE` | NAVAID Facility Type with which the MAA is Associated. |
| `NAV_RADIAL` | Azimuth (Degrees) From NAVAID (0-359.99) |
| `NAV_DISTANCE` | Distance, In Nautical Miles, From NAVAID |
| `STATE_CODE` | MAA State Abbreviation (Two-Letter Post Office) |
| `CITY` | MAA Associated City Name |
| `LATITUDE` | MAA Latitude (Formatted) |
| `LONGITUDE` | MAA Longitude (Formatted) |
| `ARPT_IDS` | LIST of Landing Facility Identifiers with which MAA is Associated. |
| `NEAREST_ARPT` | Nearest Airport ID Only Applies to Space Launch Activity Areas |
| `NEAREST_ARPT_DIST` | Nearest Airport Distance in Nautical Miles Only Applies to Space Launch Activity Areas |
| `NEAREST_ARPT_DIR` | Nearest Airport Direction Only Applies to Space Launch Activity Areas |
| `MAA_NAME` | MAA Area Name |
| `MAX_ALT` | MAA Maximum Altitude Allowed |
| `MIN_ALT` | MAA Minimum Altitude Allowed |
| `MAA_RADIUS` | MAA Area Radius, in Nautical Miles from Center Point |
| `DESCRIPTION` | Additional Descriptive Text for MAA Area |
| `MAA_USE` | MAA Use Description |
| `CHECK_NOTAMS` | Check for NOTAMs Only Applies to Space Launch Activity Areas |
| `TIME_OF_USE` | Times of Use Description |
| `USER_GROUP_NAME` | MAA User Group Name and Description |

[Complete `MAA_BASE` column reference](../csv-tables/maa-base.md)
```

```{faa-dropdown} MaaContactRecord raw fields — MAA_CON (9)
`MaaContactRecord` preserves one complete `MAA_CON` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. |
| `FREQ_SEQ` | Unique Sequence number for Frequency Contact entries |
| `FAC_ID` | Contact Facility Identifier |
| `FAC_NAME` | Contact Facility Name |
| `COMMERCIAL_FREQ` | Commercial Frequency |
| `COMMERCIAL_CHART_FLAG` | Commercial Chart Flag |
| `MIL_FREQ` | Military Frequency |
| `MIL_CHART_FLAG` | Military Chart Flag |

[Complete `MAA_CON` column reference](../csv-tables/maa-con.md)
```

```{faa-dropdown} MaaRemarkRecord raw fields — MAA_RMK (6)
`MaaRemarkRecord` preserves one complete `MAA_RMK` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. |
| `TAB_NAME` | NASR table name associated with the remark. |
| `REF_COL_NAME` | NASR column name associated with the remark; identifies a general remark when no specific source column applies. |
| `REF_COL_SEQ_NO` | Sequence number of the source record associated with the remark. |
| `REMARK` | Free-form FAA remark text associated with the record or referenced field. |

[Complete `MAA_RMK` column reference](../csv-tables/maa-rmk.md)
```

```{faa-dropdown} MaaShapePointRecord raw fields — MAA_SHP (5)
`MaaShapePointRecord` preserves one complete `MAA_SHP` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `MAA_ID` | MAA ID that uniquely identifies a Miscellaneous Activity Area. |
| `POINT_SEQ` | Unique Sequence number for MAA Polygon Coordinates. |
| `LATITUDE` | MAA Polygon Coordinate Latitude (Formatted) |
| `LONGITUDE` | MAA Polygon Coordinate Longitude (Formatted) |

[Complete `MAA_SHP` column reference](../csv-tables/maa-shp.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airspace.Maa
.. autoclass:: openNASR.airspace.MaaRecord
.. autoclass:: openNASR.airspace.MaaContactRecord
.. autoclass:: openNASR.airspace.MaaRemarkRecord
.. autoclass:: openNASR.airspace.MaaShapePointRecord
.. autoclass:: openNASR.airspace.MaaRepository
```
