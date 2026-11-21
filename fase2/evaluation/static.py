"""Host-side static measurements over an explicit video source boundary."""

import ast
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .results import write_json


VIDEO_DIRECTORIES = (
    "Tools/video",
    "Tools/video_effects",
    "Tools/video_subtitles",
    "Tools/video_frames",
)
IMAGE_EFFECTS = (
    "binarization", "border", "brightness", "contrast", "cut", "resize", "rotate", "saturation"
)
SUBSYSTEM_PATHS = (
    "projects/utils/video.js",
    "projects/utils/project_msg.js",
    "projects/utils/rabbit_mq.js",
    "projects/utils/imageStorage.js",
    "projects/utils/frameResults.js",
    "projects/utils/processBatch.js",
    "projects/routes/projects.js",
    "apiGateway/routes/projects.js",
    "wsGateway/index.js",
    "wsGateway/utils/rabbit_mq.js",
    "imageStorageService/server.js",
    "rabbitMQ/definitions.json",
    "docker-compose.yaml",
)


def source_scope(source: Path) -> dict:
    """Select all present video workers, including any residual legacy worker."""
    directories = [name for name in VIDEO_DIRECTORIES if (source / name).is_dir()]
    files = sorted(
        str(path.relative_to(source))
        for directory in directories
        for path in (source / directory).glob("*.py")
        if path.name != "__init__.py"
    )
    if not files:
        raise ValueError("No production Python video modules found in the selected commit")
    image_files = [
        f"Tools/{name}/{name}.py" for name in IMAGE_EFFECTS
        if (source / f"Tools/{name}/{name}.py").is_file()
    ]
    integration = [name for name in SUBSYSTEM_PATHS if (source / name).is_file()]
    return {
        "boundary": "video-processing Python core",
        "video_directories": directories,
        "core_python_files": files,
        "core_file_sha256": {
            name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in files
        },
        "image_effect_files_for_cross_duplication": image_files,
        "subsystem_integration_files": integration,
        "integration_file_sha256": {
            name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in integration
        },
        "excluded": "tests, __init__.py, generated files, and non-video tools",
    }


def module_inventory(source: Path, files: list[str]) -> dict:
    """Preserve the AST and line-count procedure from collect_video_baseline.py."""
    modules = []
    for name in files:
        content = (source / name).read_text(encoding="utf-8")
        tree = ast.parse(content, filename=name)
        imports = sorted({
            alias.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        })
        modules.append({
            "path": name,
            "physical_lines": len(content.splitlines()),
            "functions": sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree)),
            "classes": sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree)),
            "imports": imports,
        })
    return {"scope": files, "modules": modules}


def run_command(command: list[str], cwd: Path, log: Path, commands: list[dict], timeout: int = 300) -> subprocess.CompletedProcess:
    started = time.perf_counter()
    entry = {"argv": command, "cwd": str(cwd), "log": str(log)}
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, timeout=timeout)
        entry.update({"exit_code": result.returncode, "duration_seconds": round(time.perf_counter() - started, 4)})
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        return result
    except (OSError, subprocess.TimeoutExpired) as error:
        entry.update({"exit_code": None, "duration_seconds": round(time.perf_counter() - started, 4), "error": str(error)})
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(str(error) + "\n", encoding="utf-8")
        raise
    finally:
        commands.append(entry)


def _radon_cc_summary(data: dict) -> dict:
    # The historical 4.56 mean used Radon's 41 top-level blocks, classes included.
    blocks = [block for module in data.values() for block in module]
    functions = [block for block in blocks if block["type"] in {"function", "method"}]
    ranks = {rank: sum(block["rank"] == rank for block in blocks) for rank in "ABCDEF"}
    return {
        "block_count": len(blocks),
        "mean_block_complexity": statistics.mean(block["complexity"] for block in blocks) if blocks else None,
        "maximum_complexity": max((block["complexity"] for block in blocks), default=None),
        "blocks_by_rank": ranks,
        "function_method_count": len(functions),
        "mean_function_method_complexity": statistics.mean(block["complexity"] for block in functions) if functions else None,
        "functions_and_methods": [
            {"module": name, "name": block["name"], "line": block["lineno"],
             "complexity": block["complexity"], "rank": block["rank"]}
            for name, entries in data.items() for block in entries
            if block["type"] in {"function", "method"}
        ],
    }


def _radon_raw_summary(data: dict) -> dict:
    modules = [
        {"path": name, "loc": values["loc"], "sloc": values["sloc"]}
        for name, values in sorted(data.items())
    ]
    sizes = [item["loc"] for item in modules]
    return {
        "module_count": len(modules), "physical_loc": sum(sizes),
        "sloc": sum(item["sloc"] for item in modules),
        "average_module_loc": statistics.mean(sizes) if sizes else None,
        "largest_module_loc": max(sizes, default=None), "modules": modules,
    }


def _jscpd_summary(data: dict) -> dict:
    total = data["statistics"]["total"]
    return {
        "clones": total["clones"], "duplicated_lines": total["duplicatedLines"],
        "duplicated_line_percentage": total["percentage"],
        "sources": total["sources"], "lines": total["lines"],
    }


def _cross_duplication(data: dict, video_files: list[str], image_files: list[str]) -> dict:
    video = set(video_files)
    image = set(image_files)
    matches = []
    for clone in data["duplicates"]:
        first = clone["firstFile"]["name"]
        second = clone["secondFile"]["name"]
        if (first in video and second in image) or (first in image and second in video):
            matches.append({
                "first_file": first, "first_start": clone["firstFile"]["start"],
                "second_file": second, "second_start": clone["secondFile"]["start"],
                "lines": clone["lines"], "tokens": clone["tokens"],
            })
    return {
        "clone_count": len(matches), "clones": matches,
        "note": "No cross-boundary percentage: jscpd's combined percentage includes image-image clones.",
    }


def _staged_jscpd(source: Path, files: list[str], output: Path, command_name: str,
                  commands: list[dict], label: str, video_files: list[str] | None = None,
                  image_files: list[str] | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="picturas-jscpd-") as directory:
        stage = Path(directory)
        for name in files:
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, destination)
        report_dir = output / label
        report_dir.mkdir()
        command = [command_name, str(stage), "--pattern", "**/*.py",
                   "--min-lines", "5", "--min-tokens", "50",
                   "--reporters", "json", "--output", str(report_dir), "--silent"]
        result = run_command(command, source, report_dir / "command.log", commands)
        if result.returncode:
            raise RuntimeError(f"jscpd exited with status {result.returncode}")
        report = report_dir / "jscpd-report.json"
        if not report.is_file():
            raise RuntimeError("jscpd did not create jscpd-report.json")
        data = json.loads(report.read_text(encoding="utf-8"))
        summary = _jscpd_summary(data)
        summary["files"] = files
        summary["minimum_lines"] = 5
        summary["minimum_tokens"] = 50
        if video_files is not None and image_files is not None:
            summary = {
                "combined_sample": summary,
                "video_image_cross": _cross_duplication(data, video_files, image_files),
            }
        return summary


def collect_static(source: Path, output: Path, python: str = sys.executable,
                   jscpd: str = "jscpd") -> dict:
    """Collect independent metrics; preserve partial evidence on tool failures."""
    output.mkdir(parents=True, exist_ok=True)
    commands: list[dict] = []
    summary: dict = {"status": "partial", "metrics": {}, "tool_versions": {}, "commands": commands}
    scope = source_scope(source)
    write_json(output / "scope.json", scope)
    try:
        inventory = module_inventory(source, scope["core_python_files"])
        write_json(output / "inventory.json", inventory)
        summary["metrics"]["inventory"] = {
            "status": "complete", "module_count": len(inventory["modules"]),
            "physical_lines": sum(item["physical_lines"] for item in inventory["modules"]),
        }
    except (OSError, SyntaxError, UnicodeError) as error:
        summary["metrics"]["inventory"] = {"status": "failed", "error": str(error)}

    summary["tool_versions"]["framework_python"] = sys.version.split()[0]
    for tool, command in (("metric_python", [python, "--version"]),
                          ("radon", [python, "-m", "radon", "--version"]),
                          ("jscpd", [jscpd, "--version"])):
        try:
            result = run_command(command, source, output / f"{tool}-version.log", commands)
            summary["tool_versions"][tool] = (result.stdout or result.stderr).strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            summary["tool_versions"][tool] = None

    for metric, parser in (("cc", _radon_cc_summary), ("raw", _radon_raw_summary)):
        key = f"radon_{metric}"
        command = [python, "-m", "radon", metric, *scope["core_python_files"], "-j"]
        try:
            result = run_command(command, source, output / f"radon-{metric}.log", commands)
            if result.returncode:
                raise RuntimeError(f"radon {metric} exited with status {result.returncode}")
            data = json.loads(result.stdout)
            write_json(output / f"radon-{metric}.json", data)
            summary["metrics"][key] = {"status": "complete", **parser(data)}
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, KeyError) as error:
            summary["metrics"][key] = {"status": "unavailable", "error": str(error)}

    for label, files in (("internal", scope["core_python_files"]),
                         ("video_image", scope["core_python_files"] + scope["image_effect_files_for_cross_duplication"])):
        try:
            metric = _staged_jscpd(
                source, files, output, jscpd, commands, label,
                scope["core_python_files"] if label == "video_image" else None,
                scope["image_effect_files_for_cross_duplication"] if label == "video_image" else None,
            )
            summary["metrics"][f"jscpd_{label}"] = {"status": "complete", **metric}
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, KeyError) as error:
            summary["metrics"][f"jscpd_{label}"] = {"status": "unavailable", "error": str(error)}

    if all(item["status"] == "complete" for item in summary["metrics"].values()):
        summary["status"] = "complete"
    write_json(output / "summary.json", summary)
    return summary
