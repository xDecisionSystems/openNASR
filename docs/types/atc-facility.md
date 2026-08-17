# ATC facility

An `AtcFacility` combines one ATC facility with its ATIS, remarks, and service
rows. Child records preserve their FAA source values and source-derived order.

## FAA source tables

| Table | Content |
| --- | --- |
| `ATC_BASE` | Facility identity and location |
| `ATC_ATIS` | ATIS services |
| `ATC_RMK` | Ordered remarks |
| `ATC_SVC` | Facility services |

The complete key is (`SITE_NO`, `SITE_TYPE_CODE`, `FACILITY_TYPE`,
`STATE_CODE`, `FACILITY_ID`, `CITY`, `COUNTRY_CODE`).

```python
facility = nasr.atc_facilities.get(atc_key)

facility.record
facility.atis_services
facility.remarks
facility.services
```

<!-- BEGIN GENERATED RECORD FIELDS -->

## Record fields

Expand a record below to see every lossless FAA field it contains.
The generated Python API follows this source-field catalog.

```{faa-dropdown} AtcFacilityRecord raw fields — ATC_BASE (30)
`AtcFacilityRecord` preserves one complete `ATC_BASE` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. |
| `SITE_TYPE_CODE` | Facility Type Code. |
| `FACILITY_TYPE` | Facility Type. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `ICAO_ID` | ICAO Identifier |
| `FACILITY_NAME` | Official Facility Name |
| `REGION_CODE` | FAA Region Code. |
| `TWR_OPERATOR_CODE` | Operator Code of the Agency that Operates the Tower. |
| `TWR_CALL` | Radio Call used by Pilot to Contact Tower. |
| `TWR_HRS` | Hours of Tower Operation in Local Time. |
| `PRIMARY_APCH_RADIO_CALL` | Radio Call of Facility That Furnishes Primary Approach Control. |
| `APCH_P_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Primary Approach Control Facility/Functions |
| `APCH_P_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Primary Approach Control Facility/Functions. |
| `SECONDARY_APCH_RADIO_CALL` | Radio Call of Facility That Furnishes Secondary Approach Control. |
| `APCH_S_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Secondary Approach Control Facility/Functions |
| `APCH_S_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Secondary Approach Control Facility/Functions. |
| `PRIMARY_DEP_RADIO_CALL` | Radio Call of Facility That Furnishes Primary Departure Control. |
| `DEP_P_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Primary Departure Control Facility/Functions |
| `DEP_P_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Primary Departure Control Facility/Functions. |
| `SECONDARY_DEP_RADIO_CALL` | Radio Call of Facility That Furnishes Secondary Departure Control. |
| `DEP_S_PROVIDER` | Facility ID (or Provider Description when Provider Type equals ‘S’) of the Agency That Operates the Secondary Departure Control Facility/Functions |
| `DEP_S_PROV_TYPE_CD` | Provider Agency Type Code for Agency that Operates the Secondary Departure Control Facility/Functions. |
| `CTL_FAC_APCH_DEP_CALLS` | Approach Departure Call associated with a Control Facility. |
| `APCH_DEP_OPER_CODE` | Agency Type Code that Operates the Control Facility |
| `CTL_PRVDING_HRS` | Hours of Operation of the Primary Control Facility. |
| `SECONDARY_CTL_PRVDING_HRS` | Hours of Operation of the Secondary Control Facility. |

[Complete `ATC_BASE` column reference](../csv-tables/atc-base.md)
```

```{faa-dropdown} AtisRecord raw fields — ATC_ATIS (12)
`AtisRecord` preserves one complete `ATC_ATIS` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. |
| `SITE_TYPE_CODE` | Facility Type Code. |
| `FACILITY_TYPE` | Facility Type. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `ATIS_NO` | ATIS Serial Number. |
| `DESCRIPTION` | Optional Description of Purpose, Fulfilled by ATIS. |
| `ATIS_HRS` | ATIS Hours of Operation in Local Time. |
| `ATIS_PHONE_NO` | ATIS Phone Number. |

[Complete `ATC_ATIS` column reference](../csv-tables/atc-atis.md)
```

```{faa-dropdown} AtcRemarkRecord raw fields — ATC_RMK (13)
`AtcRemarkRecord` preserves one complete `ATC_RMK` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. |
| `SITE_TYPE_CODE` | Facility Type Code. |
| `FACILITY_TYPE` | Facility Type. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `LEGACY_ELEMENT_NUMBER` | Legacy Remark Element. |
| `TAB_NAME` | NASR Table name associated with Remark. |
| `REF_COL_NAME` | NASR Column name associated with Remark. ARPT_CTL_REMARKs are identified as ATC_REMARK. All other Non-specific remarks are identified as GENERAL_REMARK. |
| `REMARK_NO` | Sequence number assigned to Reference Column Remark. |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) |

[Complete `ATC_RMK` column reference](../csv-tables/atc-rmk.md)
```

```{faa-dropdown} AtcServiceRecord raw fields — ATC_SVC (9)
`AtcServiceRecord` preserves one complete `ATC_SVC` row. These fields are
available by mapping key or attribute name, even when the class does not
declare a dedicated typed property for each one.

| Field | Description |
| --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. |
| `SITE_NO` | Landing Facility Site Number. A unique identifying number. Not applicable to TRACON, ARTCC or CERAP. |
| `SITE_TYPE_CODE` | Facility Type Code. |
| `FACILITY_TYPE` | Facility Type. |
| `STATE_CODE` | Associated State Post Office Code standard two letter abbreviation for US States and Territories. |
| `FACILITY_ID` | Location Identifier. Unique 3-4 character alphanumeric identifier assigned to the Landing Facility or TRACON. |
| `CITY` | Airport Associated City Name |
| `COUNTRY_CODE` | Country Post Office Code Airport Located |
| `CTL_SVC` | Services Provided to Satellite Airport. |

[Complete `ATC_SVC` column reference](../csv-tables/atc-svc.md)
```

<!-- END GENERATED RECORD FIELDS -->

## Generated API

```{eval-rst}
.. autoclass:: openNASR.atc.AtcFacility
.. autoclass:: openNASR.atc.AtcFacilityRecord
.. autoclass:: openNASR.atc.AtisRecord
.. autoclass:: openNASR.atc.AtcRemarkRecord
.. autoclass:: openNASR.atc.AtcServiceRecord
.. autoclass:: openNASR.atc.AtcFacilityRepository
```

