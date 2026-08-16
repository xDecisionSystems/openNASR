"""Coverage report tests use temporary output and never commit generated JSON."""

import json

from tools.schema_coverage_report import build_report, main


def test_coverage_report_counts_all_supported_fixture_files():
    report = build_report()

    for schema_report in report["schemas"].values():
        assert schema_report["total_csv_files"] == 87
        assert schema_report["operational_csv_files"] == 63
        assert schema_report["schema_description_files"] == 24
        assert schema_report["matched_table_spec_count"] == 63
        assert schema_report["rich_record_table_count"] == 2
        assert schema_report["rich_record_tables"] == ["CLS_ARSP", "MIL_OPS"]
        assert schema_report["unmodeled_operational_files"] == []
        assert len(schema_report["unmatched_files"]) == 24


def test_coverage_report_cli_writes_only_to_requested_scratch_path(
    tmp_path, monkeypatch
):
    output = tmp_path / "reports" / "schema-coverage.json"
    monkeypatch.setattr(
        "sys.argv",
        ["schema_coverage_report", "--output", str(output)],
    )

    main()

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["schemas"]["pre_2026_09"]["matched_table_spec_count"] == 63
    assert document["schemas"]["pre_2026_09"]["rich_record_tables"] == [
        "CLS_ARSP",
        "MIL_OPS",
    ]
