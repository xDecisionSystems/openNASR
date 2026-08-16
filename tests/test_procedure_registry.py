import pytest

from openNASR.registry import (
    CDR_KEY,
    DEPARTURE_AIRPORT_KEY,
    DEPARTURE_KEY,
    DEPARTURE_ROUTE_KEY,
    DEPARTURE_ROUTE_ORDER,
    PREFERRED_ROUTE_FORMAT_KEY,
    PREFERRED_ROUTE_KEY,
    PREFERRED_ROUTE_SEGMENT_KEY,
    PROCEDURE_ROUTE_TABLES,
    STAR_AIRPORT_KEY,
    STAR_KEY,
    STAR_ROUTE_KEY,
    STAR_ROUTE_ORDER,
    IndexSpec,
    RelationshipSpec,
    TableRegistry,
)
from openNASR.schemas import SchemaCatalog


SCHEMA_IDS = ("pre_2026_09", "nasr_2026_09")


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_procedure_and_route_keys_are_declared_in_each_schema(schema_id):
    catalog = SchemaCatalog()
    registry = TableRegistry(catalog=catalog)

    expected = {
        "CDR": CDR_KEY,
        "DP_BASE": DEPARTURE_KEY,
        "DP_APT": DEPARTURE_AIRPORT_KEY,
        "DP_RTE": DEPARTURE_ROUTE_KEY,
        "PFR_BASE": PREFERRED_ROUTE_KEY,
        "PFR_RMT_FMT": PREFERRED_ROUTE_FORMAT_KEY,
        "PFR_SEG": PREFERRED_ROUTE_SEGMENT_KEY,
        "STAR_BASE": STAR_KEY,
        "STAR_APT": STAR_AIRPORT_KEY,
        "STAR_RTE": STAR_ROUTE_KEY,
    }

    assert set(expected) == PROCEDURE_ROUTE_TABLES
    for table_name, identity_key in expected.items():
        variant = registry.spec(table_name, schema_id)
        declared = {
            column.name for column in catalog.table(table_name, schema_id).columns
        }
        assert variant.identity_key == identity_key
        assert set(identity_key) <= declared
        assert set(variant.order_by) <= declared
        for relationship in variant.relationships:
            target_columns = {
                column.name
                for column in catalog.table(
                    relationship.target_table, schema_id
                ).columns
            }
            assert set(relationship.local_columns) <= declared
            assert set(relationship.target_columns) <= target_columns


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_departure_relationships_require_the_complete_procedure_key(schema_id):
    registry = TableRegistry()
    base = registry.spec("DP_BASE", schema_id)
    airports = registry.spec("DP_APT", schema_id)
    routes = registry.spec("DP_RTE", schema_id)

    assert base.indexes == (
        IndexSpec("departure", DEPARTURE_KEY, unique=True),
        IndexSpec("computer_code", ("DP_COMPUTER_CODE",)),
    )
    assert base.relationships == (
        RelationshipSpec("airports", "DP_APT", DEPARTURE_KEY, DEPARTURE_KEY),
        RelationshipSpec("routes", "DP_RTE", DEPARTURE_KEY, DEPARTURE_KEY),
    )
    assert airports.relationships == (
        RelationshipSpec("departure", "DP_BASE", DEPARTURE_KEY, DEPARTURE_KEY),
    )
    assert routes.relationships == airports.relationships
    assert routes.order_by == DEPARTURE_ROUTE_ORDER


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_preferred_route_formats_and_segments_use_direct_composite_keys(schema_id):
    registry = TableRegistry()
    base = registry.spec("PFR_BASE", schema_id)
    formats = registry.spec("PFR_RMT_FMT", schema_id)
    segments = registry.spec("PFR_SEG", schema_id)

    assert base.relationships == (
        RelationshipSpec(
            "formats",
            "PFR_RMT_FMT",
            PREFERRED_ROUTE_KEY,
            PREFERRED_ROUTE_FORMAT_KEY,
        ),
        RelationshipSpec(
            "segments", "PFR_SEG", PREFERRED_ROUTE_KEY, PREFERRED_ROUTE_KEY
        ),
    )
    assert formats.relationships == (
        RelationshipSpec(
            "preferred_route",
            "PFR_BASE",
            PREFERRED_ROUTE_FORMAT_KEY,
            PREFERRED_ROUTE_KEY,
        ),
    )
    assert segments.order_by == ("SEGMENT_SEQ",)


@pytest.mark.parametrize("schema_id", SCHEMA_IDS)
def test_star_relationships_and_route_ordering_use_complete_keys(schema_id):
    registry = TableRegistry()
    base = registry.spec("STAR_BASE", schema_id)
    airports = registry.spec("STAR_APT", schema_id)
    routes = registry.spec("STAR_RTE", schema_id)

    assert base.relationships == (
        RelationshipSpec("airports", "STAR_APT", STAR_KEY, STAR_KEY),
        RelationshipSpec("routes", "STAR_RTE", STAR_KEY, STAR_KEY),
    )
    assert airports.relationships == (
        RelationshipSpec("star", "STAR_BASE", STAR_KEY, STAR_KEY),
    )
    assert routes.relationships == airports.relationships
    assert routes.order_by == STAR_ROUTE_ORDER


def test_representative_collisions_require_full_keys_and_numeric_sequence_order():
    departures = [
        {"DP_NAME": "ANCHORAGE", "ARTCC": "ZAN", "DP_COMPUTER_CODE": "NOT ASSIGNED"},
        {"DP_NAME": "DENVER", "ARTCC": "ZDV", "DP_COMPUTER_CODE": "NOT ASSIGNED"},
    ]
    routes = [
        {**departures[0], "BODY_SEQ": "1", "POINT_SEQ": "20"},
        {**departures[0], "BODY_SEQ": "1", "POINT_SEQ": "10"},
    ]
    formats = [{"Orig": "ABE", "Dest": "ACY", "Type": "TEC", "Seq": "1"}]
    preferred_routes = [
        {"ORIGIN_ID": "ABE", "DSTN_ID": "ACY", "PFR_TYPE_CODE": "TEC", "ROUTE_NO": "1"}
    ]

    assert len({row["DP_COMPUTER_CODE"] for row in departures}) == 1
    assert (
        len({tuple(row[column] for column in DEPARTURE_KEY) for row in departures}) == 2
    )
    assert [
        row["POINT_SEQ"]
        for row in sorted(routes, key=lambda row: int(row["POINT_SEQ"]))
    ] == ["10", "20"]
    assert tuple(formats[0][column] for column in PREFERRED_ROUTE_FORMAT_KEY) == tuple(
        preferred_routes[0][column] for column in PREFERRED_ROUTE_KEY
    )
