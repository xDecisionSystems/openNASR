from openNASR.records import FaaRecord


def test_airport_repository_get_and_singular_facade_are_equivalent(fixture_nasr):
    nasr, _ = fixture_nasr

    from_repository = nasr.airports.get("kbwi")
    from_singular_method = nasr.airport("KBWI")

    assert isinstance(from_repository, FaaRecord)
    assert from_repository["ARPT_ID"] == from_singular_method["ARPT_ID"] == "BWI"
    assert from_repository["ICAO_ID"] == from_singular_method["ICAO_ID"] == "KBWI"
