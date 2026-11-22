"""Read recorded evaluations and compare evidence without rerunning it."""

import json
from pathlib import Path

from .index import BASELINE, INITIAL_REFACTORED


METRICS = (
    ("Mean complexity (all blocks)", "radon_cc", "mean_block_complexity", "CC"),
    ("Maximum complexity", "radon_cc", "maximum_complexity", "CC"),
    ("Physical LOC", "radon_raw", "physical_loc", "lines"),
    ("SLOC", "radon_raw", "sloc", "lines"),
    ("Production modules", "radon_raw", "module_count", "modules"),
    ("Largest module", "radon_raw", "largest_module_loc", "lines"),
    ("Internal duplicated lines", "jscpd_internal", "duplicated_lines", "lines"),
    ("Internal duplication", "jscpd_internal", "duplicated_line_percentage", "%"),
)


def _json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _role(meta: dict) -> str:
    if meta.get("source_kind") == "working_tree_snapshot":
        return "snapshot"
    if meta.get("role") in {"baseline", "refactored", "unclassified"}:
        return meta["role"]
    commit = meta.get("resolved_commit")
    return "baseline" if commit == BASELINE else "refactored" if commit == INITIAL_REFACTORED else "unclassified"


def _state(meta: dict) -> str:
    collection = meta.get("collection_status", "unavailable")
    verification = meta.get("verification_status", "unavailable")
    if collection != "complete":
        if verification == "failed":
            return "partial collection; functional failure"
        return "infrastructure error" if collection in {"failed", "partial"} else "incomplete"
    if verification == "failed":
        return "functional failure"
    if verification == "unavailable":
        return "infrastructure error"
    return "passed" if verification == "passed" else "collected"


def discover(root: Path) -> list[dict]:
    """Discover runs from metadata; directory names never determine a role."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Results directory does not exist: {root}")
    runs = []
    for path in root.rglob("metadata.json"):
        meta = _json(path)
        if meta is None or "requested_categories" not in meta:
            continue
        run = path.parent
        runs.append({"path": run, "relative_path": run.relative_to(root).as_posix(),
                     "run_id": str(meta.get("run_id") or run.name), "role": _role(meta),
                     "commit": meta.get("resolved_commit") or meta.get("base_commit"),
                     "date": meta.get("started_at_utc"),
                     "categories": list(meta.get("requested_categories") or []),
                     "status": _state(meta), "metadata": meta,
                     "kind": "evaluation"})
    # Framework reports have a different historical schema and no metadata.json.
    for path in root.rglob("summary*.json"):
        data = _json(path)
        if data is None or "fase2/tests/evaluation" not in str(data.get("command", "")):
            continue
        runs.append({"path": path.parent, "relative_path": path.relative_to(root).as_posix(),
                     "run_id": str(data.get("run_id") or path.parent.name), "role": "framework",
                     "commit": data.get("base_commit") or data.get("source_head"),
                     "date": data.get("executed_at_utc"), "categories": ["framework tests"],
                     "status": "failed" if data.get("failed", data.get("counts", {}).get("failures", 0)) else "passed",
                     "metadata": data, "kind": "framework"})
    return sorted(runs, key=lambda item: (item["date"] or "", item["relative_path"]))


def select(runs: list[dict], selector: str) -> dict:
    """Select an exact run ID or recorded relative path; reject ambiguity."""
    if not selector or selector in {".", ".."}:
        raise ValueError("Specify a run ID or a path listed by the list command")
    exact = [run for run in runs if selector == run["relative_path"]]
    if not exact and Path(selector).is_absolute():
        resolved = Path(selector).expanduser().resolve()
        exact = [run for run in runs if run["path"].resolve() == resolved]
    if not exact:
        exact = [run for run in runs if selector == run["run_id"]]
    if len(exact) == 1:
        return exact[0]
    if not exact:
        raise ValueError(f"Evaluation run not found: {selector}")
    matches = ", ".join(run["relative_path"] for run in exact)
    raise ValueError(f"Ambiguous run ID {selector!r}; select one path: {matches}")


def load(run: dict) -> dict:
    """Normalize only existing recorded fields; missing evidence remains missing."""
    if run["kind"] == "framework":
        return {**run, "static": None, "functional": None, "contracts": None}
    base = run["path"]
    return {**run, "static": _json(base / "static/summary.json"),
            "scope": _json(base / "static/scope.json"),
            "functional": _json(base / "functional/summary.json"),
            "contracts": _json(base / "contracts/summary.json")}


def test_counts(suite: dict) -> dict:
    counts = suite.get("counts")
    if not isinstance(counts, dict):
        return {"passed": None, "failed": None, "skipped": None}
    return {"passed": counts.get("passed", counts.get("pass")),
            "failed": counts.get("failed", counts.get("fail")),
            "skipped": counts.get("skipped")}


def contract_counts(contract: dict) -> dict:
    reports = [contract.get(key) for key in ("junit_result", "verification_junit_result")]
    reports = [item for item in reports if isinstance(item, dict)]
    if not reports:
        return {"cases": None, "passed": None, "failed": None, "skipped": None}
    tests = sum(item.get("tests", 0) for item in reports)
    failed = sum(item.get("failures", 0) + item.get("errors", 0) for item in reports)
    skipped = sum(item.get("skipped", 0) for item in reports)
    return {"cases": tests, "passed": tests - failed - skipped, "failed": failed, "skipped": skipped}


def _metric(run: dict, group: str, name: str):
    summary = run.get("static") or {}
    data = (summary.get("metrics") or {}).get(group) or {}
    return data.get(name) if data.get("status") == "complete" else None


def _static_compatibility(left: dict, right: dict, group: str) -> str | None:
    a, b = left.get("static"), right.get("static")
    if not a or not b:
        return "M2 was not recorded in both selected runs"
    sa, sb = left.get("scope"), right.get("scope")
    if not sa or not sb or sa.get("boundary") != sb.get("boundary"):
        return "measurement scope is missing or differs"
    tool = "jscpd" if group == "jscpd_internal" else "radon"
    va, vb = (a.get("tool_versions") or {}).get(tool), (b.get("tool_versions") or {}).get(tool)
    if not va or not vb or va != vb:
        return f"{tool} version is missing or differs"
    if group == "jscpd_internal":
        ma = (a.get("metrics") or {}).get(group) or {}
        mb = (b.get("metrics") or {}).get(group) or {}
        for key in ("minimum_lines", "minimum_tokens"):
            if ma.get(key) is None or ma.get(key) != mb.get(key):
                return f"jscpd {key} is missing or differs"
    return None


def compare(left: dict, right: dict, left_static: dict | None = None,
            right_static: dict | None = None) -> dict:
    """Compare explicit runs; optional M2 runs must match each selected commit."""
    if left["kind"] != "evaluation" or right["kind"] != "evaluation":
        raise ValueError("Comparison requires committed evaluation runs")
    if left["role"] == "snapshot" or right["role"] == "snapshot":
        raise ValueError("Snapshots cannot be compared as committed revisions")
    for primary, supplement in ((left, left_static), (right, right_static)):
        if supplement is not None:
            if supplement["kind"] != "evaluation" or supplement["commit"] != primary["commit"]:
                raise ValueError("Supplementary M2 run must belong to the same commit")
            if supplement.get("static") is None:
                raise ValueError("Supplementary run has no M2 measurements")
    sa, sb = left_static or left, right_static or right
    metrics = []
    for title, group, key, unit in METRICS:
        a, b = _metric(sa, group, key), _metric(sb, group, key)
        reason = _static_compatibility(sa, sb, group)
        if not reason and (not isinstance(a, (int, float)) or not isinstance(b, (int, float))):
            reason = "metric is unavailable"
        diff = b - a if reason is None else None
        relative = diff / a * 100 if diff is not None and a != 0 else None
        metrics.append({"name": title, "baseline": a, "refactored": b, "difference": diff,
                        "relative_percent": relative, "unit": unit, "limitation": reason})
    ac = {item.get("id"): item for item in (left.get("contracts") or {}).get("contracts", []) if item.get("id")}
    bc = {item.get("id"): item for item in (right.get("contracts") or {}).get("contracts", []) if item.get("id")}
    contracts = []
    for ident in sorted(ac.keys() | bc.keys()):
        a, b = ac.get(ident), bc.get(ident)
        reason = None
        if not a or not b:
            reason = "contract missing from one selected run"
        else:
            for field in ("suite_sha256", "assertions", "tolerances", "input_hashes", "level"):
                if field not in a or field not in b or a[field] != b[field]:
                    reason = f"contract {field} is missing or differs"
                    break
        astatus, bstatus = a.get("status", "unavailable") if a else "unavailable", b.get("status", "unavailable") if b else "unavailable"
        state = ("not comparable" if reason else "infrastructure error" if "infrastructure_error" in {astatus, bstatus}
                 else "skipped" if "skipped" in {astatus, bstatus}
                 else "regression" if astatus == "passed" and bstatus == "failed"
                 else "resolved" if astatus == "failed" and bstatus == "passed"
                 else "passed both" if astatus == bstatus == "passed"
                 else "failed both" if astatus == bstatus == "failed" else "unavailable")
        contracts.append({"id": ident, "baseline": astatus, "refactored": bstatus,
                          "state": state, "limitation": reason,
                          "level": (a or b or {}).get("level", "unrecorded"),
                          "description": "; ".join((a or b or {}).get("assertions", [])),
                          "baseline_item": a, "refactored_item": b})
    return {"baseline": left, "refactored": right, "baseline_static": sa,
            "refactored_static": sb, "metrics": metrics, "contracts": contracts,
            "regressions": [item["id"] for item in contracts if item["state"] == "regression"]}
