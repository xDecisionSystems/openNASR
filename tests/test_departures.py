import pandas as pd

from openNASR.routes import DepartureProcedureRepository


def test_departure_repository_uses_full_key_and_orders_routes():
    base = {"DP_NAME": "ALPHA", "ARTCC": "ZJX", "DP_COMPUTER_CODE": "ALPHA1"}
    repository = DepartureProcedureRepository(
        {
            "DP_BASE": pd.DataFrame([base]),
            "DP_APT": pd.DataFrame(
                [
                    {
                        **base,
                        "BODY_NAME": "MAIN",
                        "BODY_SEQ": "1",
                        "ARPT_ID": "AAA",
                        "RWY_END_ID": "01",
                    }
                ]
            ),
            "DP_RTE": pd.DataFrame(
                [
                    {**base, "BODY_SEQ": "1", "POINT_SEQ": "20"},
                    {**base, "BODY_SEQ": "1", "POINT_SEQ": "10"},
                ]
            ),
        }
    )

    departure = repository.get(("alpha", "zjx", "alpha1"))

    assert departure.airports[0]["ARPT_ID"] == "AAA"
    assert [route["POINT_SEQ"] for route in departure.routes] == ["10", "20"]
