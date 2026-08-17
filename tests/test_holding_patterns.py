import pandas as pd

from openNASR.holding import HoldingPatternRepository


def test_holding_pattern_uses_full_key_and_orders_remarks():
    base = {
        "HP_NAME": "ALPHA",
        "HP_NO": "1",
        "STATE_CODE": "FL",
        "COUNTRY_CODE": "US",
        "FIX_ID": "ALPHA",
        "ICAO_REGION_CODE": "K1",
    }
    repository = HoldingPatternRepository(
        {
            "HPF_BASE": pd.DataFrame([base]),
            "HPF_CHRT": pd.DataFrame([{**base, "CHARTING_TYPE_DESC": "Enroute"}]),
            "HPF_RMK": pd.DataFrame(
                [
                    {
                        **base,
                        "TAB_NAME": "A",
                        "REF_COL_NAME": "R",
                        "REF_COL_SEQ_NO": "2",
                        "REMARK": "second",
                    },
                    {
                        **base,
                        "TAB_NAME": "A",
                        "REF_COL_NAME": "R",
                        "REF_COL_SEQ_NO": "1",
                        "REMARK": "first",
                    },
                    {
                        **base,
                        "STATE_CODE": "GA",
                        "TAB_NAME": "A",
                        "REF_COL_NAME": "R",
                        "REF_COL_SEQ_NO": "0",
                        "REMARK": "other",
                    },
                ]
            ),
            "HPF_SPD_ALT": pd.DataFrame(
                [{**base, "SPEED_RANGE": "210", "ALTITUDE": "6000"}]
            ),
            "FIX_BASE": pd.DataFrame(
                [
                    {
                        "FIX_ID": "ALPHA",
                        "ICAO_REGION_CODE": "K1",
                        "STATE_CODE": "FL",
                        "COUNTRY_CODE": "US",
                    },
                    {
                        "FIX_ID": "ALPHA",
                        "ICAO_REGION_CODE": "K1",
                        "STATE_CODE": "GA",
                        "COUNTRY_CODE": "US",
                    },
                ]
            ),
        }
    )

    pattern = repository.get(("alpha", "1", "fl", "us"))

    assert pattern.record.holding_pattern_key == ("ALPHA", "1", "FL", "US")
    assert pattern.charts[0].charting_type == "Enroute"
    assert [remark["REMARK"] for remark in pattern.remarks] == ["first", "second"]
    assert pattern.speed_altitude_limits[0].altitude == "6000"
    assert pattern.fix is not None
    assert pattern.fix.state == "FL"
    assert len(repository._indexes) == 16
    assert len(repository._relationship_index._positions) == 1
