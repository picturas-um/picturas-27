import json
import subprocess

import pytest

from fase2.evaluation.cli import main
from fase2.evaluation.results import create_snapshot_run
from fase2.evaluation.snapshot import TemporarySnapshot


def _git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.test")
    _git(repo, "config", "user.name", "Test")
    (repo / ".gitignore").write_text("ignored.txt\n")
    (repo / "source.py").write_text("VALUE = 1\n")
    (repo / "deleted.py").write_text("OLD = 1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "initial")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_snapshot_captures_current_bytes_and_cleans_up(tmp_path):
    repo, commit = _repo(tmp_path)
    (repo / "source.py").write_text("VALUE = 2\n")
    (repo / "deleted.py").unlink()
    (repo / "new.py").write_text("NEW = 3\n")
    (repo / "ignored.txt").write_text("private\n")
    (repo / "fase2/evaluation").mkdir(parents=True)
    (repo / "fase2/evaluation/tool.py").write_text("EXTERNAL = True\n")
    with TemporarySnapshot(repo) as snapshot:
        path = snapshot.path
        assert snapshot.base_commit == commit
        assert (path / "source.py").read_text() == "VALUE = 2\n"
        assert (path / "new.py").read_text() == "NEW = 3\n"
        assert not (path / "deleted.py").exists()
        assert not (path / "ignored.txt").exists()
        assert not (path / "fase2/evaluation/tool.py").exists()
        assert not (path / ".git").exists()
        assert sorted(item["path"] for item in snapshot.files) == [".gitignore", "new.py", "source.py"]
    assert not path.exists()
    assert (repo / "source.py").read_text() == "VALUE = 2\n"
    assert _git(repo, "rev-parse", "HEAD") == commit


def test_snapshot_hash_changes_with_uncommitted_code(tmp_path):
    repo, _ = _repo(tmp_path)
    with TemporarySnapshot(repo) as first:
        original = first.sha256
    (repo / "source.py").write_text("VALUE = 2\n")
    with TemporarySnapshot(repo) as second:
        assert second.sha256 != original
        changed = second.sha256
    with TemporarySnapshot(repo) as repeated:
        assert repeated.sha256 == changed


def test_cli_uses_gitless_snapshot_and_preserves_result(tmp_path, monkeypatch):
    repo, commit = _repo(tmp_path)
    (repo / "source.py").write_text("VALUE = 2\n")
    (repo / "new.py").write_text("NEW = 3\n")
    sources = []

    def collect(source, output, python, jscpd):
        sources.append(source)
        assert not (source / ".git").exists()
        assert (source / "source.py").read_text() == "VALUE = 2\n"
        assert (source / "new.py").is_file()
        output.mkdir(parents=True)
        return {"status": "complete"}

    monkeypatch.setattr("fase2.evaluation.cli.collect_static", collect)
    result_root = tmp_path / "results"
    args = ["run", "--working-tree", "--source-repo", str(repo),
            "--results-root", str(result_root), "--run-id", "snapshot-test"]
    assert main(args) == 0
    assert not sources[0].exists()
    paths = list((result_root / "snapshots").glob("*/snapshot-test"))
    assert len(paths) == 1
    metadata = json.loads((paths[0] / "metadata.json").read_text())
    manifest = json.loads((paths[0] / "snapshot.json").read_text())
    assert metadata["source_kind"] == "working_tree_snapshot"
    assert metadata["resolved_commit"] is None
    assert metadata["base_commit"] == commit
    assert metadata["snapshot_sha256"] == manifest["sha256"]
    assert metadata["collection_status"] == "complete"
    assert main(args) == 2
    assert json.loads((paths[0] / "metadata.json").read_text()) == metadata


def test_snapshot_cleanup_after_category_failure(tmp_path, monkeypatch):
    repo, _ = _repo(tmp_path)
    sources = []

    def fail(source, output, python, jscpd):
        sources.append(source)
        raise RuntimeError("metric tool failed")

    monkeypatch.setattr("fase2.evaluation.cli.collect_static", fail)
    result_root = tmp_path / "results"
    assert main(["run", "--working-tree", "--source-repo", str(repo),
                 "--results-root", str(result_root)]) == 3
    assert not sources[0].exists()
    metadata_path = next((result_root / "snapshots").glob("*/*/metadata.json"))
    assert json.loads(metadata_path.read_text())["categories"]["static"]["collection_status"] == "failed"


def test_contract_runner_receives_base_commit_without_git_checkout(tmp_path, monkeypatch):
    repo, commit = _repo(tmp_path)
    observed = {}

    def collect(source, output, run_id, timeout, ids, source_head, snapshot_sha256):
        observed.update({"source": source, "source_head": source_head,
                         "snapshot_sha256": snapshot_sha256})
        assert not (source / ".git").exists()
        return {"status": "complete", "verification_status": "passed"}

    monkeypatch.setattr("fase2.evaluation.cli.collect_contracts", collect)
    assert main(["run", "--working-tree", "--contracts", "--source-repo", str(repo),
                 "--results-root", str(tmp_path / "results")]) == 0
    assert observed["source_head"] == commit
    assert len(observed["snapshot_sha256"]) == 64
    assert not observed["source"].exists()


def test_snapshot_run_validates_digest_and_refuses_overwrite(tmp_path):
    with pytest.raises(ValueError):
        create_snapshot_run(tmp_path, "not-a-hash")
    path, _ = create_snapshot_run(tmp_path, "a" * 64, "first")
    with pytest.raises(FileExistsError):
        create_snapshot_run(tmp_path, "a" * 64, "first")
    assert path.is_dir()


@pytest.mark.parametrize("args", [["run", "--working-tree", "HEAD"], ["run", "--working-tree", "--expect-commit", "a" * 40], ["run"]])
def test_ambiguous_cli_arguments_fail(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
