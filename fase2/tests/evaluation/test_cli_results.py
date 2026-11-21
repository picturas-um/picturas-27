import json
import subprocess

import pytest

from fase2.evaluation.cli import main
from fase2.evaluation.index import BASELINE, INITIAL_REFACTORED
from fase2.evaluation.results import create_run, write_json


def test_result_directories_never_overwrite(tmp_path):
    path, _ = create_run(tmp_path, "refactored", "a" * 40, "run-1")
    assert path == tmp_path / "refactored" / ("a" * 40) / "run-1"
    write_json(path / "metadata.json", {"status": "first"})
    with pytest.raises(FileExistsError):
        create_run(tmp_path, "refactored", "a" * 40, "run-1")
    assert json.loads((path / "metadata.json").read_text()) == {"status": "first"}
    with pytest.raises(ValueError):
        create_run(tmp_path, "refactored", "a" * 40, "../escape")
    with pytest.raises(ValueError):
        create_run(tmp_path, "../escape", "a" * 40, "safe")


@pytest.mark.parametrize("flag", ["--performance", "--maintenance"])
def test_unimplemented_categories_fail_explicitly(flag):
    with pytest.raises(SystemExit) as failure:
        main(["run", "HEAD", flag])
    assert failure.value.code == 2


def test_unavailable_local_commit_returns_preflight_failure(tmp_path):
    assert main(["run", "914476a92b4e4bc51f925ba2c4ef9468988e57c8",
                 "--source-repo", str(tmp_path)]) == 2


def test_run_records_selected_commit_and_cleans_up(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (("init", "-q"), ("config", "user.email", "test@example.test"),
                 ("config", "user.name", "Test")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    (repo / "source.py").write_text("VALUE = 1\n")
    for args in (("add", "source.py"), ("commit", "-qm", "source")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    def collect(source, output, python, jscpd):
        assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == commit
        assert (source / "source.py").read_text() == "VALUE = 1\n"
        return {"status": "complete"}

    monkeypatch.setattr("fase2.evaluation.cli.collect_static", collect)
    assert main(["run", commit, "--source-repo", str(repo),
                 "--results-root", str(tmp_path / "results"), "--run-id", "check"]) == 0
    metadata = json.loads((tmp_path / "results" / "unclassified" / commit / "check" / "metadata.json").read_text())
    assert metadata["role"] == "unclassified"
    assert metadata["worktree_head"] == commit
    assert metadata["collection_status"] == "complete"
    worktrees = subprocess.check_output(["git", "-C", str(repo), "worktree", "list", "--porcelain"], text=True)
    assert worktrees.count("worktree ") == 1


def test_all_runs_only_implemented_categories_and_keeps_failures(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (("init", "-q"), ("config", "user.email", "test@example.test"),
                 ("config", "user.name", "Test")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    (repo / "source.py").write_text("VALUE = 1\n")
    for args in (("add", "source.py"), ("commit", "-qm", "source")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    calls = []

    def static(*args):
        calls.append("static")
        return {"status": "complete"}

    def functional(*args):
        calls.append("functional")
        return {"status": "complete", "verification_status": "passed"}

    def contracts(*args):
        calls.append("contracts")
        return {"status": "complete", "verification_status": "failed"}

    monkeypatch.setattr("fase2.evaluation.cli.collect_static", static)
    monkeypatch.setattr("fase2.evaluation.cli.collect_docker", functional)
    monkeypatch.setattr("fase2.evaluation.cli.collect_contracts", contracts)
    assert main(["run", commit, "--all", "--source-repo", str(repo),
                 "--results-root", str(tmp_path / "results"), "--run-id", "full"]) == 1
    assert calls == ["static", "functional", "contracts"]
    metadata = json.loads((tmp_path / "results" / "unclassified" / commit / "full" / "metadata.json").read_text())
    assert metadata["requested_categories"] == ["static", "functional", "contracts"]
    assert metadata["categories"]["contracts"]["verification_status"] == "failed"


def test_all_cannot_select_only_some_contracts():
    with pytest.raises(SystemExit) as failure:
        main(["run", "HEAD", "--all", "--contract-id", "VF-01"])
    assert failure.value.code == 2


@pytest.mark.parametrize("functional,expected_exit", [
    ({"status": "complete", "verification_status": "failed"}, 1),
    ({"status": "partial", "verification_status": "unavailable"}, 3),
])
def test_static_evidence_survives_functional_or_infrastructure_failure(tmp_path, monkeypatch,
                                                                     functional, expected_exit):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (("init", "-q"), ("config", "user.email", "test@example.test"),
                 ("config", "user.name", "Test")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    (repo / "source.py").write_text("VALUE = 1\n")
    for args in (("add", "source.py"), ("commit", "-qm", "source")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    def collect_static(source, output, python, jscpd):
        write_json(output / "summary.json", {"status": "complete", "physical_loc": 1})
        return {"status": "complete"}

    def collect_docker(source, output, run_id, timeout):
        write_json(output / "summary.json", functional)
        return functional

    monkeypatch.setattr("fase2.evaluation.cli.collect_static", collect_static)
    monkeypatch.setattr("fase2.evaluation.cli.collect_docker", collect_docker)
    result = main(["run", commit, "--static", "--functional", "--source-repo", str(repo),
                   "--results-root", str(tmp_path / "results"), "--run-id", "check"])
    assert result == expected_exit
    path = tmp_path / "results" / "unclassified" / commit / "check"
    assert json.loads((path / "static/summary.json").read_text())["physical_loc"] == 1
    metadata = json.loads((path / "metadata.json").read_text())
    assert metadata["categories"]["static"]["collection_status"] == "complete"
    assert metadata["categories"]["functional"]["verification_status"] == functional["verification_status"]


def test_role_classifies_without_changing_selected_commit(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (("init", "-q"), ("config", "user.email", "test@example.test"),
                 ("config", "user.name", "Test")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    (repo / "source.py").write_text("VALUE = 1\n")
    for args in (("add", "source.py"), ("commit", "-qm", "source")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    monkeypatch.setattr("fase2.evaluation.cli.collect_static", lambda *args: {"status": "complete"})
    assert main(["run", commit, "--role", "refactored", "--source-repo", str(repo),
                 "--results-root", str(tmp_path / "results"), "--run-id", "one"]) == 0
    metadata = json.loads((tmp_path / "results" / "refactored" / commit / "one" / "metadata.json").read_text())
    assert metadata["resolved_commit"] == metadata["worktree_head"] == commit
    assert metadata["role"] == "refactored"
    assert main(["run", commit, "--role", "baseline", "--source-repo", str(repo),
                 "--results-root", str(tmp_path / "results"), "--run-id", "two"]) == 2
    assert not (tmp_path / "results" / "baseline").exists()


def test_fixed_revisions_have_semantic_roles(tmp_path, monkeypatch):
    monkeypatch.setattr("fase2.evaluation.cli.collect_static", lambda *args: {"status": "complete"})
    for commit, role in ((BASELINE, "baseline"), (INITIAL_REFACTORED, "refactored")):
        assert main(["run", commit, "--source-repo", ".", "--results-root", str(tmp_path),
                     "--run-id", "check"]) == 0
        metadata = json.loads((tmp_path / role / commit / "check" / "metadata.json").read_text())
        assert metadata["role"] == role
        assert metadata["resolved_commit"] == commit
