import pandas as pd

from openNASR.routes import PreferredRouteRepository


def test_preferred_route_orders_segments_and_attaches_format():
    key = {
        "ORIGIN_ID": "AAA",
        "DSTN_ID": "BBB",
        "PFR_TYPE_CODE": "TEC",
        "ROUTE_NO": "1",
    }
    repository = PreferredRouteRepository(
        {
            "PFR_BASE": pd.DataFrame([key]),
            "PFR_RMT_FMT": pd.DataFrame(
                [{"Orig": "AAA", "Dest": "BBB", "Type": "TEC", "Seq": "1"}]
            ),
            "PFR_SEG": pd.DataFrame(
                [{**key, "SEGMENT_SEQ": "2"}, {**key, "SEGMENT_SEQ": "1"}]
            ),
        }
    )
    route = repository.get(("aaa", "bbb", "tec", "1"))
    assert len(route.formats) == 1
    assert [segment["SEGMENT_SEQ"] for segment in route.segments] == ["1", "2"]
    assert len(repository._indexes) == 12
