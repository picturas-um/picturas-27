"""Reporting tests use synthetic evidence and never need Docker."""

import json
from pathlib import Path

import pytest

from fase2.evaluation.cli import main
from fase2.evaluation.index import BASELINE, INITIAL_REFACTORED
from fase2.evaluation.reporting import compare, discover, load, select
from fase2.evaluation.report_views import comparison_html, run_html


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _run(root: Path, role: str, commit: str, name: str, categories=("static", "functional", "contracts")) -> Path:
    path = root / role / commit / name
    _save(path / "metadata.json", {"role": role, "resolved_commit": commit,
          "run_id": name, "source_kind": "commit", "requested_categories": list(categories),
          "started_at_utc": "2026-11-21T10:00:00+00:00", "collection_status": "complete",
          "verification_status": "passed"})
    return path


def _static(path: Path, loc: int, duplicate: float = 0.0, scope: str = "video-processing Python core") -> None:
    _save(path / "static/summary.json", {"status": "complete", "tool_versions": {"radon": "6.0.1", "jscpd": "5.4.3"},
           "metrics": {"radon_cc": {"status": "complete", "mean_block_complexity": 4.0, "maximum_complexity": 9},
                       "radon_raw": {"status": "complete", "physical_loc": loc, "sloc": loc - 10,
                                     "module_count": 2, "largest_module_loc": loc // 2},
                       "jscpd_internal": {"status": "complete", "duplicated_lines": 0 if duplicate == 0 else 10,
                                          "duplicated_line_percentage": duplicate,
                                          "minimum_lines": 5, "minimum_tokens": 50}}})
    _save(path / "static/scope.json", {"boundary": scope, "core_python_files": ["Tools/video/example.py"]})


def _contracts(path: Path, status: str = "passed", suite: str = "suite-a",
               assertions=None, ident: str = "VF-07") -> None:
    assertions = assertions or ["edited timeline is used"]
    _save(path / "contracts/summary.json", {"status": "complete", "verification_status": status,
           "suite_sha256": suite, "contracts": [{"id": ident, "status": status, "level": "pipeline",
           "suite_sha256": suite, "assertions": assertions, "tolerances": {},
           "input_hashes": {"video.mov": "a" * 64},
           "junit": "vf-07/junit.xml", "log": "logs/test-vf-07.log",
           "junit_result": {"tests": 1, "failures": 1 if status == "failed" else 0,
                            "errors": 0, "skipped": 0}}]})
    junit = path / "contracts/vf-07/junit.xml"
    junit.parent.mkdir(parents=True, exist_ok=True)
    junit.write_text('<testsuite><testcase name="composed"><failure message="wrong duration"/></testcase></testsuite>'
                     if status == "failed" else '<testsuite><testcase name="composed"/></testsuite>')
    (path / "contracts/logs").mkdir(parents=True, exist_ok=True)
    (path / "contracts/logs/test-vf-07.log").write_text("evidence")


def test_discovery_uses_metadata_and_rejects_ambiguous_run_ids(tmp_path):
    first = _run(tmp_path, "misleading-name", BASELINE, "same")
    second = _run(tmp_path, "another-name", INITIAL_REFACTORED, "same")
    rows = discover(tmp_path)
    assert {row["role"] for row in rows} == {"baseline", "refactored"}
    with pytest.raises(ValueError, match="Ambiguous"):
        select(rows, "same")
    assert select(rows, first.relative_to(tmp_path).as_posix())["path"] == first
    assert select(rows, second.relative_to(tmp_path).as_posix())["path"] == second
    assert select(rows, str(second.resolve()))["path"] == second
    with pytest.raises(ValueError, match="not found"):
        select(rows, "missing")


def test_static_difference_and_zero_baseline_have_no_relative_percentage(tmp_path):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _static(a, 100)
    _static(b, 140, 25.0)
    result = compare(load(select(discover(tmp_path), "left")), load(select(discover(tmp_path), "right")))
    loc = next(m for m in result["metrics"] if m["name"] == "Physical LOC")
    dup = next(m for m in result["metrics"] if m["name"] == "Internal duplication")
    assert (loc["difference"], loc["relative_percent"]) == (40, 40)
    assert dup["difference"] == 25 and dup["relative_percent"] is None


def test_static_scope_mismatch_blocks_numeric_comparison(tmp_path):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _static(a, 100)
    _static(b, 140, scope="different subsystem")
    result = compare(load(select(discover(tmp_path), "left")), load(select(discover(tmp_path), "right")))
    assert all(m["difference"] is None and "scope" in m["limitation"] for m in result["metrics"])


def test_identical_contract_criteria_detect_regression_and_resolution(tmp_path):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _contracts(a)
    _contracts(b, "failed")
    left, right = [load(x) for x in discover(tmp_path)]
    result = compare(left, right)
    assert result["regressions"] == ["VF-07"]
    assert result["contracts"][0]["state"] == "regression"
    assert compare(right, left)["contracts"][0]["state"] == "resolved"


@pytest.mark.parametrize("change", ["suite", "assertions", "input_hashes", "tolerances"])
def test_changed_contract_criteria_are_not_comparable(tmp_path, change):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _contracts(a)
    _contracts(b, "failed", suite="different" if change == "suite" else "suite-a",
               assertions=["different"] if change == "assertions" else None)
    if change in {"input_hashes", "tolerances"}:
        path = b / "contracts/summary.json"
        data = json.loads(path.read_text())
        data["contracts"][0][change] = {"other": "different"}
        _save(path, data)
    left, right = [load(x) for x in discover(tmp_path)]
    result = compare(left, right)
    assert result["regressions"] == []
    assert result["contracts"][0]["state"] == "not comparable"


def test_missing_contract_and_supplementary_commit_mismatch(tmp_path):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _contracts(a)
    left, right = [load(x) for x in discover(tmp_path)]
    assert compare(left, right)["contracts"][0]["state"] == "not comparable"
    _static(a, 100)
    with pytest.raises(ValueError, match="same commit"):
        compare(left, right, right_static=load(select(discover(tmp_path), "left")))


def test_html_escapes_content_and_links_only_existing_run_evidence(tmp_path):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    _contracts(a, assertions=["<script>alert(1)</script>"])
    _save(a / "contracts/vf-07/vf07.json", {"result": {"duration": 2.0, "width": 80, "height": 60}})
    run = load(select(discover(tmp_path), "left"))
    page = run_html(run, tmp_path / "reports/report.html")
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "test-vf-07.log" in page
    assert "80×60" in page and "vf07.json" in page
    assert "href=\"../baseline/" in page
    assert "<style>" in page


def test_cli_list_report_compare_and_no_overwrite(tmp_path, capsys):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _static(a, 100)
    _static(b, 120)
    _contracts(a)
    _contracts(b, "failed")
    assert main(["list", "--results-root", str(tmp_path), "--role", "baseline"]) == 0
    assert "left" in capsys.readouterr().out
    target = tmp_path / "reports/report.html"
    args = ["report", "right", "--results-root", str(tmp_path), "--format", "html", "--output", str(target)]
    assert main(args) == 0
    assert "right" in target.read_text()
    assert main(args) == 2
    assert "right" in target.read_text()
    comparison = tmp_path / "reports/compare.html"
    assert main(["compare", "left", "right", "--results-root", str(tmp_path),
                 "--format", "html", "--output", str(comparison)]) == 0
    assert "VF-07" in comparison.read_text()


def test_incomplete_and_legacy_runs_do_not_invent_data(tmp_path):
    old = tmp_path / BASELINE / "historical"
    _save(old / "metadata.json", {"resolved_commit": BASELINE, "run_id": "historical",
          "requested_categories": ["static", "contracts"], "collection_status": "partial"})
    run = load(select(discover(tmp_path), "historical"))
    assert run["role"] == "baseline" and run["status"] == "infrastructure error"
    assert run["static"] is None and run["contracts"] is None
    assert "Not recorded" in run_html(run, tmp_path / "report.html")


def test_framework_and_snapshot_runs_are_distinct_from_commits(tmp_path):
    snapshot = tmp_path / "snapshots" / ("f" * 64) / "local"
    _save(snapshot / "metadata.json", {"source_kind": "working_tree_snapshot", "base_commit": INITIAL_REFACTORED,
          "resolved_commit": None, "run_id": "local", "requested_categories": ["static"],
          "collection_status": "complete", "verification_status": "skipped"})
    _save(tmp_path / "framework" / "run-1" / "summary.json", {
        "command": "python -m pytest fase2/tests/evaluation", "run_id": "self-tests",
        "passed": 10, "failed": 0, "source_head": INITIAL_REFACTORED})
    rows = discover(tmp_path)
    assert {row["role"] for row in rows} == {"snapshot", "framework"}
    assert select(rows, "local")["commit"] == INITIAL_REFACTORED
    assert select(rows, "self-tests")["kind"] == "framework"
    with pytest.raises(ValueError, match="Snapshots"):
        compare(load(select(rows, "local")), load(select(rows, "local")))


def test_missing_static_runs_are_explicitly_not_comparable(tmp_path):
    a = _run(tmp_path, "baseline", BASELINE, "left", categories=("contracts",))
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right", categories=("contracts",))
    _contracts(a)
    _contracts(b)
    left, right = [load(x) for x in discover(tmp_path)]
    result = compare(left, right)
    assert all(m["difference"] is None and "not recorded" in m["limitation"] for m in result["metrics"])
    assert result["contracts"][0]["state"] == "passed both"


@pytest.mark.parametrize("status,expected", [("infrastructure_error", "infrastructure error"),
                                             ("skipped", "skipped")])
def test_nonfunctional_contract_states_are_not_regressions(tmp_path, status, expected):
    a = _run(tmp_path, "baseline", BASELINE, "left")
    b = _run(tmp_path, "refactored", INITIAL_REFACTORED, "right")
    _contracts(a)
    _contracts(b)
    path = b / "contracts/summary.json"
    data = json.loads(path.read_text())
    data["contracts"][0]["status"] = status
    _save(path, data)
    result = compare(*[load(run) for run in discover(tmp_path)])
    assert result["contracts"][0]["state"] == expected
    assert result["regressions"] == []
