import json

import pytest

from fase2.evaluation.index import BASELINE, INITIAL_REFACTORED, build_index, collect_rows


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def test_index_uses_metadata_not_directory_names(tmp_path):
    baseline = tmp_path / "misleading-refactored-name" / "first"
    _save(baseline / "metadata.json", {"resolved_commit": BASELINE, "requested_categories": ["static"],
                                      "started_at_utc": "2026-01-01T00:00:00+00:00", "run_id": "first"})
    _save(baseline / "static/summary.json", {"status": "complete"})
    refactored = tmp_path / "misleading-baseline-name" / "second"
    _save(refactored / "metadata.json", {"resolved_commit": INITIAL_REFACTORED,
                                        "requested_categories": ["contracts"], "run_id": "second"})
    _save(refactored / "contracts/summary.json", {"verification_status": "failed", "suite_sha256": "a" * 64,
                                              "contracts": [{"junit_result": {"tests": 2, "failures": 1}}]})
    snapshot = tmp_path / "snapshots" / "third"
    _save(snapshot / "metadata.json", {"source_kind": "working_tree_snapshot", "base_commit": INITIAL_REFACTORED,
                                      "resolved_commit": None, "requested_categories": ["static"], "run_id": "third"})
    _save(snapshot / "static/summary.json", {"status": "complete"})
    rows = collect_rows(tmp_path)
    assert {row["run_id"]: row["role"] for row in rows} == {
        "first": "baseline", "second": "refactored", "third": "local snapshot"}
    assert next(row for row in rows if row["run_id"] == "second")["result"] == "failed (1 passed, 1 failed, 0 errors)"
    assert build_index(tmp_path).read_text().count("[result]") == 3


def test_index_records_framework_without_inventing_suite_version(tmp_path):
    _save(tmp_path / "arbitrary" / "summary.json", {"command": "python -m pytest fase2/tests/evaluation",
                                                         "source_head": BASELINE, "passed": 42, "failed": 0})
    row = collect_rows(tmp_path)[0]
    assert row["role"] == "framework"
    assert row["suite"] == "unrecorded"


def test_index_framework_junit_total_excludes_failures(tmp_path):
    _save(tmp_path / "framework" / "summary.json", {
        "command": "python -m pytest fase2/tests/evaluation",
        "counts": {"tests": 5, "failures": 1, "errors": 0, "skipped": 1}})
    assert collect_rows(tmp_path)[0]["result"] == "3 passed, 1 failed"


def test_index_counts_secondary_contract_check_and_unknown_legacy_counts(tmp_path):
    contract = tmp_path / "one"
    _save(contract / "metadata.json", {"resolved_commit": BASELINE, "requested_categories": ["contracts"]})
    _save(contract / "contracts/summary.json", {"verification_status": "passed", "contracts": [
        {"junit_result": {"tests": 1}, "verification_junit_result": {"tests": 1}}]})
    legacy = tmp_path / "two"
    _save(legacy / "metadata.json", {"resolved_commit": BASELINE, "requested_categories": ["functional"]})
    _save(legacy / "functional/summary.json", {"verification_status": "passed", "suites": [
        {"id": "legacy", "status": "passed"}]})
    rows = collect_rows(tmp_path)
    assert next(row for row in rows if row["category"] == "contracts")["result"] == "passed (2 passed, 0 failed, 0 errors)"
    assert next(row for row in rows if row["category"] == "functional")["result"] == "passed (counts unrecorded)"


def test_index_refuses_to_replace_historical_file(tmp_path):
    target = tmp_path / "historical.md"
    target.write_text("original evidence")
    with pytest.raises(ValueError):
        build_index(tmp_path, target)
    assert target.read_text() == "original evidence"
