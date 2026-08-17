# `APT_BASE`

Core landing-facility identity, location, ownership, operational, and services information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. | Text, up to 9 characters | Not specified by FAA | No | `00103.` |
| `SITE_TYPE_CODE` | Landing Facility Type Code. | Text, up to 1 character | Not applicable | No | `A` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `AL` |
| `ARPT_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility. | Text, up to 4 characters | Not applicable | No | `0J0` |
| `CITY` | Airport Associated City Name | Text, up to 40 characters | Not applicable | No | `ABBEVILLE` |
| `COUNTRY_CODE` | Country Post Office Code Airport Located | Text, up to 2 characters | Not applicable | No | `US` |
| `REGION_CODE` | FAA Region Code | Text, up to 3 characters | Not applicable | Yes | `ASO` |
| `ADO_CODE` | FAA District or Field Office Code | Text, up to 3 characters | Not applicable | Yes | `JAN` |
| `STATE_NAME` | Associated State Name | Text, up to 30 characters | Not applicable | Yes | `ALABAMA` |
| `COUNTY_NAME` | Associated County or Parish Name (For Non-Us Aerodromes This May Be Territory Or Province Name.) | Text, up to 21 characters | Not applicable | No | `HENRY` |
| `COUNTY_ASSOC_STATE` | Associated County's State (Post Office Code) State where the Associated County is located; may not be the same as the Associated City's State Code. For non-US Aerodrome Facilities, these "State" Codes are internal to this system and may not correspond to standard State or Country Codes in use elsewhere. | Text, up to 2 characters | Not applicable | No | `AL` |
| `ARPT_NAME` | Official Facility Name | Text, up to 50 characters | Not applicable | No | `ABBEVILLE MUNI` |
| `OWNERSHIP_TYPE_CODE` | Airport Ownership Type | Text, up to 2 characters | Not applicable | No | `PU` |
| `FACILITY_USE_CODE` | Facility Use | Text, up to 2 characters | Not applicable | No | `PU` |
| `LAT_DEG` | Airport Reference Point Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `31` |
| `LAT_MIN` | Airport Reference Point Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `36` |
| `LAT_SEC` | Airport Reference Point Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `6.193` |
| `LAT_HEMIS` | Airport Reference Point Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | Airport Reference Point Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `31.60172027` |
| `LONG_DEG` | Airport Reference Point Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `85` |
| `LONG_MIN` | Airport Reference Point Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `14` |
| `LONG_SEC` | Airport Reference Point Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `18.761` |
| `LONG_HEMIS` | Airport Reference Point Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | Airport Reference Point Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-85.23854472` |
| `SURVEY_METHOD_CODE` | Airport Reference Point Determination Method | Text, up to 1 character | Not applicable | Yes | `E` |
| `ELEV` | Airport Elevation (Nearest Tenth of a Foot MSL) Elevation is measured at the highest point on the centerline of the usable landing surface. | Numeric (6,1) (precision, scale) | feet MSL | No | `468.3` |
| `ELEV_METHOD_CODE` | Airport Elevation Determination Method | Text, up to 1 character | Not applicable | Yes | `E` |
| `MAG_VARN` | Magnetic Variation | Numeric (2,0) (precision, scale) | Not specified by FAA | Yes | `1` |
| `MAG_HEMIS` | Magnetic Variation Direction | Text, up to 1 character | Not applicable | Yes | `W` |
| `MAG_VARN_YEAR` | Magnetic Variation Epoch Year | Numeric (4,0) (precision, scale) | Not applicable | Yes | `1985` |
| `TPA` | Traffic Pattern Altitude (Whole Feet AGL) | Numeric (4,0) (precision, scale) | feet AGL | Yes | `800` |
| `CHART_NAME` | Aeronautical Sectional Chart on Which Facility Appears | Text, up to 30 characters | Not applicable | Yes | `NEW ORLEANS` |
| `DIST_CITY_TO_AIRPORT` | Distance from Central Business District of the Associated City to the Airport | Numeric (2,0) (precision, scale) | Not applicable | Yes | `3` |
| `DIRECTION_CODE` | Direction of Airport from Central Business District of Associated City (Nearest 1/8 Compass Point) | Text, up to 3 characters | Not applicable | Yes | `N` |
| `ACREAGE` | Land Area Covered by Airport (Acres) | Numeric (5,0) (precision, scale) | acres | Yes | `36` |
| `RESP_ARTCC_ID` | Responsible ARTCC Identifier (The Responsible ARTCC Is The FAA Air Route Traffic Control Center Who Has Control Over The Airport.) | Text, up to 4 characters | Not applicable | No | `ZJX` |
| `COMPUTER_ID` | Responsible ARTCC (FAA) Computer Identifier | Text, up to 3 characters | Not applicable | No | `ZCJ` |
| `ARTCC_NAME` | Responsible ARTCC Name | Text, up to 30 characters | Not applicable | No | `JACKSONVILLE` |
| `FSS_ON_ARPT_FLAG` | Tie-In FSS Physically Located On Facility | Text, up to 1 character | Not applicable | Yes | `N` |
| `FSS_ID` | Tie-In Flight Service Station (FSS) Identifier | Text, up to 4 characters | Not applicable | No | `ANB` |
| `FSS_NAME` | Tie-In FSS Name | Text, up to 30 characters | Not applicable | No | `ANNISTON` |
| `PHONE_NO` | Local Phone Number from Airport to FSS for Administrative Services | Text, up to 16 characters | Not specified by FAA | Yes | `703-724-4288` |
| `TOLL_FREE_NO` | Toll Free Phone Number from Airport to FSS for Pilot Briefing Services | Text, up to 16 characters | Not specified by FAA | Yes | `1-800-WX-BRIEF` |
| `ALT_FSS_ID` | Alternate FSS Identifier provides the identifier of a full-time Flight Service Station that assumes responsibility for the Airport during the off hours of a part-time primary FSS. | Text, up to 4 characters | Not applicable | Yes | `ENA` |
| `ALT_FSS_NAME` | Alternate FSS Name | Text, up to 30 characters | Not applicable | Yes | `KENAI` |
| `ALT_TOLL_FREE_NO` | Toll Free Phone Number from Airport to Alternate FSS for Pilot Briefing Services | Text, up to 16 characters | Not specified by FAA | Yes | `1-866-864-1737` |
| `NOTAM_ID` | Identifier of the Facility responsible for issuing Notices to Airmen (NOTAMS) and Weather information for the Airport | Text, up to 4 characters | Not applicable | Yes | `ANB` |
| `NOTAM_FLAG` | Availability of NOTAM 'D' Service at Airport | Text, up to 1 character | Not applicable | Yes | `Y` |
| `ACTIVATION_DATE` | Airport Activation Date (YYYY/MM) provides the YEAR and MONTH that the Facility was added to the NFDC airport database. Note: this information is only available for those Facilities opened since 1981. | Text, up to 7 characters | Not applicable | Yes | `1959/08` |
| `ARPT_STATUS` | Airport Status Code | Text, up to 2 characters | Not applicable | No | `O` |
| `FAR_139_TYPE_CODE` | Airport ARFF Certification Type Code. Format is the class code ('I', 'II', 'III', or 'IV') followed by a one character code A, B, C, D, E, or L. Codes A, B, C, D, E are for Airports having a full certificate under CFR PART 139, and identifies the Aircraft Rescue and Firefighting index for the Airport. | Text, up to 5 characters | Not applicable | Yes | `I C` |
| `FAR_139_CARRIER_SER_CODE` | Airport ARFF Certification Carrier Service Code. Code S is for Airports receiving scheduled Air Carrier Service from carriers certificated by the Civil Aeronautics Board. Code U is for Airports not receiving this scheduled service. | Text, up to 1 character | Not applicable | Yes | `S` |
| `ARFF_CERT_TYPE_DATE` | Airport ARFF Certification Date (YYYY/MM) | Text, up to 7 characters | Not applicable | Yes | `1973/05` |
| `NASP_CODE` | NPIAS/Federal Agreements Code. A Combination of 1 to 7 Codes that Indicate the Type of Federal Agreements existing at the Airport. | Text, up to 7 characters | Not applicable | Yes | `N` |
| `ASP_ANLYS_DTRM_CODE` | Airport Airspace Analysis Determination | Text, up to 13 characters | Not applicable | Yes | `NOT ANALYZED` |
| `CUST_FLAG` | Facility has been designated by the U.S. Department of Homeland Security as an International Airport of Entry for Customs | Text, up to 1 character | Not applicable | Yes | `N` |
| `LNDG_RIGHTS_FLAG` | Facility has been designated by the U.S. Department of Homeland Security as a Customs Landing Rights Airport. (Customs User Fee Airports will be designated with an E80, E80A, or E80C referenced remark "US CUSTOMS USER FEE ARPT.") | Text, up to 1 character | Not applicable | Yes | `N` |
| `JOINT_USE_FLAG` | Facility has Military/Civil Joint Use Agreement that allows Civil Operations at a Military Airport. | Text, up to 1 character | Not applicable | Yes | `N` |
| `MIL_LNDG_FLAG` | Airport has entered into an Agreement that Grants Landing Rights to the Military | Text, up to 1 character | Not applicable | Yes | `Y` |
| `INSPECT_METHOD_CODE` | Airport Inspection Method | Text, up to 1 character | Not applicable | Yes | `S` |
| `INSPECTOR_CODE` | Agency/Group Performing Physical Inspection | Text, up to 1 character | Not applicable | No | `S` |
| `LAST_INSPECTION` | Last Physical Inspection Date (YYYY/MM/DD) | Text, up to 10 characters | Not specified by FAA | Yes | `2023/05/26` |
| `LAST_INFO_RESPONSE` | Last Date Information Request was completed by Facility Owner or Manager (YYYY/MM/DD) | Text, up to 10 characters | Not specified by FAA | Yes | `1988/01/07` |
| `FUEL_TYPES` | Fuel Types available for public use at the Airport. | Text, up to 40 characters | Not applicable | Yes | `100LL,A+` |
| `AIRFRAME_REPAIR_SER_CODE` | Airframe Repair Service Availability/Type | Text, up to 5 characters | Not applicable | Yes | `NONE` |
| `PWR_PLANT_REPAIR_SER` | Power Plant (Engine) Repair Availability/Type | Text, up to 5 characters | Not specified by FAA | Yes | `NONE` |
| `BOTTLED_OXY_TYPE` | Type of Bottled Oxygen Available (Value represents High and/or Low Pressure Replacement Bottle) | Text, up to 8 characters | Not applicable | Yes | `NONE` |
| `BULK_OXY_TYPE` | Type of Bulk Oxygen Available (Value represents High and/or Low Pressure Cylinders) | Text, up to 8 characters | Not applicable | Yes | `NONE` |
| `LGT_SKED` | Airport Lighting Schedule value is the beginning-ending times (local time) that the Standard Airport Lights are operated. Value can be "SS-SR" (indicating sunset-sunrise), blank, or "SEE RMK", indicating that the details are in a facility remark data entry. | Text, up to 7 characters | Not specified by FAA | Yes | `SEE RMK` |
| `BCN_LGT_SKED` | Beacon Lighting Schedule value is the beginning-ending times (local time) that the Rotating Airport Beacon Light is operated. Value can be "SS-SR" (indicating sunset-sunrise), blank, or "SEE RMK", indicating that the details are in a facility remark data entry. | Text, up to 7 characters | Not specified by FAA | Yes | `SS-SR` |
| `TWR_TYPE_CODE` | Air Traffic Control Tower Facility Type (ATCT, NON-ATCT, ATCT-A/C, ATCT-RAPCON, ATCT-RATCF, ATCT-TRACON, TRACON). NON-ATCT is equivalent to “N” ATC TOWER at Airport. All Other are equivalent to “Y” ATC TOWER at AIRPORT. | Text, up to 12 characters | Not applicable | No | `NON-ATCT` |
| `SEG_CIRCLE_MKR_FLAG` | Segmented Circle Airport Marker System on the Airport | Text, up to 3 characters | Not applicable | Yes | `N` |
| `BCN_LENS_COLOR` | Lens Color of Operable Beacon located on the Airport | Text, up to 3 characters | Not specified by FAA | Yes | `WG` |
| `LNDG_FEE_FLAG` | Landing Fee charged to Non-Commercial Users of Airport | Text, up to 1 character | Not applicable | Yes | `N` |
| `MEDICAL_USE_FLAG` | A "Y" in this field indicates that the Landing Facility Is used for Medical Purposes | Text, up to 1 character | Not applicable | Yes | `Y` |
| `ARPT_PSN_SOURCE` | Airport Position Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `POSITION_SRC_DATE` | Airport Position Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2025/06/17` |
| `ARPT_ELEV_SOURCE` | Airport Elevation Source | Text, up to 16 characters | Not specified by FAA | Yes | `3RD PARTY SURVEY` |
| `ELEVATION_SRC_DATE` | Airport Elevation Source Date (YYYY/MM/DD) | Text, up to 10 characters | Not applicable | Yes | `2025/06/17` |
| `CONTR_FUEL_AVBL` | Contract Fuel Available | Text, up to 1 character | Not specified by FAA | Yes | `N` |
| `TRNS_STRG_BUOY_FLAG` | Buoy Transient Storage Facilities | Text, up to 1 character | Not applicable | Yes | `N` |
| `TRNS_STRG_HGR_FLAG` | Hangar Transient Storage Facilities | Text, up to 1 character | Not applicable | Yes | `Y` |
| `TRNS_STRG_TIE_FLAG` | Tie-Down Transient Storage Facilities | Text, up to 1 character | Not applicable | Yes | `Y` |
| `OTHER_SERVICES` | Other Airport Services Available. A Comma-Separated List of Other Airport Services Available at the Airport, which include: | Text, up to 110 characters | Not specified by FAA | Yes | `INSTR,RNTL,SALES` |
| `WIND_INDCR_FLAG` | Wind Indicator shows whether a Wind Indicator exists at the Airport | Text, up to 3 characters | Not applicable | Yes | `Y-L` |
| `ICAO_ID` | ICAO Identifier | Text, up to 7 characters | Not applicable | Yes | `KEET` |
| `MIN_OP_NETWORK` | Minimum Operational Network (MON) | Text, up to 1 character | Not specified by FAA | No | `N` |
| `USER_FEE_FLAG` | If Flag is checked in NASR, User Fee Airports Will Be Designated With Text "US CUSTOMS USER FEE ARPT." | Text, up to 26 characters | Not applicable | Yes | `US CUSTOMS USER FEE ARPT.` |
| `CTA` | Cold Temperature Airport. Altitude Correction Required At or Below Temperature Given in Celsius. | Text, up to 4 characters | Not specified by FAA | Yes | `-13C` |

## Sources

- `APT_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `APT DATA LAYOUT.pdf` for FAA field definitions and stated units
- `APT_BASE.csv` from the 2026-08-06 cycle for example values
