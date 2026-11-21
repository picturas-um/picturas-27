"""Execute shared, revision-independent pytest contracts in selected Docker images."""

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .docker import DockerError, DockerRunner, discover_suites, validate_compose
from .git import resolve_commit
from .results import write_json


CONTRACT_ROOT = Path(__file__).with_name("contracts")
SPECS = {
    "VF-01": {"test": "vf01", "level": "component", "inputs": ["sample_6s.mov"],
              "assertions": ["brightness before binarization matches decoded-frame oracle",
                             "output differs from reverse order", "input unchanged"],
              "tolerances": {"expected_frame_mae_lt": 20, "reverse_margin_gt": 10}},
    "VF-02": {"test": "vf02", "level": "component", "inputs": ["sample_10s_720p.mp4"],
              "assertions": ["trim(1,4) then speed(2) produces 1.5-second video", "audio present"],
              "tolerances": {"duration_seconds_abs": 0.20}},
    "VF-03": {"test": "vf03", "level": "component", "inputs": ["sample_10s_720p.mp4"],
              "assertions": ["MP4/H.264 and AAC audio", "audio and video ends align"],
              "tolerances": {"stream_end_seconds_max": 0.25}},
    "VF-04": {"test": "vf04", "level": "component", "inputs": [],
              "assertions": ["generated flash and beep remain at 0.25 seconds after trim and 2x speed",
                             "audio and visual markers remain within 0.12 seconds"],
              "tolerances": {"marker_expected_seconds_abs": 0.12, "marker_alignment_seconds_max": 0.12,
                             "duration_seconds_abs": 0.20}},
    "VF-05": {"test": "vf05", "level": "component", "inputs": ["sample_6s.mov"],
              "assertions": ["preview is three seconds of output", "source unchanged"],
              "tolerances": {"duration_seconds_abs": 0.20}},
    "VF-06": {"test": "vf06", "level": "component", "inputs": ["sample_6s.mov"],
              "assertions": ["four distinct PNG and JPEG frames at expected times and dimensions",
                             "preview contact sheet is PNG with six samples"],
              "tolerances": {"sample_time_seconds_abs": 0.08}},
    "VF-07": {"test": "vf07", "level": "pipeline", "inputs": ["sample_6s.mov"],
              "assertions": ["native projects route is used", "trim, brightness and resize precede extraction",
                             "two 80x60 frames come from the edited two-second timeline",
                             "extracted frames visibly reflect brightness"],
              "tolerances": {"duration_seconds_abs": 0.20, "sample_time_seconds_abs": 0.08}},
    "VF-09": {"test": "vf09 and not vf09_extraction", "level": "component",
              "inputs": ["corrupted.mp4", "sample_6s.mov"],
              "assertions": ["corrupted input raises InvalidVideo", "invalid trim and speed are rejected",
                             "no partial output"],
              "tolerances": {}},
    "VF-09X": {"test": "vf09_extraction", "level": "component", "inputs": ["sample_6s.mov"],
               "assertions": ["non-terminal extraction raises InvalidExtraction", "no partial output"],
               "tolerances": {}},
    "VF-08": {"test": "vf08", "level": "component", "inputs": ["sample_6s.mov"],
              "assertions": ["deterministic speech renders visible captions", "audio and video remain valid"],
              "tolerances": {"duration_seconds_abs": 0.20, "caption_region_mae_gt": 3},
              "recognizer": "deterministic-stub-v1"},
    "VF-10": {"test": "vf10", "level": "component", "inputs": ["sample_6s.mov"],
              "assertions": ["native worker reply correlates with request and has valid video output",
                             "progress reaches 100 without decreasing", "message is acknowledged"],
              "tolerances": {}},
    "VF-11": {"test": "vf11_prepare_worker_manifest", "level": "integration",
              "inputs": ["sample_6s.mov"],
              "assertions": ["native projects route selects the frame worker",
                             "worker reply contains three frame records",
                             "projects persistence helper creates distinct image results linked to source video"],
              "tolerances": {}},
}

MIXED_PIPELINE = [
    {"procedure": "trim", "params": {"start": 1, "end": 3}},
    {"procedure": "brightness", "params": {"brightness": 0.3}},
    {"procedure": "resize", "params": {"width": 80, "height": 60}},
    {"procedure": "extract_frames", "params": {"count": 2, "format": "png"}},
]
FRAME_PIPELINE = [{"procedure": "extract_frames", "params": {"count": 3, "format": "png"}}]

NODE_ROUTE = (
    "const fs=require('fs'),v=require('/app/utils/video');"
    "const tools=JSON.parse(process.argv[1]);"
    "const project={tools:tools.map((t,i)=>({...t,position:i}))};"
    "const pipeline=v.videoPipeline(project,'evaluation-video');"
    "let tool;"
    "if(process.argv[2]==='baseline'){"
    "const src=fs.readFileSync('/app/routes/projects.js','utf8');"
    "if(!src.includes('tool_name = \"video\";'))throw Error('Baseline route changed');"
    "tool='video';"
    "}else{tool=v.resolveVideoWorkerTool(pipeline)}"
    "console.log(JSON.stringify({pipeline,tool}));"
)

ATTEST_MOUNTS = (
    "import hashlib,json,sys;"
    "digest=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest();"
    "print(json.dumps({p:digest(p) for p in sys.argv[1:]}))"
)

NODE_PERSIST = (
    "const fs=require('fs');"
    "const {persistFrameResults}=require('/app/utils/frameResults');"
    "const reply=JSON.parse(fs.readFileSync('/evidence/vf11-reply.json','utf8'));"
    "const created=[],uploaded=[];"
    "const storage={"
    "upload:async(file,name)=>{const key='key-'+(uploaded.length+1);uploaded.push({file,name,key});return key},"
    "create:async(record)=>{const value={...record,_id:'result-'+(created.length+1)};created.push(value);return value},"
    "removeResult:async()=>{},removeImage:async()=>{}};"
    "const process={new_img_uri:'/evidence/vf11.mp4',img_id:'m4-video',"
    "project_id:'m4-project',user_id:'m4-user',token:1};"
    "(async()=>{try{await persistFrameResults(reply.output,process,storage,'/');"
    "fs.writeFileSync('/evidence/vf11-persisted.json',JSON.stringify({status:'success',created,uploaded}));}"
    "catch(error){fs.writeFileSync('/evidence/vf11-persisted.json',"
    "JSON.stringify({status:'error',message:String(error),created,uploaded}));}})();"
)

PYTEST_COMMAND = (
    "set -eu; python -m pip install --disable-pip-version-check --quiet pytest==9.2.0; "
    "python --version; python -m pytest --version; ffmpeg -version | head -n 1; "
    "ffprobe -version | head -n 1; echo EVALUATION_TEST_START; "
    "python -m pytest -q /contracts/test_contracts.py -k \"$1\" "
    "--junitxml=/evidence/\"$2\""
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def architecture_for(source: Path) -> str:
    original = (source / "Tools/video/video_processor.py").is_file()
    refactored = (source / "Tools/video_effects/effects.py").is_file() and (
        source / "Tools/video_frames/frame_extraction.py").is_file()
    if original == refactored:
        raise DockerError("Cannot unambiguously identify a supported video architecture")
    return "baseline" if original else "refactored"


def service_for(architecture: str, contract_id: str, route: str | None = None) -> str:
    if architecture == "baseline":
        if route is not None and route != "video":
            raise DockerError(f"Unexpected baseline route: {route}")
        return "video_tool"
    if contract_id in {"VF-06", "VF-07", "VF-09X", "VF-11"}:
        if contract_id in {"VF-07", "VF-11"}:
            names = {"video_frames": "video_frames_tool", "video_effects": "video_effects_tool",
                     "video_subtitles": "video_subtitles_tool"}
            if route not in names:
                raise DockerError(f"Unknown selected video service: {route}")
            return names[route]
        return "video_frames_tool"
    if contract_id == "VF-08":
        return "video_subtitles_tool"
    return "video_effects_tool"


def junit_status(path: Path) -> tuple[str, dict]:
    if not path.is_file():
        return "infrastructure_error", {"error": "pytest produced no JUnit report"}
    try:
        root = ET.parse(path).getroot()
        cases = root.findall(".//testcase")
    except ET.ParseError as error:
        return "infrastructure_error", {"error": f"Invalid JUnit report: {error}"}
    if not cases:
        return "infrastructure_error", {"error": "pytest collected no contract tests"}
    details = {"tests": len(cases), "failures": 0, "errors": 0, "skipped": 0}
    for case in cases:
        details["failures"] += case.find("failure") is not None
        details["errors"] += case.find("error") is not None
        details["skipped"] += case.find("skipped") is not None
    if details["errors"]:
        return "infrastructure_error", details
    if details["failures"]:
        return "failed", details
    if details["skipped"]:
        return "unavailable", details
    return "passed", details


def _mounts(source: Path, evidence: Path) -> list[str]:
    return ["-v", f"{CONTRACT_ROOT.resolve()}:/contracts:ro",
            "-v", f"{(source / 'samples/video').resolve()}:/inputs:ro",
            "-v", f"{evidence.resolve()}:/evidence:rw"]


def _mounted_hashes(source: Path, contract_ids: list[str]) -> dict[str, str]:
    manifest = json.loads((CONTRACT_ROOT / "cases.json").read_text())
    names = sorted({name for contract_id in contract_ids for name in SPECS[contract_id]["inputs"]})
    expected = {f"/contracts/{path.name}": sha(path) for path in CONTRACT_ROOT.iterdir()
                if path.suffix == ".py" or path.name == "cases.json"}
    for name in names:
        path = source / "samples/video" / name
        if not path.is_file() or sha(path) != manifest["inputs"][name]:
            raise DockerError(f"Input fixture is absent or differs from the fixed manifest: {name}")
        expected[f"/inputs/{name}"] = manifest["inputs"][name]
    return expected


class ContractRunner:
    def __init__(self, source: Path, output: Path, run_id: str, timeout: int = 3600,
                 invoke=None, contract_ids: list[str] | None = None, source_head: str | None = None,
                 snapshot_sha256: str | None = None):
        self.source = source.resolve()
        self.output = output
        self.contract_ids = contract_ids or list(SPECS)
        self.source_head = source_head
        self.snapshot_sha256 = snapshot_sha256
        if not self.contract_ids or any(item not in SPECS for item in self.contract_ids):
            raise ValueError("Unknown or empty contract selection")
        self.docker = DockerRunner(self.source, output, run_id, timeout, invoke=invoke)

    def _route(self, architecture: str, pipeline: list[dict], label: str) -> dict:
        command = self.docker._compose("run", "-T", "--no-deps", "--rm", "--entrypoint", "node",
                                       "projects", "-e", NODE_ROUTE, json.dumps(pipeline), architecture)
        result = self.docker.call(command, label + "-projects-route", timeout=120)
        if result.returncode:
            raise DockerError("Native projects routing command failed")
        try:
            route = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise DockerError("Native projects routing output is invalid") from error
        if route.get("pipeline") != pipeline:
            raise DockerError("Native projects pipeline differs from the requested contract")
        return route

    def _attest_mounts(self, service: str, expected: dict[str, str]) -> None:
        paths = list(expected)
        command = self.docker._compose("run", "-T", "--no-deps", "--rm",
                                       *_mounts(self.source, self.output), "--entrypoint", "python",
                                       service, "-c", ATTEST_MOUNTS, *paths)
        result = self.docker.call(command, "attest-mounts-" + service, timeout=120)
        if result.returncode:
            raise DockerError("External contract or fixture attestation failed")
        try:
            actual = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise DockerError("External attestation output is invalid") from error
        if actual != expected:
            raise DockerError("Mounted contracts or fixtures differ from host hashes")

    def collect(self) -> dict:
        self.output.mkdir(parents=True, exist_ok=True)
        architecture = architecture_for(self.source)
        expected_mounts = _mounted_hashes(self.source, self.contract_ids)
        suite_files = {path: value for path, value in expected_mounts.items() if path.startswith("/contracts/")}
        suite_hash = hashlib.sha256(json.dumps(suite_files, sort_keys=True).encode()).hexdigest()
        summary = {"status": "partial", "verification_status": "unavailable",
                   "project": self.docker.project,
                   "source_head": None if self.snapshot_sha256 else (
                       self.source_head or resolve_commit(self.source, "HEAD")),
                   "source_base_commit": self.source_head if self.snapshot_sha256 else None,
                   "source_snapshot_sha256": self.snapshot_sha256,
                   "architecture": architecture, "suite_sha256": suite_hash,
                   "adapter_sha256": sha(CONTRACT_ROOT / "adapters.py"),
                   "mounted_hashes": expected_mounts, "contracts": [], "commands": self.docker.commands,
                   "contexts": {}, "image_ids": {}, "docker_versions": {}, "service_errors": {},
                   "route": None, "cleanup_errors": []}
        write_json(self.output / "summary.json", summary)
        volumes: list[str] = []
        attempted: list[str] = []
        resources_started = False
        try:
            for label, command in (("docker", ["docker", "--version"]),
                                   ("compose", ["docker", "compose", "version"]),
                                   ("daemon", ["docker", "info", "--format", "{{.ServerVersion}}"] )):
                result = self.docker.call(command, "version-" + label, timeout=30)
                if result.returncode:
                    raise DockerError(f"Docker {label} is unavailable")
                summary["docker_versions"][label] = result.stdout.strip()
            self.docker._check_project_unused()
            config_result = self.docker.call(self.docker._compose("config", "--format", "json"),
                                             "compose-config", timeout=60, redact_stdout=True)
            if config_result.returncode:
                raise DockerError("Compose configuration failed")
            config = json.loads(config_result.stdout)
            selected = {"projects", "video_tool"} if architecture == "baseline" else {
                "projects", "video_effects_tool", "video_frames_tool"}
            if architecture == "refactored" and "VF-08" in self.contract_ids:
                selected.add("video_subtitles_tool")
            summary["contexts"] = validate_compose(config, self.source, self.docker.project, selected)
            volumes = [item["name"] for item in config.get("volumes", {}).values()]
            suite_by_service = {item["service"]: item for item in discover_suites(self.source)}
            for service in sorted(selected):
                try:
                    resources_started = True
                    attempted.append(service)
                    build = self.docker.call(self.docker._compose("build", service), "build-" + service)
                    if build.returncode:
                        raise DockerError(f"Image build failed for {service}")
                    summary["image_ids"][service] = self.docker._image(service)
                    self.docker._attest(suite_by_service[service])
                    if service != "projects":
                        self._attest_mounts(service, expected_mounts)
                except (DockerError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
                    summary["service_errors"][service] = str(error)
                finally:
                    write_json(self.output / "summary.json", summary)
            if "VF-07" in self.contract_ids:
                if "projects" in summary["service_errors"]:
                    summary["route_error"] = summary["service_errors"]["projects"]
                else:
                    try:
                        summary["route"] = self._route(architecture, MIXED_PIPELINE, "vf07")
                    except (DockerError, OSError, subprocess.TimeoutExpired, ValueError) as error:
                        summary["route_error"] = str(error)
            if "VF-11" in self.contract_ids:
                if "projects" in summary["service_errors"]:
                    summary["route_vf11_error"] = summary["service_errors"]["projects"]
                else:
                    try:
                        summary["route_vf11"] = self._route(architecture, FRAME_PIPELINE, "vf11")
                    except (DockerError, OSError, subprocess.TimeoutExpired, ValueError) as error:
                        summary["route_vf11_error"] = str(error)
            write_json(self.output / "summary.json", summary)
            for contract_id in self.contract_ids:
                spec = SPECS[contract_id]
                item = {"id": contract_id, **spec, "status": "infrastructure_error",
                        "input_hashes": {name: expected_mounts[f"/inputs/{name}"] for name in spec["inputs"]},
                        "adapter": architecture, "adapter_sha256": summary["adapter_sha256"],
                        "suite_sha256": suite_hash}
                summary["contracts"].append(item)
                evidence = self.output / contract_id.lower()
                evidence.mkdir(parents=True, exist_ok=True)
                try:
                    if contract_id == "VF-07" and summary["route"] is None:
                        raise DockerError(summary.get("route_error", "Native projects route is unavailable"))
                    if contract_id == "VF-11" and "route_vf11" not in summary:
                        raise DockerError(summary.get("route_vf11_error", "Native projects route is unavailable"))
                    route = (summary["route"]["tool"] if contract_id == "VF-07" else
                             summary["route_vf11"]["tool"] if contract_id == "VF-11" else None)
                    service = service_for(architecture, contract_id, route)
                    item["service"] = service
                    if service in summary["service_errors"]:
                        raise DockerError(summary["service_errors"][service])
                    item["image_id"] = summary["image_ids"].get(service)
                    command = self.docker._compose(
                        "run", "-T", "--no-deps", "--rm", *_mounts(self.source, evidence),
                        "-e", f"EVAL_ARCHITECTURE={architecture}", "-e", f"EVAL_SERVICE={service}",
                        "--entrypoint", "sh", service, "-c", PYTEST_COMMAND, "contract", spec["test"],
                        "junit-worker.xml" if contract_id == "VF-11" else "junit.xml")
                    result = self.docker.call(command, "test-" + contract_id.lower())
                    item["duration_seconds"] = self.docker.commands[-1]["duration_seconds"]
                    item["log"] = f"logs/test-{contract_id.lower()}.log"
                    item["junit"] = f"{contract_id.lower()}/junit-worker.xml" if contract_id == "VF-11" else f"{contract_id.lower()}/junit.xml"
                    if "EVALUATION_TEST_START" not in result.stdout:
                        raise DockerError("Contract test runner did not start")
                    status, details = junit_status(evidence / ("junit-worker.xml" if contract_id == "VF-11" else "junit.xml"))
                    item["status"], item["junit_result"] = status, details
                    if contract_id == "VF-04" and (evidence / "vf04.json").is_file():
                        generated = json.loads((evidence / "vf04.json").read_text())
                        item["input_hashes"]["generated_marker.mp4"] = generated["generated_input_sha256"]
                    if result.returncode and status == "passed":
                        raise DockerError("pytest failed after reporting passed tests")
                    if contract_id == "VF-11" and status == "passed":
                        persist = self.docker.call(
                            self.docker._compose("run", "-T", "--no-deps", "--rm",
                                                 "-v", f"{evidence.resolve()}:/evidence:rw",
                                                 "--entrypoint", "node", "projects", "-e", NODE_PERSIST),
                            "vf11-projects-persist", timeout=120)
                        item["persistence_log"] = "logs/vf11-projects-persist.log"
                        item["integration_driver_sha256"] = hashlib.sha256(NODE_PERSIST.encode()).hexdigest()
                        if persist.returncode:
                            raise DockerError("Projects persistence helper could not run")
                        verify = self.docker.call(
                            self.docker._compose("run", "-T", "--no-deps", "--rm",
                                                 *_mounts(self.source, evidence),
                                                 "-e", f"EVAL_ARCHITECTURE={architecture}",
                                                 "-e", f"EVAL_SERVICE={service}",
                                                 "--entrypoint", "sh", service, "-c", PYTEST_COMMAND,
                                                 "contract", "vf11_verify_persisted_results", "junit.xml"),
                            "test-vf11-verify")
                        item["verification_log"] = "logs/test-vf11-verify.log"
                        if "EVALUATION_TEST_START" not in verify.stdout:
                            raise DockerError("Integration verification runner did not start")
                        final_status, final_details = junit_status(evidence / "junit.xml")
                        item["verification_junit"] = "vf-11/junit.xml"
                        item["verification_junit_result"] = final_details
                        item["status"] = final_status
                        if verify.returncode and final_status == "passed":
                            raise DockerError("Integration verification process failed")
                except (DockerError, OSError, subprocess.TimeoutExpired, ValueError) as error:
                    item["status"] = "infrastructure_error"
                    item["error"] = str(error)
                finally:
                    write_json(self.output / "summary.json", summary)
            states = [item["status"] for item in summary["contracts"]]
            summary["verification_status"] = "failed" if "failed" in states else (
                "passed" if all(state == "passed" for state in states) else "unavailable")
            summary["status"] = "complete" if all(state in {"passed", "failed"} for state in states) else "partial"
        except (DockerError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
            summary["error"] = str(error)
        finally:
            if resources_started:
                summary["cleanup_errors"] = self.docker._cleanup(volumes, attempted)
            if summary["cleanup_errors"]:
                summary["status"] = "partial"
            write_json(self.output / "summary.json", summary)
        return summary


def collect_contracts(source: Path, output: Path, run_id: str, timeout: int = 3600,
                      contract_ids: list[str] | None = None, source_head: str | None = None,
                      snapshot_sha256: str | None = None) -> dict:
    return ContractRunner(source, output, run_id, timeout, contract_ids=contract_ids,
                          source_head=source_head, snapshot_sha256=snapshot_sha256).collect()
