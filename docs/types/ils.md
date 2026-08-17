# Instrument landing system

Instrument landing system records are attached to an `AirportRecord` and
preserve the FAA's separate base, DME, glide-slope, and marker rows.

## FAA source tables

| Table | Record type |
| --- | --- |
| `ILS_BASE` | `IlsRecord` |
| `ILS_DME` | `DmeRecord` |
| `ILS_GS` | `GlideSlopeRecord` |
| `ILS_MKR` | `MarkerRecord` |

## Access

```python
airport = nasr.airports.get("ATL")

airport.ils
airport.dmes
airport.glide_slopes
airport.markers
```

The related tuples preserve FAA source order and raw source values.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} IlsRecord raw fields — ILS_BASE (36)
`IlsRecord` preserves one complete `ILS_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code |
| `RWY_END_ID` | ILS Runway End Identifier |
| `ILS_LOC_ID` | ILS Identification |
| `SYSTEM_TYPE_CODE` | ILS System Type. |
| `STATE_NAME` | Associated State Name |
| `REGION_CODE` | FAA Region responsible for NAVAID (code) |
| `RWY_LEN` | ILS Runway Length in Whole Feet |
| `RWY_WIDTH` | ILS Runway Width in Whole Feet |
| `CATEGORY` | Category of the ILS |
| `OWNER` | A Concatenation of the ILS OWNER CODE - ILS OWNER NAME |
| `OPERATOR` | A Concatenation of the ILS OPERATOR CODE - ILS OPERATOR NAME |
| `APCH_BEAR` | ILS Approach Bearing in Degrees Magnetic |
| `MAG_VAR` | Magnetic Variation Degrees |
| `MAG_VAR_HEMIS` | Magnetic Variation Direction |
| `COMPONENT_STATUS` | Operational Status of Localizer |
| `COMPONENT_STATUS_DATE` | Effective Date of Localizer Operational Status |
| `LAT_DEG` | Localizer Antenna Latitude Degrees |
| `LAT_MIN` | Localizer Antenna Latitude Minutes |
| `LAT_SEC` | Localizer Antenna Latitude Seconds |
| `LAT_HEMIS` | Localizer Antenna Latitude Hemisphere |
| `LAT_DECIMAL` | Localizer Antenna Latitude in Decimal Format |
| `LONG_DEG` | Localizer Antenna Longitude Degrees |
| `LONG_MIN` | Localizer Antenna Longitude Minutes |
| `LONG_SEC` | Localizer Antenna Longitude Seconds |
| `LONG_HEMIS` | Localizer Antenna Longitude Hemisphere |
| `LONG_DECIMAL` | Localizer Antenna Longitude in Decimal Format |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information |
| `SITE_ELEVATION` | Site Elevation of Localizer Antenna in Tenth of a Foot (MSL). |
| `LOC_FREQ` | Localizer Frequency (MHZ) |
| `BK_COURSE_STATUS_CODE` | Localizer Back Course Status |

[Complete `ILS_BASE` column reference](../csv-tables/ils-base.md)
```

```{faa-dropdown} DmeRecord raw fields — ILS_DME (25)
`DmeRecord` preserves one complete `ILS_DME` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code |
| `RWY_END_ID` | ILS Runway End Identifier |
| `ILS_LOC_ID` | ILS Identification |
| `SYSTEM_TYPE_CODE` | ILS System Type. |
| `COMPONENT_STATUS` | Operational Status of DME |
| `COMPONENT_STATUS_DATE` | Effective Date of DME Operational Status |
| `LAT_DEG` | DME Transponder Antenna Latitude Degrees |
| `LAT_MIN` | DME Transponder Antenna Latitude Minutes |
| `LAT_SEC` | DME Transponder Antenna Latitude Seconds |
| `LAT_HEMIS` | DME Transponder Antenna Latitude Hemisphere |
| `LAT_DECIMAL` | DME Transponder Antenna Latitude in Decimal Format |
| `LONG_DEG` | DME Transponder Antenna Longitude Degrees |
| `LONG_MIN` | DME Transponder Antenna Longitude Minutes |
| `LONG_SEC` | DME Transponder Antenna Longitude Seconds |
| `LONG_HEMIS` | DME Transponder Antenna Longitude Hemisphere |
| `LONG_DECIMAL` | DME Transponder Antenna Longitude in Decimal Format |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information |
| `SITE_ELEVATION` | Site Elevation of DME Transponder Antenna in Tenth of a Foot (MSL). |
| `CHANNEL` | NAS Channel on Which Distance Data is Transmitted |

[Complete `ILS_DME` column reference](../csv-tables/ils-dme.md)
```

```{faa-dropdown} GlideSlopeRecord raw fields — ILS_GS (27)
`GlideSlopeRecord` preserves one complete `ILS_GS` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code |
| `RWY_END_ID` | ILS Runway End Identifier |
| `ILS_LOC_ID` | ILS Identification |
| `SYSTEM_TYPE_CODE` | ILS System Type. |
| `COMPONENT_STATUS` | Operational Status of Glide Slope |
| `COMPONENT_STATUS_DATE` | Effective Date of Glide Slope Operational Status |
| `LAT_DEG` | Glide Slope Transmitter Antenna Latitude Degrees |
| `LAT_MIN` | Glide Slope Transmitter Antenna Latitude Minutes |
| `LAT_SEC` | Glide Slope Transmitter Antenna Latitude Seconds |
| `LAT_HEMIS` | Glide Slope Transmitter Antenna Latitude Hemisphere |
| `LAT_DECIMAL` | Glide Slope Transmitter Antenna Latitude in Decimal Format |
| `LONG_DEG` | Glide Slope Transmitter Antenna Longitude Degrees |
| `LONG_MIN` | Glide Slope Transmitter Antenna Longitude Minutes |
| `LONG_SEC` | Glide Slope Transmitter Antenna Longitude Seconds |
| `LONG_HEMIS` | Glide Slope Transmitter Antenna Longitude Hemisphere |
| `LONG_DECIMAL` | Glide Slope Transmitter Antenna Longitude in Decimal Format |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information |
| `SITE_ELEVATION` | Site Elevation of Glide Slope Transmitter Antenna in Tenth of a Foot (MSL). |
| `G_S_TYPE_CODE` | Glide Slope Class/Type |
| `G_S_ANGLE` | Glide Slope Angle in Degrees and Hundredths of Degree |
| `G_S_FREQ` | Glide Slope Transmission Frequency |

[Complete `ILS_GS` column reference](../csv-tables/ils-gs.md)
```

```{faa-dropdown} MarkerRecord raw fields — ILS_MKR (32)
`MarkerRecord` preserves one complete `ILS_MKR` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code |
| `RWY_END_ID` | ILS Runway End Identifier |
| `ILS_LOC_ID` | ILS Identification |
| `SYSTEM_TYPE_CODE` | ILS System Type. |
| `ILS_COMP_TYPE_CODE` | Marker Type (IM - Inner Marker, MM - Middle Marker, OM - Outer Marker) |
| `COMPONENT_STATUS` | Operational Status of Marker Beacon |
| `COMPONENT_STATUS_DATE` | Effective Date of Marker Beacon Operational Status |
| `LAT_DEG` | Marker Beacon Latitude Degrees |
| `LAT_MIN` | Marker Beacon Latitude Minutes |
| `LAT_SEC` | Marker Beacon Latitude Seconds |
| `LAT_HEMIS` | Marker Beacon Latitude Hemisphere |
| `LAT_DECIMAL` | Marker Beacon Latitude in Decimal Format |
| `LONG_DEG` | Marker Beacon Longitude Degrees |
| `LONG_MIN` | Marker Beacon Longitude Minutes |
| `LONG_SEC` | Marker Beacon Longitude Seconds |
| `LONG_HEMIS` | Marker Beacon Longitude Hemisphere |
| `LONG_DECIMAL` | Marker Beacon Longitude in Decimal Format |
| `LAT_LONG_SOURCE_CODE` | Code Indication Source of Latitude/Longitude Information |
| `SITE_ELEVATION` | Site Elevation of Marker Beacon in Tenth of a Foot (MSL). |
| `MKR_FAC_TYPE_CODE` | Facility/Type of Marker/Locator |
| `MARKER_ID_BEACON` | Location Identifier of Beacon at Marker |
| `COMPASS_LOCATOR_NAME` | Name of the Marker Locator Beacon |
| `FREQ` | NAVAID Frequency when Marker is collocated else Locator Frequency (in KHZ) |
| `NAV_ID` | Location Identifier of Navigation Aid Collocated With Marker (Blank Indicates Marker Is Not Collocated With A NAVAID) |
| `NAV_TYPE` | Collocated NAVAID Type |
| `LOW_POWERED_NDB_STATUS` | Low Powered NDB Status of Marker Beacon |

[Complete `ILS_MKR` column reference](../csv-tables/ils-mkr.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.ils.IlsRecord
.. autoclass:: openNASR.ils.DmeRecord
.. autoclass:: openNASR.ils.GlideSlopeRecord
.. autoclass:: openNASR.ils.MarkerRecord
.. autoclass:: openNASR.ils.ILSBase
.. autoclass:: openNASR.ils.ILSDME
.. autoclass:: openNASR.ils.ILSGS
.. autoclass:: openNASR.ils.ILSMKR
```

