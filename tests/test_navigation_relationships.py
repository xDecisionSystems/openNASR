import pandas as pd
import pytest

from openNASR.airway import AirwayRepository
from openNASR.registry import (
    AIRWAY_FIX_KEY,
    AIRWAY_NAVAID_KEY,
    COMMUNICATION_NAVAID_KEY,
    FIX_KEY,
    NAVAID_KEY,
    RelationshipSpec,
    SERVICED_FACILITY_KEY,
    TableRegistry,
)
from openNASR.schemas import SchemaCatalog


@pytest.mark.parametrize("schema_id", ("pre_2026_09", "nasr_2026_09"))
def test_navigation_relationships_use_complete_declared_keys(schema_id):
    catalog = SchemaCatalog()
    registry = TableRegistry(catalog=catalog)

    assert (
        RelationshipSpec("fix", "FIX_BASE", AIRWAY_FIX_KEY, FIX_KEY)
        in registry.spec("AWY_SEG_ALT", schema_id).relationships
    )
    assert (
        RelationshipSpec("navaid", "NAV_BASE", AIRWAY_NAVAID_KEY, NAVAID_KEY)
        in registry.spec("AWY_SEG_ALT", schema_id).relationships
    )
    assert (
        RelationshipSpec("fix", "FIX_BASE", FIX_KEY, FIX_KEY)
        in registry.spec("HPF_BASE", schema_id).relationships
    )
    assert (
        RelationshipSpec("navaid", "NAV_BASE", COMMUNICATION_NAVAID_KEY, NAVAID_KEY)
        in registry.spec("COM", schema_id).relationships
    )
    assert registry.spec("FRQ", schema_id).relationships == ()
    assert registry.spec("FRQ", schema_id).indexes[1].columns == SERVICED_FACILITY_KEY

    for table_name in ("AWY_SEG_ALT", "HPF_BASE", "COM", "FRQ"):
        variant = registry.spec(table_name, schema_id)
        local = {column.name for column in catalog.table(table_name, schema_id).columns}
        assert set(variant.identity_key or ()) <= local
        for relationship in variant.relationships:
            target = {
                column.name
                for column in catalog.table(
                    relationship.target_table, schema_id
                ).columns
            }
            assert set(relationship.local_columns) <= local
            assert set(relationship.target_columns) <= target


def test_airway_points_resolve_only_complete_fix_and_navaid_keys():
    fix_segment = {
        "REGULATORY": "Y",
        "AWY_LOCATION": "D",
        "AWY_ID": "1",
        "POINT_SEQ": "1",
        "FROM_POINT": "ALPHA",
        "FROM_PT_TYPE": "FIX",
        "NAV_CITY": "",
        "ICAO_REGION_CODE": "K1",
        "STATE_CODE": "FL",
        "COUNTRY_CODE": "US",
    }
    navaid_segment = {
        **fix_segment,
        "POINT_SEQ": "2",
        "FROM_POINT": "BRAVO",
        "FROM_PT_TYPE": "VOR",
        "NAV_CITY": "ORLANDO",
        "ICAO_REGION_CODE": "",
    }
    repository = AirwayRepository(
        {
            "AWY_BASE": pd.DataFrame(
                [{"REGULATORY": "Y", "AWY_LOCATION": "D", "AWY_ID": "1"}]
            ),
            "AWY_SEG_ALT": pd.DataFrame([navaid_segment, fix_segment]),
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
            "NAV_BASE": pd.DataFrame(
                [
                    {
                        "NAV_ID": "BRAVO",
                        "NAV_TYPE": "VOR",
                        "CITY": "ORLANDO",
                        "STATE_CODE": "FL",
                        "COUNTRY_CODE": "US",
                    },
                    {
                        "NAV_ID": "BRAVO",
                        "NAV_TYPE": "VOR",
                        "CITY": "MIAMI",
                        "STATE_CODE": "FL",
                        "COUNTRY_CODE": "US",
                    },
                ]
            ),
        }
    )

    airway = repository.get(("Y", "D", "1"))

    assert airway.segments[0].fix is not None
    assert airway.segments[0].fix.state == "FL"
    assert airway.segments[0].navaid is None
    assert airway.segments[1].fix is None
    assert airway.segments[1].navaid is not None
    assert airway.segments[1].navaid.name is None
