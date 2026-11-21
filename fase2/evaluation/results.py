"""Create non-overwriting result directories and persist JSON evidence."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def default_root() -> Path:
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_home / "picturas-evaluation" / "evaluations"


def create_run(root: Path, role: str, commit: str, run_id: str | None = None) -> tuple[Path, str]:
    if role not in {"baseline", "refactored", "unclassified"}:
        raise ValueError(f"Invalid evaluation role: {role}")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("commit must be a full lowercase Git SHA-1 hash")
    return _create_run(root, (role, commit), run_id)


def create_snapshot_run(root: Path, snapshot_sha256: str, run_id: str | None = None) -> tuple[Path, str]:
    if len(snapshot_sha256) != 64 or any(char not in "0123456789abcdef" for char in snapshot_sha256):
        raise ValueError("snapshot_sha256 must be a full lowercase SHA-256 digest")
    return _create_run(root, ("snapshots", snapshot_sha256), run_id)


def _create_run(root: Path, parts: tuple[str, ...], run_id: str | None) -> tuple[Path, str]:
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    if run_id in {".", ".."} or not run_id or any(char not in "-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for char in run_id):
        raise ValueError("run-id must contain only letters, digits, dots, underscores or hyphens")
    directory = root.expanduser().resolve().joinpath(*parts, run_id)
    directory.mkdir(parents=True, exist_ok=False)
    return directory, run_id


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
