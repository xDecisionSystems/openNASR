# `NAV_BASE`

Core navaid identity, type, name, frequency, location, status, and controlling-facility information.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `NAV_ID` | NAVAID Facility Identifier. | Text, up to 4 characters | Not applicable | No | `AA` |
| `NAV_TYPE` | NAVAID Facility Type. | Text, up to 25 characters | Not applicable | No | `NDB` |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. | Text, up to 2 characters | Not applicable | Yes | `ND` |
| `CITY` | NAVAID Associated City Name | Text, up to 40 characters | Not applicable | No | `FARGO` |
| `COUNTRY_CODE` | Country Post Office Code NAVAID Located | Text, up to 2 characters | Not applicable | No | `US` |
| `NAV_STATUS` | Navigation Aid Status | Text, up to 30 characters | Not applicable | No | `OPERATIONAL IFR` |
| `NAME` | Name of NAVAID | Text, up to 30 characters | Not applicable | No | `KENIE` |
| `STATE_NAME` | Associated State Name | Text, up to 30 characters | Not applicable | Yes | `NORTH DAKOTA` |
| `REGION_CODE` | FAA Region responsible for NAVAID (code) | Text, up to 3 characters | Not applicable | Yes | `AGL` |
| `COUNTRY_NAME` | Country Name NAVAID Located | Text, up to 30 characters | Not applicable | No | `UNITED STATES` |
| `FAN_MARKER` | Name of FAN MARKER | Text, up to 30 characters | Not specified by FAA | Yes | `FORT STEVENS` |
| `OWNER` | A Concatenation of the NAVAID OWNER CODE - NAVAID OWNER NAME | Text, up to 50 characters | Not specified by FAA | Yes | `F-FEDERAL AVIATION ADMIN` |
| `OPERATOR` | A Concatenation of the NAVAID OPERATOR CODE - NAVAID OPERATOR NAME | Text, up to 50 characters | Not specified by FAA | Yes | `F-FEDERAL AVIATION ADMIN` |
| `NAS_USE_FLAG` | Common System Usage (Y or N) Defines how the NAVAID is used. | Text, up to 1 character | Not applicable | No | `Y` |
| `PUBLIC_USE_FLAG` | NAVAID PUBLIC USE (Y or N) Defines by whom the NAVAID is used. | Text, up to 1 character | Not applicable | No | `Y` |
| `NDB_CLASS_CODE` | Class of NDB | Text, up to 11 characters | Not applicable | Yes | `HW/LOM` |
| `OPER_HOURS` | HOURS of Operation of NAVAID. | Text, up to 11 characters | hours | Yes | `24` |
| `HIGH_ALT_ARTCC_ID` | Identifier of ARTCC with High Altitude Boundary That the NAVAID Falls Within. | Text, up to 4 characters | Not applicable | Yes | `ZMP` |
| `HIGH_ARTCC_NAME` | Name of ARTCC with High Altitude Boundary That the NAVAID Falls Within. | Text, up to 30 characters | Not applicable | Yes | `MINNEAPOLIS` |
| `LOW_ALT_ARTCC_ID` | Identifier of ARTCC with Low Altitude Boundary That the NAVAID Falls Within. | Text, up to 4 characters | Not applicable | Yes | `ZMP` |
| `LOW_ARTCC_NAME` | Name of ARTCC with Low Altitude Boundary That the NAVAID Falls Within. | Text, up to 30 characters | Not applicable | Yes | `MINNEAPOLIS` |
| `LAT_DEG` | NAVAID Latitude Degrees | Numeric (2,0) (precision, scale) | degrees | No | `47` |
| `LAT_MIN` | NAVAID Latitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `0` |
| `LAT_SEC` | NAVAID Latitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `32.5878` |
| `LAT_HEMIS` | NAVAID Latitude Hemisphere | Text, up to 1 character | Not applicable | No | `N` |
| `LAT_DECIMAL` | NAVAID Latitude in Decimal Format | Numeric (10,8) (precision, scale) | decimal degrees | No | `47.00905216` |
| `LONG_DEG` | NAVAID Longitude Degrees | Numeric (3,0) (precision, scale) | degrees | No | `96` |
| `LONG_MIN` | NAVAID Longitude Minutes | Numeric (2,0) (precision, scale) | minutes | No | `48` |
| `LONG_SEC` | NAVAID Longitude Seconds | Numeric (6,4) (precision, scale) | seconds | No | `54.6606` |
| `LONG_HEMIS` | NAVAID Longitude Hemisphere | Text, up to 1 character | Not applicable | No | `W` |
| `LONG_DECIMAL` | NAVAID Longitude in Decimal Format | Numeric (11,8) (precision, scale) | decimal degrees | No | `-96.8151835` |
| `SURVEY_ACCURACY_CODE` | Latitude/Longitude Survey Accuracy (Code) | Text, up to 1 character | Not applicable | Yes | `6` |
| `TACAN_DME_STATUS` | Status of TACAN or DME Equipment. | Text, up to 30 characters | Not applicable | Yes | `OPERATIONAL RESTRICTED` |
| `TACAN_DME_LAT_DEG` | Latitude Degrees of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (2,0) (precision, scale) | degrees | Yes | `41` |
| `TACAN_DME_LAT_MIN` | Latitude Minutes of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (2,0) (precision, scale) | minutes | Yes | `29` |
| `TACAN_DME_LAT_SEC` | Latitude Seconds of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (6,4) (precision, scale) | seconds | Yes | `0.074` |
| `TACAN_DME_LAT_HEMIS` | Latitude Hemisphere of TACAN Portion of VORTAC when TACAN is not sited with VOR | Text, up to 1 character | Not applicable | Yes | `N` |
| `TACAN_DME_LAT_DECIMAL` | Latitude in Decimal Format of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (10,8) (precision, scale) | Not specified by FAA | Yes | `41.48335388` |
| `TACAN_DME_LONG_DEG` | Longitude Degrees of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (3,0) (precision, scale) | degrees | Yes | `120` |
| `TACAN_DME_LONG_MIN` | Longitude Minutes of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (2,0) (precision, scale) | minutes | Yes | `33` |
| `TACAN_DME_LONG_SEC` | Longitude Seconds of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (6,4) (precision, scale) | seconds | Yes | `41.55` |
| `TACAN_DME_LONG_HEMIS` | Longitude Hemisphere of TACAN Portion of VORTAC when TACAN is not sited with VOR | Text, up to 1 character | Not applicable | Yes | `W` |
| `TACAN_DME_LONG_DECIMAL` | Longitude in Decimal Format of TACAN Portion of VORTAC when TACAN is not sited with VOR | Numeric (11,8) (precision, scale) | Not specified by FAA | Yes | `-120.56154166` |
| `ELEV` | Elevation in Tenth of a Foot (MSL). | Numeric (6,1) (precision, scale) | feet | Yes | `890.6` |
| `MAG_VARN` | Magnetic Variation Degrees (DME, VOT and FM NAVAID Types do not have MAG VAR. Any value in this column for those NAVAID Types should be ignored.) | Numeric (2,0) (precision, scale) | degrees | Yes | `4` |
| `MAG_VARN_HEMIS` | Direction (east or west) of magnetic variation. | Text, up to 1 character | Not applicable | Yes | `E` |
| `MAG_VARN_YEAR` | Magnetic Variation Epoch Year (DME, VOT and FM NAVAID Types do not have MAG VAR YEAR. Any value in this column for those NAVAID Types should be ignored.) | Numeric (4,0) (precision, scale) | Not applicable | Yes | `2005` |
| `SIMUL_VOICE_FLAG` | Simultaneous Voice Feature | Text, up to 1 character | Not applicable | Yes | `N` |
| `PWR_OUTPUT` | Power Output (In Watts) | Numeric (4,0) (precision, scale) | Not specified by FAA | Yes | `100` |
| `AUTO_VOICE_ID_FLAG` | Automatic Voice Identification Feature | Text, up to 1 character | Not applicable | Yes | `N` |
| `MNT_CAT_CODE` | Monitoring Category | Text, up to 1 character | Not applicable | Yes | `1` |
| `VOICE_CALL` | Radio Voice Call (Name) or Trans Signal | Text, up to 60 characters | Not specified by FAA | Yes | `NONE` |
| `CHAN` | Channel (TACAN) NAVAID Transmits On | Text, up to 4 characters | Not specified by FAA | Yes | `113Y` |
| `FREQ` | Frequency the NAVAID Transmits On (Except TACAN) | Numeric (5,2) (precision, scale) | Not specified by FAA | Yes | `365` |
| `MKR_IDENT` | Transmitted Fan Marker/Marine Radio Beacon Identifier | Text, up to 30 characters | Not applicable | Yes | `DOT DASH DOT` |
| `MKR_SHAPE` | Fan Marker Type (E - ELLIPTICAL) | Text, up to 1 character | Not specified by FAA | Yes | `E` |
| `MKR_BRG` | True Bearing of Major Axis of Fan Marker | Numeric (3,0) (precision, scale) | Not specified by FAA | Yes | `16` |
| `ALT_CODE` | VOR Standard Service Volume | Text, up to 2 characters | Not applicable | Yes | `VH` |
| `DME_SSV` | DME Standard Service Volume | Text, up to 2 characters | Not specified by FAA | Yes | `DH` |
| `LOW_NAV_ON_HIGH_CHART_FLAG` | Low Altitude Facility Used in High Structure | Text, up to 1 character | Not applicable | Yes | `Y` |
| `Z_MKR_FLAG` | NAVAID Z Marker Available | Text, up to 1 character | Not applicable | Yes | `N` |
| `FSS_ID` | Associated/Controlling FSS (IDENT) | Text, up to 4 characters | Not applicable | Yes | `GFK` |
| `FSS_NAME` | Associated/Controlling FSS (Name) | Text, up to 30 characters | Not applicable | Yes | `GRAND FORKS` |
| `FSS_HOURS` | Hours of Operation of Controlling FSS | Text, up to 65 characters | hours | Yes | `24` |
| `NOTAM_ID` | NOTAM Accountability Code (IDENT) | Text, up to 4 characters | Not applicable | Yes | `FAR` |
| `QUAD_IDENT` | Quadrant Identification and Range Leg Bearing (LFR Only) | Text, up to 20 characters | Not applicable | Yes | `078A169N265A349N` |
| `PITCH_FLAG` | Pitch Flag | Text, up to 1 character | Not applicable | Yes | `N` |
| `CATCH_FLAG` | Catch Flag | Text, up to 1 character | Not applicable | Yes | `N` |
| `SUA_ATCAA_FLAG` | SUA/ATCAA Flag | Text, up to 1 character | Not applicable | Yes | `N` |
| `RESTRICTION_FLAG` | NAVAID Restriction Flag | Text, up to 1 character | Not applicable | Yes | `Y` |
| `HIWAS_FLAG` | HIWAS Flag | Text, up to 1 character | Not applicable | Yes | `No non-empty value in 2026-08-06 cycle` |

## Sources

- `NAV_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `NAV DATA LAYOUT.pdf` for FAA field definitions and stated units
- `NAV_BASE.csv` from the 2026-08-06 cycle for example values
