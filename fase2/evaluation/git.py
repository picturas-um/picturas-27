"""Resolve local commits and manage detached, temporary Git worktrees."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


class GitError(RuntimeError):
    """A Git operation could not be completed safely."""


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if result.returncode:
        raise GitError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout.strip()


def repository_root(location: Path) -> Path:
    return Path(_git(location, "rev-parse", "--show-toplevel")).resolve()


def resolve_commit(repo: Path, revision: str) -> str:
    if not revision or revision.startswith("-") or "\x00" in revision:
        raise GitError("Invalid Git revision")
    try:
        commit = _git(repo, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")
    except GitError as error:
        raise GitError(f"Revision {revision!r} is not available locally: {error}") from error
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise GitError(f"Git returned an invalid commit hash: {commit!r}")
    return commit


class TemporaryWorktree:
    """Create a worktree from a disposable local bare clone, leaving repo/.git alone."""

    def __init__(self, repo: Path, commit: str):
        self.repo = repo
        self.commit = commit
        self.root = None
        self.bare = None
        self.path = None

    def __enter__(self) -> Path:
        self.root = Path(tempfile.mkdtemp(prefix="picturas-evaluation-"))
        self.bare = self.root / "repository.git"
        self.path = self.root / "source"
        added = False
        try:
            cloned = subprocess.run(
                ["git", "clone", "--bare", "--shared", "--no-hardlinks", str(self.repo), str(self.bare)],
                capture_output=True, text=True,
            )
            if cloned.returncode:
                raise GitError(cloned.stderr.strip() or "Could not create local evaluation repository")
            _git(self.bare, "worktree", "add", "--detach", str(self.path), self.commit)
            added = True
            actual = _git(self.path, "rev-parse", "HEAD")
            if actual != self.commit:
                raise GitError(f"Worktree HEAD mismatch: expected {self.commit}, got {actual}")
        except BaseException as error:
            if added:
                try:
                    _git(self.bare, "worktree", "remove", str(self.path))
                except GitError as cleanup_error:
                    raise GitError(
                        f"Worktree setup failed ({error}); cleanup failed at {self.path}: {cleanup_error}"
                    ) from cleanup_error
            shutil.rmtree(self.root, ignore_errors=True)
            raise
        return self.path

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            _git(self.bare, "worktree", "remove", str(self.path))
            shutil.rmtree(self.root)
        except (GitError, OSError) as error:
            raise GitError(f"Could not safely remove worktree {self.path}: {error}") from error
        return False
