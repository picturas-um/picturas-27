import os
import subprocess
import sys
from pathlib import Path

import pytest

from fase2.evaluation.git import GitError, TemporaryWorktree, resolve_commit
from fase2.evaluation.static import run_command


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def revisions(tmp_path):
    repo = tmp_path / "repository"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "evaluation@example.test")
    git(repo, "config", "user.name", "Evaluation Test")
    source = repo / "candidate.py"
    source.write_text("VALUE = 'first'\n")
    git(repo, "add", "candidate.py")
    git(repo, "commit", "-qm", "first")
    first = git(repo, "rev-parse", "HEAD")
    source.write_text("VALUE = 'second'\n")
    git(repo, "commit", "-qam", "second")
    second = git(repo, "rev-parse", "HEAD")
    return repo, first, second


def test_resolves_full_commits_and_rejects_invalid_references(revisions):
    repo, first, second = revisions
    assert resolve_commit(repo, first[:8]) == first
    assert resolve_commit(repo, "HEAD") == second
    for revision in ("missing-branch", "--help", ""):
        with pytest.raises(GitError):
            resolve_commit(repo, revision)


def test_executes_the_selected_commit_without_importing_the_current_tree(revisions, tmp_path, monkeypatch):
    repo, first, second = revisions
    # A deliberately wrong PYTHONPATH must not override the selected worktree.
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "candidate.py").write_text("VALUE = 'foreign'\n")
    monkeypatch.setenv("PYTHONPATH", str(foreign))
    observed = []
    for commit in (first, second):
        with TemporaryWorktree(repo, commit) as source:
            assert git(source, "rev-parse", "HEAD") == commit
            command = [sys.executable, "-B", "-c",
                       "import candidate; print(candidate.VALUE); print(candidate.__file__)"]
            result = run_command(command, source, tmp_path / f"{commit}.log", [])
            assert result.returncode == 0
            value, location = result.stdout.strip().splitlines()
            assert Path(location).resolve() == source / "candidate.py"
            observed.append(value)
    assert observed == ["first", "second"]
    assert git(repo, "rev-parse", "HEAD") == second
    assert git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_cleanup_after_failure_preserves_preexisting_worktree(revisions, tmp_path):
    repo, first, _ = revisions
    existing = tmp_path / "existing"
    git(repo, "worktree", "add", "--detach", str(existing), first)
    with pytest.raises(RuntimeError, match="injected"):
        with TemporaryWorktree(repo, first) as source:
            assert source.is_dir()
            raise RuntimeError("injected")
    assert existing.is_dir()
    assert git(existing, "rev-parse", "HEAD") == first
    assert git(repo, "worktree", "list", "--porcelain").count("worktree ") == 2


def test_command_failures_are_logged(revisions, tmp_path):
    repo, _, _ = revisions
    commands = []
    result = run_command([sys.executable, "-c", "raise SystemExit(7)"], repo,
                         tmp_path / "failure.log", commands)
    assert result.returncode == 7
    assert commands[0]["exit_code"] == 7
    with pytest.raises(FileNotFoundError):
        run_command(["missing-picturas-evaluation-tool"], repo,
                    tmp_path / "missing.log", commands)
    assert commands[-1]["exit_code"] is None
    with pytest.raises(subprocess.TimeoutExpired):
        run_command([sys.executable, "-c", "import time; time.sleep(2)"], repo,
                    tmp_path / "timeout.log", commands, timeout=0.01)
    assert "error" in commands[-1]
