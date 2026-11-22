"""Terminal and standalone HTML views of recorded evaluation evidence."""

import html
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

from .reporting import METRICS, contract_counts, test_counts


def _value(value) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _contract_issues(run: dict, item: dict | None) -> list[str]:
    if not item or not item.get("junit"):
        return []
    base = run["path"].resolve()
    path = (base / "contracts" / item["junit"]).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        return []
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return []
    issues = []
    for case in root.iter("testcase"):
        for tag in ("failure", "error"):
            for failure in case.findall(tag):
                lines = (failure.text or "").strip().splitlines()
                message = (failure.get("message") or (lines[0] if lines else tag)).splitlines()
                detail = message[0] if message else tag
                issues.append(f"{case.get('name', 'test')}: {detail[:220]}")
    return issues


def _contract_artifacts(run: dict, item: dict | None, output: Path) -> tuple[list[str], list[str]]:
    """Summarize recorded observable properties and link JSON evidence."""
    if not item or not item.get("junit"):
        return [], []
    base = (run["path"] / "contracts").resolve()
    folder = (base / Path(item["junit"]).parent).resolve()
    try:
        folder.relative_to(base)
    except ValueError:
        return [], []
    properties, links = [], []
    for path in sorted(folder.glob("*.json")):
        try:
            path.resolve().relative_to(base)
        except ValueError:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        facts = []
        if result.get("duration") is not None:
            facts.append(f"duration {_value(result['duration'])} s")
        if result.get("width") is not None and result.get("height") is not None:
            facts.append(f"{result['width']}×{result['height']}")
        if data.get("mean_brightness") is not None:
            facts.append(f"mean brightness {_value(data['mean_brightness'])}")
        if facts:
            properties.append(f"{path.name}: " + ", ".join(facts))
        relative = path.relative_to(run["path"]).as_posix()
        links.append(_link(output, run, relative, path.name))
    return properties, links


def _metrics(run: dict) -> list[tuple[str, object, str]]:
    summary = run.get("static") or {}
    groups = summary.get("metrics") or {}
    return [(title, (groups.get(group) or {}).get(key) if (groups.get(group) or {}).get("status") == "complete" else None, unit)
            for title, group, key, unit in METRICS]


def list_text(runs: list[dict]) -> str:
    lines = ["Role          Commit    Date (UTC)                 Run ID                                  Categories                Status", "-" * 125]
    for run in runs:
        commit = (run["commit"] or "-")[:8]
        date = (run["date"] or "unrecorded")[:25]
        categories = ",".join(run["categories"])
        lines.append(f"{run['role'][:13]:13} {commit:8} {date:25} {run['run_id']:39} {categories:25} {run['status']}")
        lines.append(f"  Path: {run['relative_path']}")
        if run.get("contracts"):
            failures = [item.get("id") for item in run["contracts"].get("contracts", []) if item.get("status") == "failed"]
            if failures:
                lines.append("  Failed contracts: " + ", ".join(failures))
    return "\n".join(lines)


def run_text(run: dict) -> str:
    lines = ["PictuRAS Evaluation", "=" * 25,
             f"Role: {run['role']}", f"Commit: {run['commit'] or 'unrecorded'}",
             f"Run: {run['run_id']}", f"Date: {run['date'] or 'unrecorded'}",
             f"Categories: {', '.join(run['categories'])}", f"Status: {run['status']}"]
    if run["kind"] == "framework":
        data = run["metadata"]
        lines += ["", "Framework tests", f"Passed: {_value(data.get('passed', (data.get('counts') or {}).get('passed')))}",
                  f"Failed: {_value(data.get('failed', (data.get('counts') or {}).get('failures')))}"]
    if run.get("static"):
        lines += ["", "M2 — Static metrics"]
        lines += [f"  {title}: {_value(value)} {unit}" for title, value, unit in _metrics(run)]
    if run.get("functional"):
        lines += ["", "M3 — Revision-specific suites (counts are not equivalent across revisions)"]
        for suite in run["functional"].get("suites", []):
            c = test_counts(suite)
            lines.append(f"  {suite.get('id', 'unknown')} [{suite.get('service', 'unrecorded')}]: "
                         f"{_value(c['passed'])} passed, {_value(c['failed'])} failed, "
                         f"{_value(c['skipped'])} skipped; {suite.get('status', 'unavailable')}")
    if run.get("contracts"):
        lines += ["", "M4 — Shared contracts (test cases, not assertion counts)"]
        for item in run["contracts"].get("contracts", []):
            c = contract_counts(item)
            lines.append(f"  {item.get('id', '?')} [{item.get('level', '?')}]: {item.get('status', 'unavailable')} "
                         f"({ _value(c['passed'])} passed, {_value(c['failed'])} failed)")
            if item.get("status") == "failed":
                lines += ["    " + issue for issue in _contract_issues(run, item)]
    lines += ["", f"Evidence: {run['path']}"]
    return "\n".join(lines)


def comparison_text(result: dict) -> str:
    a, b = result["baseline"], result["refactored"]
    lines = ["PictuRAS Evaluation Comparison", "=" * 32,
             f"Left:  {a['role']} {a['commit']} / {a['run_id']}",
             f"Right: {b['role']} {b['commit']} / {b['run_id']}", "", "M2 — Static metrics"]
    for metric in result["metrics"]:
        note = f" ({metric['limitation']})" if metric["limitation"] else ""
        diff = _value(metric["difference"])
        rel = _value(metric["relative_percent"])
        difference_unit = "percentage points" if metric["unit"] == "%" else metric["unit"]
        lines.append(f"  {metric['name']}: {_value(metric['baseline'])} → {_value(metric['refactored'])}; "
                     f"Δ {diff} {difference_unit}; Δ% {rel}{note}")
    lines += ["", "M3 — Existing suites (reported separately; counts are not equivalent)"]
    for run in (a, b):
        lines.append(f"  {run['role']}:")
        for suite in (run.get("functional") or {}).get("suites", []):
            c = test_counts(suite)
            lines.append(f"    {suite.get('id')}: {_value(c['passed'])} passed, {_value(c['failed'])} failed")
        if not run.get("functional"):
            lines.append("    unavailable")
    lines += ["", "M4 — Shared contracts"]
    if not result["contracts"]:
        lines.append("  unavailable")
    for item in result["contracts"]:
        note = f" ({item['limitation']})" if item["limitation"] else ""
        lines.append(f"  {item['id']}: {item['baseline']} → {item['refactored']}: {item['state']}{note}")
        if item["state"] == "regression":
            lines += ["    " + issue for issue in _contract_issues(b, item["refactored_item"])]
    lines += ["", "Regressions: " + (", ".join(result["regressions"]) or "none confirmed by comparable contracts"),
              f"Evidence: {a['path']}", f"          {b['path']}"]
    return "\n".join(lines)


_CSS = """body{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#182532;background:#fafcfe}
h1,h2{color:#183e5c}table{border-collapse:collapse;width:100%;margin:1rem 0 2rem}th,td{border:1px solid #cdd7df;padding:.5rem;text-align:left;vertical-align:top}
th{background:#e9f1f7}code{overflow-wrap:anywhere}.failed,.regression{color:#a62121;font-weight:700}.passed,.resolved{color:#176337}
.note{background:#fff4d9;padding:.7rem;border-left:4px solid #bb8b19}a{color:#075b9c}small{color:#526271}pre{white-space:pre-wrap}td{overflow-wrap:anywhere}"""


def _h(value) -> str:
    return html.escape(_value(value), quote=True)


def _link(output: Path, run: dict, relative: str, label: str) -> str:
    """Only link existing evidence inside the selected run."""
    candidate = (run["path"] / relative).resolve()
    try:
        candidate.relative_to(run["path"].resolve())
    except ValueError:
        return _h(label) + " (unavailable)"
    if not candidate.is_file():
        return _h(label) + " (unavailable)"
    target = os.path.relpath(candidate, output.parent.resolve())
    return f'<a href="{html.escape(quote(Path(target).as_posix(), safe="/.."), quote=True)}">{_h(label)}</a>'


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{_h(value)}</th>" for value in headers)
    body = "".join("<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _page(title: str, sections: list[str]) -> str:
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{_h(title)}</title><style>{_CSS}</style></head><body>"
            f"<h1>{_h(title)}</h1>" + "".join(sections) + "</body></html>\n")


def _overview(run: dict) -> str:
    rows = [[_h(key), _h(value)] for key, value in (
        ("Role", run["role"]), ("Full commit / base", run["commit"]), ("Run ID", run["run_id"]),
        ("Date (UTC)", run["date"]), ("Categories", ", ".join(run["categories"])),
        ("Status", run["status"]))]
    return "<h2>Overview</h2>" + _table(["Field", "Value"], rows)


def _static(run: dict, output: Path) -> str:
    if not run.get("static"):
        return "<h2>M2 — Static metrics</h2><p>Not recorded in this run.</p>"
    rows = [[_h(name), _h(value), _h(unit)] for name, value, unit in _metrics(run)]
    scope = run.get("scope") or {}
    tools = (run["static"].get("tool_versions") or {})
    detail = (f"<p>Scope: {_h(scope.get('boundary'))}; files: {_h(len(scope.get('core_python_files', [])))} "
              f"({_h(', '.join(scope.get('core_python_files', [])))}). ")
    detail += "Tool versions: " + ", ".join(f"{_h(k)} {_h(v)}" for k, v in tools.items()) + ".</p>"
    duplication = ((run["static"].get("metrics") or {}).get("jscpd_internal") or {})
    detail += (f"<p>jscpd threshold: {_h(duplication.get('minimum_lines'))} lines, "
               f"{_h(duplication.get('minimum_tokens'))} tokens. "
               "Internal duplication applies only to the video-processing core.</p>")
    inventory = None
    try:
        inventory = json.loads((run["path"] / "static/inventory.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    modules = inventory.get("modules", []) if isinstance(inventory, dict) else []
    dependency_table = (_table(["Production module", "Imports"], [
        [_h(module.get("path")), _h(", ".join(module.get("imports", [])))] for module in modules])
        if modules else "<p>Dependency inventory unavailable.</p>")
    return ("<h2>M2 — Static metrics</h2>" + detail + _table(["Metric", "Value", "Unit"], rows)
            + "<h3>Module and import inventory</h3>" + dependency_table
            + _link(output, run, "static/scope.json", "Measurement scope") + " · "
            + _link(output, run, "static/summary.json", "Raw M2 summary") + " · "
            + _link(output, run, "static/inventory.json", "Raw inventory"))


def _functional(run: dict, output: Path) -> str:
    if not run.get("functional"):
        return "<h2>M3 — Existing tests</h2><p>Not recorded in this run.</p>"
    rows = []
    for suite in run["functional"].get("suites", []):
        c = test_counts(suite)
        log = "functional/" + suite["test_log"] if suite.get("test_log") else ""
        rows.append([_h(suite.get("id")), _h(suite.get("service")), _h(suite.get("kind")),
                     _h(c["passed"]), _h(c["failed"]), _h(c["skipped"]),
                     _h(suite.get("duration_seconds")), _h(suite.get("status")),
                     _link(output, run, log, "log") if log else "unavailable"])
    return (f"<h2>M3 — Existing tests: {_h(run['role'])} / {_h(run['run_id'])}</h2><p class=\"note\">These suites differ by revision; "
            "their test counts are not equivalent functional evidence.</p>"
            + _table(["Suite", "Service", "Runner", "Passed", "Failed", "Skipped", "Seconds", "Status", "Evidence"], rows))


def _contracts(run: dict, output: Path) -> str:
    if not run.get("contracts"):
        return "<h2>M4 — Shared contracts</h2><p>Not recorded in this run.</p>"
    rows = []
    for item in run["contracts"].get("contracts", []):
        c = contract_counts(item)
        issues = "; ".join(_contract_issues(run, item)) or "—"
        log = "contracts/" + item["log"] if item.get("log") else ""
        properties, artifacts = _contract_artifacts(run, item, output)
        rows.append([_h(item.get("id")), _h(item.get("level")), _h(item.get("status")),
                     _h("; ".join(item.get("assertions", []))),
                     _h(c["cases"]), _h(c["passed"]), _h(c["failed"]),
                     _h("; ".join(properties)) + "<br>" + _h(issues),
                     ", ".join(([_link(output, run, log, "log")] if log else []) + artifacts) or "unavailable"])
    return ("<h2>M4 — Shared functional contracts</h2>"
            + _table(["Contract", "Level", "Status", "Criteria", "Test cases", "Passed", "Failed", "Failed assertions / errors", "Evidence"], rows))


def _evidence(run: dict, output: Path) -> str:
    links = [_link(output, run, "metadata.json", "Run metadata")]
    for category in ("static", "functional", "contracts"):
        if run.get(category):
            links.append(_link(output, run, f"{category}/summary.json", f"{category} JSON"))
    if run.get("contracts"):
        links.append("Contract suite SHA-256: " + _h(run["contracts"].get("suite_sha256")))
        links.append("Docker images: " + _h(run["contracts"].get("image_ids")))
        links.append("Docker versions: " + _h(run["contracts"].get("docker_versions")))
        input_hashes = {key: value for item in run["contracts"].get("contracts", [])
                        for key, value in item.get("input_hashes", {}).items()}
        links += [f"Input {_h(key)}: <code>{_h(value)}</code>" for key, value in sorted(input_hashes.items())]
    return "<h2>Evidence and metadata</h2><ul>" + "".join(f"<li>{value}</li>" for value in links) + "</ul>"


def run_html(run: dict, output: Path) -> str:
    sections = [_overview(run)]
    if run["kind"] == "framework":
        sections.append("<h2>Framework tests</h2><pre>" + _h(run_text(run)) + "</pre>"
                        + _link(output, run, Path(run["relative_path"]).name, "Summary JSON") + " · "
                        + _link(output, run, run["metadata"].get("junit", "junit.xml"), "JUnit report"))
    else:
        sections += [_static(run, output), _functional(run, output), _contracts(run, output)]
        failed = [item for item in (run.get("contracts") or {}).get("contracts", []) if item.get("status") == "failed"]
        sections.append("<h2>Functional failures</h2><p>" +
                        (_h(", ".join(item["id"] for item in failed)) if failed else "None recorded in this run") + "</p>")
        sections.append(_evidence(run, output))
    return _page("PictuRAS Evaluation Report", sections)


def comparison_html(result: dict, output: Path) -> str:
    a, b = result["baseline"], result["refactored"]
    sections = ["<h2>Selected evaluations</h2>", _overview(a), _overview(b)]
    rows = []
    for m in result["metrics"]:
        difference = _value(m["difference"])
        if m["difference"] is not None and m["unit"] == "%":
            difference += " percentage points"
        rows.append([_h(m["name"]), _h(m["baseline"]), _h(m["refactored"]),
                     _h(difference), _h(m["relative_percent"]), _h(m["unit"]),
                     _h(m["limitation"] or "Same measurement protocol; interpret in context")])
    sections += ["<h2>M2 — Static metrics comparison</h2>",
                 "<p class=\"note\">These values describe the selected Python video-processing core. "
                 "A lower complexity value alone does not establish improved modularity; size and duplication "
                 "have different interpretations. Relative change is omitted when the left value is zero.</p>",
                 _table(["Metric", "Left", "Right", "Absolute Δ", "Relative Δ %", "Unit", "Interpretation / limit"], rows)]
    for side in (result["baseline_static"], result["refactored_static"]):
        if side is not a and side is not b:
            sections.append(f"<p>Supplementary M2 run: {_h(side['relative_path'])}</p>")
        sections.append(_static(side, output))
    sections += [_functional(a, output), _functional(b, output)]
    contract_rows = []
    for item in result["contracts"]:
        issues = "; ".join(_contract_issues(b, item["refactored_item"])) or "—"
        links = []
        observations = []
        for run, entry in ((a, item["baseline_item"]), (b, item["refactored_item"])):
            if entry and entry.get("log"):
                links.append(_link(output, run, "contracts/" + entry["log"], run["role"] + " log"))
            facts, artifacts = _contract_artifacts(run, entry, output)
            if item["state"] in {"regression", "resolved", "failed both"}:
                observations += [f"{run['role']}: {fact}" for fact in facts]
            links += artifacts
        contract_rows.append([_h(item["id"]), _h(item["description"]), _h(item["level"]), _h(item["baseline"]),
                              _h(item["refactored"]), _h(item["state"]),
                              _h(item["limitation"] or ("; ".join(observations + [issues]))), ", ".join(links)])
    sections += ["<h2>M4 — Shared contract comparison</h2>",
                 _table(["ID", "Criteria", "Level", "Left", "Right", "Comparison", "Failed assertions / limit", "Evidence"], contract_rows),
                 "<h2>Functional regressions</h2><p class=\"regression\">" +
                 _h(", ".join(result["regressions"]) or "None confirmed by comparable contracts") + "</p>",
                 _evidence(a, output), _evidence(b, output)]
    return _page("PictuRAS Evaluation Comparison", sections)
