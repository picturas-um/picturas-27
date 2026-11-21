import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from fase2.evaluation.docker import (
    DockerError, DockerRunner, discover_suites, parse_test_output, validate_compose,
)


def source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    for directory, name in (("Tools/video", "effects.py"), ("projects", "utils/video.js")):
        path = source / directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("VALUE = 1\n")
    for name in ("Tools/video/tests/test_effects.py", "Tools/video/tests/conftest.py",
                 "projects/tests/video.test.js"):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# test\n")
    for name in ("Tools/video/Dockerfile", "projects/Dockerfile", "docker-compose.yaml"):
        path = source / name
        path.write_text("FROM scratch\n")
    return source


def config_for(source: Path, project: str) -> dict:
    return {
        "name": project,
        "volumes": {"image_data": {"name": project + "_image_data"}},
        "networks": {"default": {"name": project + "_default"}},
        "services": {
            "video_tool": {"build": {"context": str(source / "Tools"),
                                     "dockerfile": "video/Dockerfile"},
                           "volumes": [{"type": "volume", "source": "image_data", "target": "/app/images"}]},
            "projects": {"build": {"context": str(source / "projects"),
                                   "dockerfile": "Dockerfile"}, "volumes": []},
        },
    }


def fake_runner(tmp_path, test_failure=False, timeout=False, wrong_hash=False,
                build_failure=False, daemon_unavailable=False, volume_owner=None):
    source = source_tree(tmp_path)
    holder = {}
    calls = []

    def invoke(command, **kwargs):
        calls.append(command)
        runner = holder["runner"]
        if command[:2] == ["docker", "--version"]:
            return subprocess.CompletedProcess(command, 0, "Docker 29\n", "")
        if command[:3] == ["docker", "compose", "version"]:
            return subprocess.CompletedProcess(command, 0, "Compose 5\n", "")
        if command[:2] == ["docker", "info"]:
            return subprocess.CompletedProcess(command, 1 if daemon_unavailable else 0,
                                               "" if daemon_unavailable else "29\n", "")
        if command[:2] in (["docker", "ps"], ["docker", "volume"],
                           ["docker", "network"], ["docker", "image"]):
            if command[1:3] == ["image", "inspect"]:
                return subprocess.CompletedProcess(command, 0, "sha256:" + "a" * 64 + "\n", "")
            if command[1:3] == ["volume", "inspect"]:
                return subprocess.CompletedProcess(command, 0 if volume_owner else 1,
                                                   json.dumps({"com.docker.compose.project": volume_owner})
                                                   if volume_owner else "", "not found")
            return subprocess.CompletedProcess(command, 0, "", "")
        if "config" in command:
            return subprocess.CompletedProcess(command, 0,
                                               json.dumps(config_for(source, runner.project)), "")
        if "build" in command:
            return subprocess.CompletedProcess(command,
                                               1 if build_failure and command[-1] == "video_tool" else 0,
                                               "done\n", "")
        if "down" in command:
            return subprocess.CompletedProcess(command, 0, "done\n", "")
        if "run" in command and "--entrypoint" in command:
            service = command[command.index("--entrypoint") + 2]
            entrypoint = command[command.index("--entrypoint") + 1]
            if entrypoint in ("python", "node"):
                suite = next(s for s in discover_suites(source) if s["service"] == service)
                hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                          for name, path in suite["code_files"].items()}
                if wrong_hash and service == "video_tool":
                    hashes["/app/effects.py"] = "bad"
                return subprocess.CompletedProcess(command, 0, json.dumps({"hashes": hashes}), "")
            if timeout and service == "video_tool":
                raise subprocess.TimeoutExpired(command, 1, output="partial test output\n")
            code = 1 if test_failure and service == "video_tool" else 0
            return subprocess.CompletedProcess(command, code,
                                               "EVALUATION_TEST_START\n" + ("failed\n" if code else "passed\n"), "")
        raise AssertionError(command)

    runner = DockerRunner(source, tmp_path / "out", "test-run", invoke=invoke)
    holder["runner"] = runner
    return runner, calls


def test_discovers_existing_revision_suites(tmp_path):
    source = source_tree(tmp_path)
    suites = discover_suites(source)
    assert [(suite["id"], suite["service"]) for suite in suites] == [
        ("video-original-pytest", "video_tool"), ("projects-node-test", "projects")]
    assert all(source in suite["test_root"].parents for suite in suites)


def test_discovers_refactored_services_separately(tmp_path):
    source = source_tree(tmp_path)
    for directory in ("Tools/video_effects", "Tools/video_subtitles", "Tools/video_frames"):
        path = source / directory / "tests/test_worker.py"
        path.parent.mkdir(parents=True)
        path.write_text("def test_worker(): pass\n")
    assert {suite["service"] for suite in discover_suites(source)} == {
        "video_tool", "video_effects_tool", "video_subtitles_tool", "video_frames_tool", "projects"
    }


def test_parses_suite_counts_without_merging_them():
    python = parse_test_output("python-pytest", "74 passed in 37.81s\n")
    node = parse_test_output("node-test", "ℹ tests 8\nℹ pass 8\nℹ fail 0\nℹ duration_ms 72.2\n")
    assert python == {"counts": {"passed": 74}, "reported_duration_seconds": 37.81}
    assert node == {"counts": {"tests": 8, "pass": 8, "fail": 0},
                    "reported_duration_seconds": 0.0722}


@pytest.mark.parametrize("mutation", [
    lambda config: config["volumes"]["image_data"].update(external=True),
    lambda config: config["services"]["video_tool"].update(container_name="fixed-name"),
    lambda config: config["services"]["video_tool"].update(volumes=[{"type": "bind", "source": "/etc", "target": "/app"}]),
    lambda config: config["services"]["video_tool"]["build"].update(context="/tmp/outside"),
])
def test_rejects_unsafe_compose_resources(tmp_path, mutation):
    source = source_tree(tmp_path)
    config = config_for(source, "picturas-eval-test")
    mutation(config)
    with pytest.raises(DockerError):
        validate_compose(config, source, "picturas-eval-test", {"video_tool", "projects"})


def test_uses_selected_worktree_and_cleans_only_own_project(tmp_path):
    runner, commands = fake_runner(tmp_path)
    result = runner.collect()
    assert result["status"] == "complete"
    assert result["verification_status"] == "passed"
    assert len(result["suites"]) == 2
    assert all(suite["provenance"]["verified_file_count"] > 0 for suite in result["suites"])
    assert all(str(runner.source / "docker-compose.yaml") in command for command in commands
               if command[:2] == ["docker", "compose"] and "version" not in command)
    assert all("-p" not in command or command[command.index("-p") + 1] == runner.project for command in commands)
    assert not any("-v" in command and "down" in command for command in commands)
    assert any("down" in command for command in commands)
    assert "resolved configuration withheld" in (runner.output / "logs/compose-config.log").read_text()
    assert "services" not in (runner.output / "logs/compose-config.log").read_text()


@pytest.mark.parametrize("options,expected", [
    ({"test_failure": True}, ["failed", "passed"]),
    ({"timeout": True}, ["infrastructure_error", "passed"]),
    ({"wrong_hash": True}, ["infrastructure_error", "passed"]),
    ({"build_failure": True}, ["infrastructure_error", "passed"]),
])
def test_one_suite_failure_does_not_stop_other_suites_or_cleanup(tmp_path, options, expected):
    runner, commands = fake_runner(tmp_path, **options)
    result = runner.collect()
    assert [suite["status"] for suite in result["suites"]] == expected
    assert any("down" in command for command in commands)
    assert json.loads((runner.output / "summary.json").read_text())["suites"][-1]["status"] == "passed"
    if options.get("test_failure"):
        assert result["verification_status"] == "failed"
    else:
        assert result["status"] == "partial"
    if options.get("build_failure"):
        assert any(command[:3] == ["docker", "image", "rm"] for command in commands)
    if options.get("timeout"):
        assert "partial test output" in (runner.output / "logs/video-original-pytest-test.log").read_text()


def test_unavailable_daemon_starts_no_resources(tmp_path):
    runner, commands = fake_runner(tmp_path, daemon_unavailable=True)
    result = runner.collect()
    assert result["status"] == "partial"
    assert result["verification_status"] == "unavailable"
    assert "unavailable" in result["error"]
    assert not any("build" in command or "down" in command for command in commands)


def test_cleanup_retains_volume_with_wrong_owner(tmp_path):
    runner, commands = fake_runner(tmp_path, volume_owner="some-other-project")
    result = runner.collect()
    assert result["status"] == "partial"
    assert result["cleanup_errors"]
    assert not any(command[:3] == ["docker", "volume", "rm"] for command in commands)
