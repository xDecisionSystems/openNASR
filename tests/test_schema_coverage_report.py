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
        assert schema_report["rich_record_table_count"] == 45
        assert schema_report["rich_record_tables"] == [
            "APT_BASE",
            "APT_RWY",
            "APT_RWY_END",
            "ARB_BASE",
            "ATC_ATIS",
            "ATC_BASE",
            "ATC_RMK",
            "ATC_SVC",
            "AWOS",
            "AWY_BASE",
            "AWY_SEG_ALT",
            "CDR",
            "CLS_ARSP",
            "COM",
            "DP_APT",
            "DP_BASE",
            "DP_RTE",
            "FIX_BASE",
            "FRQ",
            "FSS_BASE",
            "FSS_RMK",
            "HPF_BASE",
            "HPF_CHRT",
            "HPF_RMK",
            "HPF_SPD_ALT",
            "ILS_BASE",
            "ILS_DME",
            "ILS_GS",
            "ILS_MKR",
            "LID",
            "MAA_BASE",
            "MAA_CON",
            "MAA_RMK",
            "MAA_SHP",
            "MIL_OPS",
            "NAV_BASE",
            "PFR_BASE",
            "PFR_RMT_FMT",
            "PFR_SEG",
            "RDR",
            "STAR_APT",
            "STAR_BASE",
            "STAR_RTE",
            "WXL_BASE",
            "WXL_SVC",
        ]
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
        "APT_BASE",
        "APT_RWY",
        "APT_RWY_END",
        "ARB_BASE",
        "ATC_ATIS",
        "ATC_BASE",
        "ATC_RMK",
        "ATC_SVC",
        "AWOS",
        "AWY_BASE",
        "AWY_SEG_ALT",
        "CDR",
        "CLS_ARSP",
        "COM",
        "DP_APT",
        "DP_BASE",
        "DP_RTE",
        "FIX_BASE",
        "FRQ",
        "FSS_BASE",
        "FSS_RMK",
        "HPF_BASE",
        "HPF_CHRT",
        "HPF_RMK",
        "HPF_SPD_ALT",
        "ILS_BASE",
        "ILS_DME",
        "ILS_GS",
        "ILS_MKR",
        "LID",
        "MAA_BASE",
        "MAA_CON",
        "MAA_RMK",
        "MAA_SHP",
        "MIL_OPS",
        "NAV_BASE",
        "PFR_BASE",
        "PFR_RMT_FMT",
        "PFR_SEG",
        "RDR",
        "STAR_APT",
        "STAR_BASE",
        "STAR_RTE",
        "WXL_BASE",
        "WXL_SVC",
    ]
