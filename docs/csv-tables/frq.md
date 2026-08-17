# `FRQ`

FAA frequency assignments and the facilities or services using them.

This page describes the FAA CSV published in the **2026-08-06** NASR cycle. 
FAA schemas can change between cycles; inspect the schema file shipped with 
the selected cycle when exact compatibility is required.

## Columns

| Column | Description | Format | Units | Nullable | Example value |
| --- | --- | --- | --- | --- | --- |
| `EFF_DATE` | The 28 Day NASR Subscription Effective Date in format ‘YYYY/MM/DD’. | Text, up to 10 characters; YYYY/MM/DD | Not applicable | No | `2026/08/06` |
| `FACILITY` | Contains FACILITY ID except for FACILITY TYPE AFIS, CTAF, GCO, UNICOM and RCAG which do not contain FACILITY IDs in NASR. The FACILITY NAME is used for RCAG sites. AFIS, CTAF, GCO and UNICOM are NULL since they do not contain either a FACILITY ID or FACILITY NAME in NASR. | Text, up to 30 characters | Not specified by FAA | Yes | `00A` |
| `FAC_NAME` | Official Facility Name. AFIS, CTAF, GCO and UNICOM FACILITY TYPEs are NULL since they do not contain either a FACILITY ID or FACILITY NAME in NASR. ASOS/AWOS FACILITY TYPEs are NULL since they do not contain a FACILITY NAME in NASR. | Text, up to 50 characters | Not applicable | Yes | `TOTAL RF` |
| `FACILITY_TYPE` | All records contain a FACILITY TYPE. Please note that RCO or RCO1 both are the same and serve the same function; a remote communication outlet. An RCO1 may exist if two separate sites | Text, up to 12 characters | Not applicable | No | `NON-ATCT` |
| `ARTCC_OR_FSS_ID` | FACILITY TYPE RCAG contain an identified ARTCC ID and FACILITY TYPE RCO/RCO1 contain an identified FSS ID. The ARTCC ID for an RCAG and the FSS ID for an RCO/RCO1 is included for convenience since that is the resource in NASR you must open to view specific RCAG or RCO/RCO1 information. | Text, up to 4 characters | Not applicable | Yes | `RNO` |
| `CPDLC` | A Controller Pilot Data Link Communications (CPDLC) remark associated with a FACILITY is listed here. | Text, up to 100 characters | Not specified by FAA | Yes | `CPDLC (LOGON KUSA)` |
| `TOWER_HRS` | Only listed for ATCT FACILITY TYPEs where the FACILITY equals the SERVICED FACILITY. | Text, up to 200 characters | Not specified by FAA | Yes | `0800-1600 MON-FRI.` |
| `SERVICED_FACILITY` | The FACILITY ID (or FACILITY NAME if FACILITY TYPE is RCAG) that is serviced by the frequencies listed. This is a NON-NULL field. | Text, up to 30 characters | Not specified by FAA | No | `00A` |
| `SERVICED_FAC_NAME` | The FACILITY NAME that is serviced by the frequencies listed. | Text, up to 50 characters | Not applicable | Yes | `TOTAL RF` |
| `SERVICED_SITE_TYPE` | Facility Type of SERVICED FACILITY. | Text, up to 25 characters | Not applicable | Yes | `HELIPORT` |
| `LAT_DECIMAL` | Facility Reference Point Latitude in Decimal Format. | Numeric (10,8) (precision, scale) | decimal degrees | Yes | `40.07083333` |
| `LONG_DECIMAL` | Facility Reference Point Longitude in Decimal Format. | Numeric (11,8) (precision, scale) | decimal degrees | Yes | `-74.93361111` |
| `SERVICED_CITY` | Serviced Facility Associated City Name. | Text, up to 40 characters | Not applicable | Yes | `BENSALEM` |
| `SERVICED_STATE` | This is the two letter state ID of the SERVICED FACILITY. | Text, up to 2 characters | Not applicable | Yes | `PA` |
| `SERVICED_COUNTRY` | Country Post Office Code Serviced Facility Located | Text, up to 2 characters | Not applicable | Yes | `US` |
| `TOWER_OR_COMM_CALL` | Radio call used by pilot to contact ATC or FSS facility. | Text, up to 30 characters | Not specified by FAA | Yes | `EUREKA` |
| `PRIMARY_APPROACH_RADIO_CALL` | Radio call of facility that furnishes primary approach control. | Text, up to 26 characters | Not specified by FAA | Yes | `PALM BEACH` |
| `FREQ` | Frequency for SERVICED FACILITY use. In the case of a NAVAID with DME/TACAN Channel, the Frequency is displayed with the Channel – FREQ/CHAN. | Text, up to 40 characters | Not specified by FAA | Yes | `122.9` |
| `SECTORIZATION` | Sectorization based on SERVICED FACILITY or airway boundaries, or limitations based on runway usage. For ARTCC and RCAG, Sectorization identifies the Frequency Altitude as Low, High, Low/High or Ultra-High. | Text, up to 50 characters | Not specified by FAA | Yes | `250-330 TED ABV 1500 FT` |
| `FREQ_USE` | SERVICED FACILITY frequency use description. | Text, up to 600 characters | Not specified by FAA | Yes | `CTAF` |
| `REMARK` | Remark Text (Free Form Text that further describes a specific Information Item.) | Text, up to 1500 characters | Not applicable | Yes | `PAPI RY 10 AND RY 28; MIRL RY 10/28 OPER DUSK-1000; AFTER 1000 ACTVT - CTAF.` |

## Sources

- `FRQ_CSV_DATA_STRUCTURE.csv` for FAA type, maximum length, and nullability
- `FRQ DATA LAYOUT.pdf` for FAA field definitions and stated units
- `FRQ.csv` from the 2026-08-06 cycle for example values
