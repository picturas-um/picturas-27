import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from fase2.evaluation import contract_runner
from fase2.evaluation.contract_runner import (
    ContractRunner, architecture_for, junit_status, service_for,
)
from fase2.evaluation.contracts import adapters
from fase2.evaluation.docker import DockerError


def test_adapter_only_forwards_pipeline_and_error(monkeypatch):
    calls = []

    def process_video(*args, **kwargs):
        calls.append((args, kwargs))
        if args[2] == ["fail"]:
            raise RuntimeError("application error")
        return {"output_type": "video"}

    monkeypatch.setattr(adapters.importlib, "import_module",
                        lambda name: SimpleNamespace(__file__="/app/" + name + ".py",
                                                     process_video=process_video))
    pipeline = [{"procedure": "brightness", "params": {"brightness": 0.3}}]
    for architecture, service in (("baseline", "video_tool"),
                                  ("refactored", "video_effects_tool"),
                                  ("refactored", "video_frames_tool")):
        adapter = adapters.ProcessorAdapter(architecture, service)
        assert adapter.execute(Path("/inputs/a.mov"), Path("/evidence/o.mp4"), pipeline) == {
            "output_type": "video"}
        assert calls[-1][0][2] is pipeline
        with pytest.raises(RuntimeError, match="application error"):
            adapter.execute(Path("/inputs/a.mov"), Path("/evidence/o.mp4"), ["fail"])


def test_adapter_rejects_module_outside_selected_image(monkeypatch):
    monkeypatch.setattr(adapters.importlib, "import_module",
                        lambda name: SimpleNamespace(__file__="/other/effects.py"))
    with pytest.raises(RuntimeError, match="outside the selected image"):
        adapters.ProcessorAdapter("refactored", "video_effects_tool")


def test_worker_adapter_passes_message_to_native_callback(monkeypatch):
    seen = {}

    class Worker:
        def callback(self, channel, method, properties, body):
            seen["request"] = json.loads(body)
            channel.basic_publish("picturas", "project_queue", json.dumps({
                "status": "success", "correlationId": seen["request"]["messageId"]}))
            channel.basic_ack(method.delivery_tag)

    def load(name):
        if name == "video":
            return SimpleNamespace(__file__="/app/video.py", VideoWorker=Worker)
        return SimpleNamespace(__file__="/app/video_processor.py", process_video=lambda *a, **k: {})

    monkeypatch.setattr(adapters.importlib, "import_module", load)
    adapter = adapters.ProcessorAdapter("baseline", "video_tool")
    pipeline = [{"procedure": "brightness", "params": {"brightness": 1.1}}]
    result = adapter.invoke_worker(Path("/inputs/a.mov"), Path("/evidence/o.mp4"), pipeline)
    assert seen["request"]["parameters"]["tools"] == pipeline
    assert seen["request"]["procedure"] == "video"
    assert result["acks"] == [7]
    assert result["messages"][0]["body"]["correlationId"] == "m4-vf10-request"


def test_architecture_and_route_are_explicit(tmp_path):
    with pytest.raises(DockerError):
        architecture_for(tmp_path)
    source = tmp_path / "Tools/video/video_processor.py"
    source.parent.mkdir(parents=True)
    source.touch()
    assert architecture_for(tmp_path) == "baseline"
    assert service_for("baseline", "VF-07", "video") == "video_tool"
    assert service_for("refactored", "VF-07", "video_frames") == "video_frames_tool"
    assert service_for("refactored", "VF-09X") == "video_frames_tool"
    assert service_for("refactored", "VF-08") == "video_subtitles_tool"
    assert service_for("refactored", "VF-11", "video_frames") == "video_frames_tool"
    with pytest.raises(DockerError):
        service_for("refactored", "VF-07", "unknown")


@pytest.mark.parametrize("fragment,expected", [
    ("", "passed"),
    ('<failure message="wrong"/>', "failed"),
    ('<error message="import"/>', "infrastructure_error"),
    ('<skipped message="model unavailable"/>', "unavailable"),
])
def test_junit_classification(tmp_path, fragment, expected):
    path = tmp_path / "junit.xml"
    path.write_text(f'<testsuite><testcase name="vf01">{fragment}</testcase></testsuite>')
    assert junit_status(path)[0] == expected


def test_missing_junit_is_infrastructure_error(tmp_path):
    assert junit_status(tmp_path / "missing.xml")[0] == "infrastructure_error"


def test_contract_runner_preserves_failure_and_continues(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "results"
    (source / "Tools/video").mkdir(parents=True)
    (source / "Tools/video/video_processor.py").touch()
    hashes = json.loads((contract_runner.CONTRACT_ROOT / "cases.json").read_text())["inputs"]
    monkeypatch.setattr(contract_runner, "_mounted_hashes", lambda *args: {
        f"/inputs/{name}": value for name, value in hashes.items()})
    monkeypatch.setattr(contract_runner, "resolve_commit", lambda *args: "a" * 40)
    monkeypatch.setattr(contract_runner, "validate_compose", lambda *args: {"projects": {}, "video_tool": {}})
    monkeypatch.setattr(contract_runner, "discover_suites", lambda *args: [
        {"service": "projects"}, {"service": "video_tool"}])

    class FakeDocker:
        def __init__(self, source, output, run_id, timeout, invoke=None):
            self.project = "picturas-eval-test"
            self.commands = []

        def _compose(self, *args):
            return ["docker", "compose", *args]

        def call(self, command, label, **kwargs):
            self.commands.append({"argv": command, "duration_seconds": 0.1})
            if label == "compose-config":
                return subprocess.CompletedProcess(command, 0, json.dumps({"volumes": {}}), "")
            if label.startswith("test-"):
                contract_id = label[5:].upper()
                evidence = output / contract_id.lower()
                evidence.mkdir(parents=True, exist_ok=True)
                failure = '<failure message="regression"/>' if contract_id == "VF-01" else ""
                (evidence / "junit.xml").write_text(
                    f'<testsuite><testcase name="{contract_id}">{failure}</testcase></testsuite>')
                return subprocess.CompletedProcess(command, 1 if failure else 0,
                                                   "EVALUATION_TEST_START\n", "")
            return subprocess.CompletedProcess(command, 0, "ok\n", "")

        def _check_project_unused(self):
            pass

        def _image(self, service):
            return "sha256:" + "a" * 64

        def _attest(self, suite):
            pass

        def _cleanup(self, volumes, attempted):
            assert set(attempted) == {"projects", "video_tool"}
            return []

    monkeypatch.setattr(contract_runner, "DockerRunner", FakeDocker)
    monkeypatch.setattr(ContractRunner, "_attest_mounts", lambda *args: None)
    runner = ContractRunner(source, output, "run", contract_ids=["VF-01", "VF-09"])
    result = runner.collect()
    assert [item["status"] for item in result["contracts"]] == ["failed", "passed"]
    assert result["verification_status"] == "failed"
    assert result["status"] == "complete"
    assert json.loads((output / "summary.json").read_text())["contracts"][0]["status"] == "failed"


def test_vf11_integration_stages_are_orchestrated_without_daemon(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "results"
    (source / "Tools/video").mkdir(parents=True)
    (source / "Tools/video/video_processor.py").touch()
    fixture_hash = json.loads((contract_runner.CONTRACT_ROOT / "cases.json").read_text())[
        "inputs"]["sample_6s.mov"]
    monkeypatch.setattr(contract_runner, "_mounted_hashes",
                        lambda *args: {"/inputs/sample_6s.mov": fixture_hash})
    monkeypatch.setattr(contract_runner, "resolve_commit", lambda *args: "a" * 40)
    monkeypatch.setattr(contract_runner, "validate_compose", lambda *args: {})
    monkeypatch.setattr(contract_runner, "discover_suites", lambda *args: [
        {"service": "projects"}, {"service": "video_tool"}])
    labels = []

    class FakeDocker:
        def __init__(self, source, output, run_id, timeout, invoke=None):
            self.project = "picturas-eval-test"
            self.commands = []

        def _compose(self, *args):
            return ["docker", "compose", *args]

        def call(self, command, label, **kwargs):
            labels.append(label)
            self.commands.append({"argv": command, "duration_seconds": 0.1})
            if label == "compose-config":
                return subprocess.CompletedProcess(command, 0, json.dumps({"volumes": {}}), "")
            if label == "vf11-projects-route":
                return subprocess.CompletedProcess(command, 0, json.dumps({
                    "pipeline": contract_runner.FRAME_PIPELINE, "tool": "video"}), "")
            if label == "test-vf-11":
                evidence = output / "vf-11"
                evidence.mkdir(parents=True, exist_ok=True)
                (evidence / "junit-worker.xml").write_text(
                    '<testsuite><testcase name="worker"/></testsuite>')
                return subprocess.CompletedProcess(command, 0, "EVALUATION_TEST_START\n", "")
            if label == "vf11-projects-persist":
                (output / "vf-11/vf11-persisted.json").write_text('{"status":"success"}')
            if label == "test-vf11-verify":
                (output / "vf-11/junit.xml").write_text(
                    '<testsuite><testcase name="persistence"/></testsuite>')
                return subprocess.CompletedProcess(command, 0, "EVALUATION_TEST_START\n", "")
            return subprocess.CompletedProcess(command, 0, "ok\n", "")

        def _check_project_unused(self):
            pass

        def _image(self, service):
            return "sha256:" + "a" * 64

        def _attest(self, suite):
            pass

        def _cleanup(self, volumes, attempted):
            return []

    monkeypatch.setattr(contract_runner, "DockerRunner", FakeDocker)
    monkeypatch.setattr(ContractRunner, "_attest_mounts", lambda *args: None)
    result = ContractRunner(source, output, "run", contract_ids=["VF-11"]).collect()
    assert result["contracts"][0]["status"] == "passed"
    assert labels.index("vf11-projects-route") < labels.index("test-vf-11")
    assert labels.index("test-vf-11") < labels.index("vf11-projects-persist")
    assert labels.index("vf11-projects-persist") < labels.index("test-vf11-verify")
