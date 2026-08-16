import pytest

from openNASR.registry import FACILITY_TABLES, TableRegistry
from openNASR.schemas import SchemaCatalog


@pytest.mark.parametrize("schema_id", ("pre_2026_09", "nasr_2026_09"))
def test_facility_keys_and_relationships_use_declared_columns(schema_id):
    catalog = SchemaCatalog()
    registry = TableRegistry(catalog=catalog)
    for table_name in FACILITY_TABLES:
        variant = registry.spec(table_name, schema_id)
        local = {column.name for column in catalog.table(table_name, schema_id).columns}
        assert variant.identity_key
        assert set(variant.identity_key) <= local
        assert set(variant.order_by) <= local
        for relationship in variant.relationships:
            target = {
                column.name
                for column in catalog.table(
                    relationship.target_table, schema_id
                ).columns
            }
            assert set(relationship.local_columns) <= local
            assert set(relationship.target_columns) <= target


@pytest.mark.parametrize("schema_id", ("pre_2026_09", "nasr_2026_09"))
def test_radar_and_awos_remain_standalone_without_complete_parent_keys(schema_id):
    registry = TableRegistry()
    assert registry.spec("RDR", schema_id).relationships == ()
    assert registry.spec("AWOS", schema_id).relationships == ()
