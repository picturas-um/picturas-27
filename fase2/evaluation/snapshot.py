"""Capture a developer checkout without modifying Git history or the checkout."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .git import GitError, resolve_commit


# The framework and its evidence are supplied by the host, never by the source.
EXCLUDED = ("fase2/evaluation", "fase2/tests/evaluation", "fase2/resultados")


def _excluded(name: str, extra: tuple[str, ...]) -> bool:
    return any(name == prefix or name.startswith(prefix + "/") for prefix in EXCLUDED + extra)


class TemporarySnapshot:
    """Copy tracked and non-ignored untracked files into a disposable Gitless tree."""

    def __init__(self, repo: Path, exclude: Path | None = None):
        self.repo = repo.resolve()
        self.exclude = exclude
        self.root: Path | None = None
        self.path: Path | None = None
        self.base_commit: str | None = None
        self.sha256: str | None = None
        self.files: list[dict] = []

    def __enter__(self) -> "TemporarySnapshot":
        self.base_commit = resolve_commit(self.repo, "HEAD")
        extra: tuple[str, ...] = ()
        if self.exclude is not None:
            target = self.exclude.expanduser().resolve()
            if target == self.repo:
                raise GitError("Results root cannot be the source repository")
            if target.is_relative_to(self.repo):
                extra = (target.relative_to(self.repo).as_posix(),)
        listed = subprocess.run(
            ["git", "-C", str(self.repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
        )
        if listed.returncode:
            raise GitError(listed.stderr.decode(errors="replace").strip() or "Could not list checkout files")
        self.root = Path(tempfile.mkdtemp(prefix="picturas-snapshot-"))
        self.path = self.root / "source"
        self.path.mkdir()
        try:
            names = sorted(set(name.decode("utf-8", "surrogateescape") for name in listed.stdout.split(b"\0") if name))
            for name in names:
                if _excluded(name, extra):
                    continue
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
                    raise GitError(f"Unsafe checkout path: {name!r}")
                original = self.repo / relative
                if not original.exists() and not original.is_symlink():
                    continue  # A tracked deletion is absent from the snapshot.
                if original.is_symlink() or not original.is_file():
                    raise GitError(f"Snapshot requires a regular file: {name!r}")
                before = hashlib.sha256(original.read_bytes()).hexdigest()
                target = self.path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
                after = hashlib.sha256(target.read_bytes()).hexdigest()
                if before != after or hashlib.sha256(original.read_bytes()).hexdigest() != before:
                    raise GitError(f"Checkout changed while capturing {name!r}; retry the evaluation")
                self.files.append({"path": name, "sha256": after, "mode": target.stat().st_mode & 0o777})
            payload = {"base_commit": self.base_commit, "files": self.files}
            self.sha256 = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            return self
        except BaseException:
            shutil.rmtree(self.root)
            raise

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if self.root is not None:
            shutil.rmtree(self.root)
        return False
