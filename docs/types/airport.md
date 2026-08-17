# Airport

An `AirportRecord` preserves one airport base row and attaches its runway,
runway-end, ILS, class-airspace, and military-operation relationships.

## FAA source tables

| Table | Related data |
| --- | --- |
| `APT_BASE` | Identity, name, position, elevation, and status |
| `APT_RWY` / `APT_RWY_END` | Runways and physical runway ends |
| `ILS_BASE` / `ILS_DME` / `ILS_GS` / `ILS_MKR` | Landing-system components |
| `CLS_ARSP` / `MIL_OPS` | Relationships through the complete airport site key |

## Lookup

```python
airport = nasr.airports.get("ATL")
same_airport = nasr.airports.get("KATL")

airport.faa_id
airport.runways
airport.ils
airport.class_airspace

# Plot runways, departures, and arrivals for this airport.
figure, axes = airport.plot(nasr)
```

FAA and ICAO identifiers are normalized case-insensitively. The modern
repository returns `AirportRecord`; `Airport` is the compatibility aggregate.

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} AirportRecord raw fields — APT_BASE (90)
`AirportRecord` preserves one complete `APT_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. |
| `SITE_TYPE_CODE` | Landing Facility Type Code. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `REGION_CODE` | FAA Region Code |
| `ADO_CODE` | FAA District or Field Office Code |
| `STATE_NAME` | Associated State Name |
| `COUNTY_NAME` | Associated County or Parish Name (For Non-Us Aerodromes This May Be Territory Or Province Name.) |
| `COUNTY_ASSOC_STATE` | Associated County's State (Post Office Code) State where the Associated County is located; may not be the same as the Associated City's State Code. For non-US Aerodrome Facilities, these "State" Codes are internal to this system and may not correspond to standard State or Country Codes in use elsewhere. |
| `ARPT_NAME` | Official Facility Name |
| `OWNERSHIP_TYPE_CODE` | Airport Ownership Type |
| `FACILITY_USE_CODE` | Facility Use |
| `LAT_DEG` | Airport Reference Point Latitude Degrees |
| `LAT_MIN` | Airport Reference Point Latitude Minutes |
| `LAT_SEC` | Airport Reference Point Latitude Seconds |
| `LAT_HEMIS` | Airport Reference Point Latitude Hemisphere |
| `LAT_DECIMAL` | Airport Reference Point Latitude in Decimal Format |
| `LONG_DEG` | Airport Reference Point Longitude Degrees |
| `LONG_MIN` | Airport Reference Point Longitude Minutes |
| `LONG_SEC` | Airport Reference Point Longitude Seconds |
| `LONG_HEMIS` | Airport Reference Point Longitude Hemisphere |
| `LONG_DECIMAL` | Airport Reference Point Longitude in Decimal Format |
| `SURVEY_METHOD_CODE` | Airport Reference Point Determination Method |
| `ELEV` | Airport Elevation (Nearest Tenth of a Foot MSL) Elevation is measured at the highest point on the centerline of the usable landing surface. |
| `ELEV_METHOD_CODE` | Airport Elevation Determination Method |
| `MAG_VARN` | Magnetic Variation |
| `MAG_HEMIS` | Magnetic Variation Direction |
| `MAG_VARN_YEAR` | Magnetic Variation Epoch Year |
| `TPA` | Traffic Pattern Altitude (Whole Feet AGL) |
| `CHART_NAME` | Aeronautical Sectional Chart on Which Facility Appears |
| `DIST_CITY_TO_AIRPORT` | Distance from Central Business District of the Associated City to the Airport |
| `DIRECTION_CODE` | Direction of Airport from Central Business District of Associated City (Nearest 1/8 Compass Point) |
| `ACREAGE` | Land Area Covered by Airport (Acres) |
| `RESP_ARTCC_ID` | Responsible ARTCC Identifier (The Responsible ARTCC Is The FAA Air Route Traffic Control Center Who Has Control Over The Airport.) |
| `COMPUTER_ID` | Responsible ARTCC (FAA) Computer Identifier |
| `ARTCC_NAME` | Responsible ARTCC Name |
| `FSS_ON_ARPT_FLAG` | Tie-In FSS Physically Located On Facility |
| `FSS_ID` | Tie-In Flight Service Station (FSS) Identifier |
| `FSS_NAME` | Tie-In FSS Name |
| `PHONE_NO` | Local Phone Number from Airport to FSS for Administrative Services |
| `TOLL_FREE_NO` | Toll Free Phone Number from Airport to FSS for Pilot Briefing Services |
| `ALT_FSS_ID` | Alternate FSS Identifier provides the identifier of a full-time Flight Service Station that assumes responsibility for the Airport during the off hours of a part-time primary FSS. |
| `ALT_FSS_NAME` | Alternate FSS Name |
| `ALT_TOLL_FREE_NO` | Toll Free Phone Number from Airport to Alternate FSS for Pilot Briefing Services |
| `NOTAM_ID` | Identifier of the Facility responsible for issuing Notices to Airmen (NOTAMS) and Weather information for the Airport |
| `NOTAM_FLAG` | Availability of NOTAM 'D' Service at Airport |
| `ACTIVATION_DATE` | Airport Activation Date (YYYY/MM) provides the YEAR and MONTH that the Facility was added to the NFDC airport database. Note: this information is only available for those Facilities opened since 1981. |
| `ARPT_STATUS` | Airport Status Code |
| `FAR_139_TYPE_CODE` | Airport ARFF Certification Type Code. Format is the class code ('I', 'II', 'III', or 'IV') followed by a one character code A, B, C, D, E, or L. Codes A, B, C, D, E are for Airports having a full certificate under CFR PART 139, and identifies the Aircraft Rescue and Firefighting index for the Airport. |
| `FAR_139_CARRIER_SER_CODE` | Airport ARFF Certification Carrier Service Code. Code S is for Airports receiving scheduled Air Carrier Service from carriers certificated by the Civil Aeronautics Board. Code U is for Airports not receiving this scheduled service. |
| `ARFF_CERT_TYPE_DATE` | Airport ARFF Certification Date (YYYY/MM) |
| `NASP_CODE` | NPIAS/Federal Agreements Code. A Combination of 1 to 7 Codes that Indicate the Type of Federal Agreements existing at the Airport. |
| `ASP_ANLYS_DTRM_CODE` | Airport Airspace Analysis Determination |
| `CUST_FLAG` | Facility has been designated by the U.S. Department of Homeland Security as an International Airport of Entry for Customs |
| `LNDG_RIGHTS_FLAG` | Facility has been designated by the U.S. Department of Homeland Security as a Customs Landing Rights Airport. (Customs User Fee Airports will be designated with an E80, E80A, or E80C referenced remark "US CUSTOMS USER FEE ARPT.") |
| `JOINT_USE_FLAG` | Facility has Military/Civil Joint Use Agreement that allows Civil Operations at a Military Airport. |
| `MIL_LNDG_FLAG` | Airport has entered into an Agreement that Grants Landing Rights to the Military |
| `INSPECT_METHOD_CODE` | Airport Inspection Method |
| `INSPECTOR_CODE` | Agency/Group Performing Physical Inspection |
| `LAST_INSPECTION` | Last Physical Inspection Date (YYYY/MM/DD) |
| `LAST_INFO_RESPONSE` | Last Date Information Request was completed by Facility Owner or Manager (YYYY/MM/DD) |
| `FUEL_TYPES` | Fuel Types available for public use at the Airport. |
| `AIRFRAME_REPAIR_SER_CODE` | Airframe Repair Service Availability/Type |
| `PWR_PLANT_REPAIR_SER` | Power Plant (Engine) Repair Availability/Type |
| `BOTTLED_OXY_TYPE` | Type of Bottled Oxygen Available (Value represents High and/or Low Pressure Replacement Bottle) |
| `BULK_OXY_TYPE` | Type of Bulk Oxygen Available (Value represents High and/or Low Pressure Cylinders) |
| `LGT_SKED` | Airport Lighting Schedule value is the beginning-ending times (local time) that the Standard Airport Lights are operated. Value can be "SS-SR" (indicating sunset-sunrise), blank, or "SEE RMK", indicating that the details are in a facility remark data entry. |
| `BCN_LGT_SKED` | Beacon Lighting Schedule value is the beginning-ending times (local time) that the Rotating Airport Beacon Light is operated. Value can be "SS-SR" (indicating sunset-sunrise), blank, or "SEE RMK", indicating that the details are in a facility remark data entry. |
| `TWR_TYPE_CODE` | Air Traffic Control Tower Facility Type (ATCT, NON-ATCT, ATCT-A/C, ATCT-RAPCON, ATCT-RATCF, ATCT-TRACON, TRACON). NON-ATCT is equivalent to “N” ATC TOWER at Airport. All Other are equivalent to “Y” ATC TOWER at AIRPORT. |
| `SEG_CIRCLE_MKR_FLAG` | Segmented Circle Airport Marker System on the Airport |
| `BCN_LENS_COLOR` | Lens Color of Operable Beacon located on the Airport |
| `LNDG_FEE_FLAG` | Landing Fee charged to Non-Commercial Users of Airport |
| `MEDICAL_USE_FLAG` | A "Y" in this field indicates that the Landing Facility Is used for Medical Purposes |
| `ARPT_PSN_SOURCE` | Airport Position Source |
| `POSITION_SRC_DATE` | Airport Position Source Date (YYYY/MM/DD) |
| `ARPT_ELEV_SOURCE` | Airport Elevation Source |
| `ELEVATION_SRC_DATE` | Airport Elevation Source Date (YYYY/MM/DD) |
| `CONTR_FUEL_AVBL` | Contract Fuel Available |
| `TRNS_STRG_BUOY_FLAG` | Buoy Transient Storage Facilities |
| `TRNS_STRG_HGR_FLAG` | Hangar Transient Storage Facilities |
| `TRNS_STRG_TIE_FLAG` | Tie-Down Transient Storage Facilities |
| `OTHER_SERVICES` | Other Airport Services Available. A Comma-Separated List of Other Airport Services Available at the Airport, which include: |
| `WIND_INDCR_FLAG` | Wind Indicator shows whether a Wind Indicator exists at the Airport |
| `ICAO_ID` | ICAO Identifier |
| `MIN_OP_NETWORK` | Minimum Operational Network (MON) |
| `USER_FEE_FLAG` | If Flag is checked in NASR, User Fee Airports Will Be Designated With Text "US CUSTOMS USER FEE ARPT." |
| `CTA` | Cold Temperature Airport. Altitude Correction Required At or Below Temperature Given in Celsius. |

[Complete `APT_BASE` column reference](../csv-tables/apt-base.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.airport.AirportRecord
.. autoclass:: openNASR.repository.AirportRepository
.. autoclass:: openNASR.airport.Airport
```
