import json
from pathlib import Path

from fase2.evaluation.static import (
    _cross_duplication, _radon_cc_summary, _radon_raw_summary,
    collect_static, module_inventory, source_scope,
)


def test_scope_includes_every_present_video_worker_and_separates_integration(tmp_path):
    for directory in ("Tools/video", "Tools/video_effects", "Tools/video_frames", "Tools/video_subtitles"):
        root = tmp_path / directory
        root.mkdir(parents=True)
        (root / "worker.py").write_text("VALUE = 1\n")
        (root / "__init__.py").write_text("")
        (root / "tests").mkdir()
        (root / "tests" / "test_worker.py").write_text("assert True\n")
    integration = tmp_path / "projects/utils/video.js"
    integration.parent.mkdir(parents=True)
    integration.write_text("// orchestration\n")
    scope = source_scope(tmp_path)
    assert len(scope["core_python_files"]) == 4
    assert "projects/utils/video.js" in scope["subsystem_integration_files"]
    assert all("tests" not in name and "__init__" not in name for name in scope["core_python_files"])


def test_inventory_preserves_baseline_ast_counting(tmp_path):
    source = tmp_path / "Tools/video"
    source.mkdir(parents=True)
    (source / "worker.py").write_text("import os\nfrom pathlib import Path\nclass Worker:\n    def run(self):\n        return 1\n")
    data = module_inventory(tmp_path, ["Tools/video/worker.py"])
    assert data["modules"][0] == {
        "path": "Tools/video/worker.py", "physical_lines": 5,
        "functions": 1, "classes": 1, "imports": ["os", "pathlib"],
    }


def test_radon_summaries_keep_historical_block_mean_distinct_from_functions():
    cc = {"worker.py": [
        {"type": "class", "name": "Worker", "lineno": 1, "complexity": 2, "rank": "A",
         "methods": [{"type": "method", "name": "run", "complexity": 6}]},
        {"type": "method", "name": "run", "lineno": 2, "complexity": 6, "rank": "B"},
    ]}
    summary = _radon_cc_summary(cc)
    assert summary["block_count"] == 2
    assert summary["mean_block_complexity"] == 4
    assert summary["function_method_count"] == 1
    assert summary["mean_function_method_complexity"] == 6
    raw = _radon_raw_summary({"worker.py": {"loc": 10, "sloc": 7}})
    assert raw["physical_loc"] == 10 and raw["sloc"] == 7


def test_missing_external_tools_leave_inventory_and_partial_results(tmp_path):
    source = tmp_path / "source"
    module = source / "Tools/video/worker.py"
    module.parent.mkdir(parents=True)
    module.write_text("VALUE = 1\n")
    output = tmp_path / "results"
    result = collect_static(source, output, python="missing-python-tool", jscpd="missing-jscpd-tool")
    assert result["status"] == "partial"
    assert result["metrics"]["inventory"]["status"] == "complete"
    assert result["metrics"]["radon_cc"]["status"] == "unavailable"
    assert result["metrics"]["jscpd_internal"]["status"] == "unavailable"
    assert json.loads((output / "summary.json").read_text())["status"] == "partial"


def test_cross_duplication_excludes_clones_within_image_tools():
    data = {"duplicates": [
        {"firstFile": {"name": "Tools/video/effects.py", "start": 2},
         "secondFile": {"name": "Tools/brightness/brightness.py", "start": 3},
         "lines": 6, "tokens": 50},
        {"firstFile": {"name": "Tools/brightness/brightness.py", "start": 4},
         "secondFile": {"name": "Tools/rotate/rotate.py", "start": 5},
         "lines": 8, "tokens": 60},
    ]}
    result = _cross_duplication(data, ["Tools/video/effects.py"],
                                ["Tools/brightness/brightness.py", "Tools/rotate/rotate.py"])
    assert result["clone_count"] == 1
    assert result["clones"][0]["first_file"] == "Tools/video/effects.py"
