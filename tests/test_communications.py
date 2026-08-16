import pandas as pd

from openNASR.communications import CommunicationOutletRepository, FrequencyRepository


def test_communication_outlet_and_frequency_repositories_expose_rich_records():
    communication_outlets = CommunicationOutletRepository(
        {
            "COM": pd.DataFrame(
                [
                    {
                        "COMM_LOC_ID": "alpha",
                        "COMM_OUTLET_NAME": "Alpha Radio",
                        "COMM_TYPE": "FSS",
                        "NAV_ID": "ANV",
                        "NAV_TYPE": "VOR",
                        "CITY": "ALPHA CITY",
                        "STATE_CODE": "FL",
                        "COUNTRY_CODE": "US",
                    }
                ]
            ),
            "NAV_BASE": pd.DataFrame(
                [
                    {
                        "NAV_ID": "ANV",
                        "NAV_TYPE": "VOR",
                        "CITY": "ALPHA CITY",
                        "STATE_CODE": "FL",
                        "COUNTRY_CODE": "US",
                    }
                ]
            ),
        }
    )
    frequencies = FrequencyRepository(
        {
            "FRQ": pd.DataFrame(
                [
                    {
                        "FACILITY": "ALPHA",
                        "SERVICED_FACILITY": "A1",
                        "SERVICED_SITE_TYPE": "A",
                        "SERVICED_STATE": "FL",
                        "SERVICED_COUNTRY": "US",
                        "FREQ": "121.5",
                        "SECTORIZATION": "",
                        "FREQ_USE": "EMERGENCY",
                    }
                ]
            )
        }
    )

    outlet = communication_outlets.get("ALPHA")
    frequency = frequencies.get(
        ("alpha", "a1", "a", "fl", "us", "121.5", None, "emergency")
    )

    assert outlet.record.name == "Alpha Radio"
    assert outlet.record.communication_type == "FSS"
    assert outlet.navaid is not None
    assert outlet.navaid.identifier == "ANV"
    assert frequency.record.frequency_key == (
        "ALPHA",
        "A1",
        "A",
        "FL",
        "US",
        "121.5",
        None,
        "EMERGENCY",
    )
    assert len(frequencies.find(serviced_facility=("a1", "a", "fl", "us"))) == 1
