"""Run revision-specific application suites in disposable Compose containers."""

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from .results import write_json


PYTEST_COMMAND = (
    "set -eu; python --version; ffmpeg -version | head -n 1; "
    "ffprobe -version | head -n 1; "
    "python -m pip install --disable-pip-version-check --quiet pytest==9.2.0; "
    "python -m pytest --version; python -m pip freeze; "
    "echo EVALUATION_TEST_START; python -m pytest -q tests"
)
NODE_COMMAND = (
    "set -eu; node --version; npm --version; "
    "echo EVALUATION_TEST_START; node --test \"$@\""
)
PYTHON_ATTEST = (
    "import hashlib,json,subprocess,sys; "
    "digest=lambda path:hashlib.sha256(open(path,'rb').read()).hexdigest(); "
    "version=lambda name:subprocess.run([name,'-version'],capture_output=True,text=True).stdout.splitlines()[0]; "
    "print(json.dumps({'hashes':{path:digest(path) for path in sys.argv[1:]},"
    "'python':sys.version.split()[0],'ffmpeg':version('ffmpeg'),'ffprobe':version('ffprobe')}))"
)
NODE_ATTEST = (
    "const fs=require('fs'),c=require('crypto'),cp=require('child_process');"
    "const hash=p=>c.createHash('sha256').update(fs.readFileSync(p)).digest('hex');"
    "const v=p=>cp.execFileSync(p,['-version'],{encoding:'utf8'}).split(String.fromCharCode(10))[0];"
    "console.log(JSON.stringify({hashes:Object.fromEntries(process.argv.slice(1).map(p=>[p,hash(p)])),"
    "node:process.version,npm:cp.execFileSync('npm',['--version'],{encoding:'utf8'}).trim(),"
    "ffmpeg:v('ffmpeg'),ffprobe:v('ffprobe')}))"
)


class DockerError(RuntimeError):
    """Docker infrastructure or isolation validation failed."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_test_output(kind: str, output: str) -> dict:
    """Keep test counts local to a suite; they are not cross-revision evidence."""
    if kind == "python-pytest":
        matches = re.findall(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed)\b", output)
        counts = {name: int(value) for value, name in matches}
        duration = re.search(r"\bin (\d+(?:\.\d+)?)s\b", output)
        return {"counts": counts, "reported_duration_seconds": float(duration.group(1)) if duration else None}
    counts = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-2] in {"tests", "pass", "fail", "skipped", "cancelled"} and parts[-1].isdigit():
            counts[parts[-2]] = int(parts[-1])
    duration = re.search(r"\bduration_ms\s+(\d+(?:\.\d+)?)", output)
    return {"counts": counts, "reported_duration_seconds": float(duration.group(1)) / 1000 if duration else None}


def discover_suites(source: Path) -> list[dict]:
    """Select only suites and services present in the chosen worktree."""
    worker_roots = [
        ("video-original-pytest", "video_tool", "Tools/video"),
        ("video-effects-pytest", "video_effects_tool", "Tools/video_effects"),
        ("video-subtitles-pytest", "video_subtitles_tool", "Tools/video_subtitles"),
        ("video-frames-pytest", "video_frames_tool", "Tools/video_frames"),
    ]
    suites = []
    for suite_id, service, root_name in worker_roots:
        root = source / root_name
        tests = sorted((root / "tests").glob("test_*.py"))
        if not tests:
            continue
        identity = sorted((root / "tests").glob("*.py"))
        production = sorted(path for path in root.glob("*.py") if path.name != "__init__.py")
        utils = sorted((source / "Tools/utils").glob("*.py"))
        code = {f"/app/{path.name}": path for path in production}
        code.update({f"/app/utils/{path.name}": path for path in utils})
        code.update({f"/app/tests/{path.name}": path for path in identity})
        suites.append({
            "id": suite_id, "kind": "python-pytest", "service": service,
            "test_root": root / "tests", "test_files": identity, "code_files": code,
        })
    node_root = source / "projects"
    node_tests = sorted((node_root / "tests").glob("*.test.js"))
    if node_tests:
        code = {f"/app/tests/{path.name}": path for path in node_tests}
        for name in ("utils/video.js", "utils/project_msg.js", "utils/frameResults.js",
                     "utils/processBatch.js", "routes/projects.js"):
            path = node_root / name
            if path.is_file():
                code[f"/app/{name}"] = path
        suites.append({
            "id": "projects-node-test", "kind": "node-test", "service": "projects",
            "test_root": node_root / "tests", "test_files": node_tests, "code_files": code,
        })
    if not suites:
        raise DockerError("No existing Python or Node video test suites found")
    return suites


def validate_compose(config: dict, source: Path, project: str, services: set[str]) -> dict:
    """Reject Compose features that could address resources outside this run."""
    if config.get("name") != project:
        raise DockerError("Compose project name differs from the unique evaluation name")
    for kind in ("volumes", "networks"):
        for item in config.get(kind, {}).values():
            if item.get("external") or not item.get("name", "").startswith(project + "_"):
                raise DockerError(f"Compose {kind} include an external or fixed-name resource")
    for name, service in config.get("services", {}).items():
        if service.get("container_name"):
            raise DockerError(f"Service {name} fixes a container_name")
    details = {}
    for name in services:
        service = config.get("services", {}).get(name)
        if service is None:
            raise DockerError(f"Required Compose service {name} is absent")
        if service.get("image"):
            raise DockerError(f"Service {name} has a non-isolated image tag")
        for key in ("privileged", "network_mode", "pid", "ipc", "devices", "volumes_from", "extends"):
            if service.get(key):
                raise DockerError(f"Service {name} uses unsupported isolation feature {key}")
        build = service.get("build") or {}
        context = Path(build.get("context", "")).resolve()
        dockerfile = (context / build.get("dockerfile", "Dockerfile")).resolve()
        if source.resolve() not in context.parents or not dockerfile.is_file() or context not in dockerfile.parents:
            raise DockerError(f"Build context or Dockerfile for {name} is outside the selected worktree")
        if build.get("additional_contexts"):
            raise DockerError(f"Service {name} uses additional build contexts")
        for mount in service.get("volumes", []):
            if mount.get("type") != "volume" or mount.get("source") not in config.get("volumes", {}):
                raise DockerError(f"Service {name} uses an external or bind-mounted volume")
        details[name] = {"context": str(context), "dockerfile": str(dockerfile),
                         "dockerfile_sha256": _sha(dockerfile),
                         "named_volumes": [item["source"] for item in service.get("volumes", [])]}
    return details


class DockerRunner:
    def __init__(self, source: Path, output: Path, run_id: str, timeout: int = 3600,
                 invoke=None):
        self.source = source.resolve()
        self.output = output
        self.run_id = run_id
        self.project = "picturas-eval-" + uuid.uuid4().hex[:12]
        self.timeout = timeout
        self.invoke = invoke or subprocess.run
        self.commands: list[dict] = []
        self.base = ["docker", "compose", "-f", str(self.source / "docker-compose.yaml"),
                     "--project-directory", str(self.source), "-p", self.project]
        self.environment = os.environ.copy()
        for key in list(self.environment):
            if key.startswith("COMPOSE_") or key == "PYTHONPATH":
                self.environment.pop(key)

    def call(self, command: list[str], label: str, timeout: int | None = None,
             redact_stdout: bool = False):
        started = time.perf_counter()
        log = self.output / "logs" / f"{label}.log"
        record = {"argv": command, "cwd": str(self.source), "log": str(log)}
        try:
            result = self.invoke(command, cwd=self.source, env=self.environment,
                                 capture_output=True, text=True, timeout=timeout or self.timeout)
            record.update({"exit_code": result.returncode,
                           "duration_seconds": round(time.perf_counter() - started, 4)})
            log.parent.mkdir(parents=True, exist_ok=True)
            logged_stdout = "[resolved configuration withheld to avoid exposing secrets]\n" if redact_stdout else result.stdout
            log.write_text(logged_stdout + result.stderr, encoding="utf-8")
            return result
        except (OSError, subprocess.TimeoutExpired) as error:
            record.update({"exit_code": None, "error": str(error),
                           "duration_seconds": round(time.perf_counter() - started, 4)})
            log.parent.mkdir(parents=True, exist_ok=True)
            partial = ""
            if isinstance(error, subprocess.TimeoutExpired) and not redact_stdout:
                for stream in (error.stdout, error.stderr):
                    if stream:
                        partial += stream.decode("utf-8", errors="replace") if isinstance(stream, bytes) else stream
            log.write_text(partial + str(error) + "\n", encoding="utf-8")
            raise
        finally:
            self.commands.append(record)

    def _compose(self, *args: str) -> list[str]:
        return [*self.base, *args]

    def _mount(self, suite: dict) -> list[str]:
        root = suite["test_root"].resolve()
        if self.source not in root.parents:
            raise DockerError("Test mount escapes the selected worktree")
        return ["-v", f"{root}:/app/tests:ro"]

    def _attest(self, suite: dict) -> dict:
        files = suite["code_files"]
        entrypoint = "python" if suite["kind"] == "python-pytest" else "node"
        script = PYTHON_ATTEST if entrypoint == "python" else NODE_ATTEST
        flag = "-c" if entrypoint == "python" else "-e"
        command = self._compose("run", "-T", "--no-deps", "--rm", *self._mount(suite),
                                "--entrypoint", entrypoint, suite["service"], flag, script, *files)
        result = self.call(command, suite["id"] + "-attest", timeout=300)
        if result.returncode:
            raise DockerError("Container provenance command failed")
        try:
            actual = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise DockerError("Container provenance output is not JSON") from error
        expected = {name: _sha(path) for name, path in files.items()}
        if actual.get("hashes") != expected:
            raise DockerError("Container source or test file hashes differ from the selected worktree")
        actual["verified_file_count"] = len(expected)
        return actual

    def _test(self, suite: dict):
        if suite["kind"] == "python-pytest":
            command = self._compose("run", "-T", "--no-deps", "--rm", *self._mount(suite),
                                    "--entrypoint", "sh", suite["service"], "-c", PYTEST_COMMAND)
        else:
            names = [f"tests/{path.name}" for path in suite["test_files"] if path.name.endswith(".test.js")]
            command = self._compose("run", "-T", "--no-deps", "--rm", *self._mount(suite),
                                    "--entrypoint", "sh", suite["service"], "-c", NODE_COMMAND,
                                    "evaluation-sh", *names)
        return self.call(command, suite["id"] + "-test")

    def _image(self, service: str) -> str:
        tag = f"{self.project}-{service}:latest"
        result = self.call(["docker", "image", "inspect", tag, "--format", "{{.Id}}"],
                           service + "-image", timeout=60)
        if result.returncode or not re.fullmatch(r"sha256:[0-9a-f]{64}", result.stdout.strip()):
            raise DockerError(f"Cannot identify the newly built image for {service}")
        return result.stdout.strip()

    def _check_project_unused(self) -> None:
        checks = (
            ("container", ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={self.project}"]),
            ("volume", ["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={self.project}"]),
            ("network", ["docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={self.project}"]),
            ("image", ["docker", "image", "ls", "-q", "--filter", f"reference={self.project}-*"]),
        )
        for kind, command in checks:
            result = self.call(command, "preflight-" + kind, timeout=30)
            if result.returncode or result.stdout.strip():
                raise DockerError(f"Evaluation project collides with existing Docker {kind} resources")

    def _cleanup(self, volumes: list[str], attempted_services: list[str]) -> list[str]:
        errors = []
        try:
            result = self.call(self._compose("down", "--remove-orphans"), "cleanup-down", timeout=180)
            if result.returncode:
                errors.append("docker compose down failed")
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(f"docker compose down failed: {error}")
        for name in volumes:
            try:
                inspect = self.call(["docker", "volume", "inspect", name, "--format", "{{json .Labels}}"],
                                    "inspect-volume-" + name, timeout=30)
                if inspect.returncode:
                    continue  # The run did not create this volume.
                labels = json.loads(inspect.stdout)
                if not isinstance(labels, dict) or labels.get("com.docker.compose.project") != self.project:
                    errors.append(f"Volume {name} has an unexpected owner; retained")
                    continue
                removed = self.call(["docker", "volume", "rm", name], "remove-volume-" + name, timeout=30)
                if removed.returncode:
                    errors.append(f"Could not remove owned volume {name}")
            except (OSError, subprocess.TimeoutExpired, ValueError) as error:
                errors.append(f"Volume cleanup failed for {name}: {error}")
        for service in attempted_services:
            tag = f"{self.project}-{service}:latest"
            try:
                inspect = self.call(["docker", "image", "inspect", tag, "--format", "{{.Id}}"],
                                    "inspect-cleanup-image-" + service, timeout=30)
                if inspect.returncode:
                    continue
                removed = self.call(["docker", "image", "rm", tag], "remove-image-" + service, timeout=90)
                if removed.returncode:
                    errors.append(f"Could not remove evaluation image {tag}")
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(f"Image cleanup failed for {tag}: {error}")
        return errors

    def collect(self) -> dict:
        self.output.mkdir(parents=True, exist_ok=True)
        suites = discover_suites(self.source)
        summary = {"project": self.project, "run_id": self.run_id,
                   "status": "partial", "verification_status": "skipped",
                   "suites": [], "commands": self.commands, "docker_versions": {},
                   "contexts": {}, "cleanup_errors": []}
        volumes = []
        attempted_services = []
        resources_started = False
        write_json(self.output / "summary.json", summary)
        try:
            for label, command in (("docker", ["docker", "--version"]),
                                   ("compose", ["docker", "compose", "version"]),
                                   ("daemon", ["docker", "info", "--format", "{{.ServerVersion}}"])):
                result = self.call(command, "version-" + label, timeout=30)
                if result.returncode:
                    raise DockerError(f"Docker {label} is unavailable")
                summary["docker_versions"][label] = result.stdout.strip()
            self._check_project_unused()
            config_result = self.call(self._compose("config", "--format", "json"),
                                      "compose-config", timeout=60, redact_stdout=True)
            if config_result.returncode:
                raise DockerError("Compose configuration failed")
            config = json.loads(config_result.stdout)
            services = {suite["service"] for suite in suites}
            summary["contexts"] = validate_compose(config, self.source, self.project, services)
            volumes = [entry["name"] for entry in config.get("volumes", {}).values()]
            for suite in suites:
                suite_result = {
                    "id": suite["id"], "kind": suite["kind"], "service": suite["service"],
                    "test_files": {str(path.relative_to(self.source)): _sha(path) for path in suite["test_files"]},
                    "status": "infrastructure_error",
                }
                summary["suites"].append(suite_result)
                write_json(self.output / "summary.json", summary)
                try:
                    resources_started = True
                    attempted_services.append(suite["service"])
                    build = self.call(self._compose("build", suite["service"]), suite["id"] + "-build")
                    suite_result["build_duration_seconds"] = self.commands[-1]["duration_seconds"]
                    if build.returncode:
                        raise DockerError("Image build failed")
                    suite_result["image_id"] = self._image(suite["service"])
                    suite_result["provenance"] = self._attest(suite)
                    test = self._test(suite)
                    suite_result["duration_seconds"] = self.commands[-1]["duration_seconds"]
                    suite_result["test_log"] = f"logs/{suite['id']}-test.log"
                    if "EVALUATION_TEST_START" not in test.stdout:
                        raise DockerError("Test runner did not start")
                    suite_result.update(parse_test_output(suite["kind"], test.stdout))
                    suite_result["status"] = "passed" if test.returncode == 0 else "failed"
                except (DockerError, OSError, subprocess.TimeoutExpired, ValueError) as error:
                    suite_result["error"] = str(error)
                finally:
                    write_json(self.output / "summary.json", summary)
            statuses = [suite["status"] for suite in summary["suites"]]
            summary["verification_status"] = "failed" if "failed" in statuses else (
                "passed" if statuses and all(item == "passed" for item in statuses) else "unavailable")
            summary["status"] = "complete" if all(item in {"passed", "failed"} for item in statuses) else "partial"
        except (DockerError, OSError, subprocess.TimeoutExpired, ValueError) as error:
            summary["error"] = str(error)
            summary["verification_status"] = "unavailable"
        finally:
            if resources_started:
                summary["cleanup_errors"] = self._cleanup(volumes, attempted_services)
            if summary["cleanup_errors"]:
                summary["status"] = "partial"
            write_json(self.output / "summary.json", summary)
        return summary


def collect_docker(source: Path, output: Path, run_id: str, timeout: int = 3600) -> dict:
    return DockerRunner(source, output, run_id, timeout).collect()
