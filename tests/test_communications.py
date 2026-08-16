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
                    }
                ]
            )
        }
    )
    frequencies = FrequencyRepository(
        {
            "FRQ": pd.DataFrame(
                [
                    {
                        "FACILITY": "ALPHA",
                        "FREQ": "121.5",
                        "FREQ_SUFFIX": "",
                        "USE_CODE": "E",
                        "FREQ_USE": "EMERGENCY",
                    }
                ]
            )
        }
    )

    outlet = communication_outlets.get("ALPHA")
    frequency = frequencies.get(("alpha", "121.5", None, "e", "emergency"))

    assert outlet.record.name == "Alpha Radio"
    assert outlet.record.communication_type == "FSS"
    assert frequency.record.frequency_key == ("ALPHA", "121.5", None, "E", "EMERGENCY")
