import pandas as pd

from openNASR.routes import CodedDepartureRouteRepository


def test_coded_departure_route_repository_returns_typed_record():
    repository = CodedDepartureRouteRepository(
        {"CDR": pd.DataFrame([{"RCode": "AB1", "Orig": "AAA", "Dest": "BBB"}])}
    )

    route = repository.get("ab1")

    assert route.record.route_code == "AB1"
    assert route.record.origin == "AAA"
    assert route.record.destination == "BBB"
    assert len(repository._indexes) == 1
