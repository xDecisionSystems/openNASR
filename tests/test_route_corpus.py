"""The checked-in route corpus resolves exactly as recorded."""

import json

import pytest

from tools.route_corpus import DEFAULT_CORPUS, load_corpus, main, run_corpus


def test_every_corpus_route_matches_its_recorded_outcome():
    report = run_corpus(load_corpus(DEFAULT_CORPUS))

    assert report["mismatches"] == []
    assert report["expectation_match_rate"] == 1.0
    assert report["total"] >= 8
    assert report["resolved"] < report["total"]  # the corpus keeps failure cases


def test_a_changed_resolution_is_reported_as_a_mismatch():
    document = load_corpus(DEFAULT_CORPUS)
    document["routes"][0]["expect"]["points"][0][0] = 1.0

    report = run_corpus(document)

    assert [item["id"] for item in report["mismatches"]] == [
        document["routes"][0]["id"]
    ]
    assert report["expectation_match_rate"] < 1.0


def test_cli_fails_below_the_minimum_rate(tmp_path, capsys):
    document = load_corpus(DEFAULT_CORPUS)
    document["routes"][0]["expect"] = {"status": "error", "error": "ValueError"}
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert main([str(path)]) == 1
    assert main([str(path), "--min-rate", "0.5"]) == 0
    first, _ = json.JSONDecoder().raw_decode(capsys.readouterr().out)
    assert first["total"] == len(document["routes"])


def test_corpus_with_duplicate_ids_is_rejected(tmp_path):
    document = load_corpus(DEFAULT_CORPUS)
    document["routes"].append(document["routes"][0])
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_corpus(path)
