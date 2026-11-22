"""Command-line entry point for local-revision static and Docker evaluation."""

import argparse
import hashlib
import subprocess
import sys
import uuid
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

from .contract_runner import SPECS, collect_contracts
from .docker import collect_docker
from .git import GitError, TemporaryWorktree, repository_root, resolve_commit
from .index import BASELINE, INITIAL_REFACTORED, build_index
from .results import create_run, create_snapshot_run, default_root, write_json
from .reporting import compare as compare_runs, discover, load, select
from .report_views import comparison_html, comparison_text, list_text, run_html, run_text
from .snapshot import TemporarySnapshot
from .static import collect_static


def _framework_identity() -> dict:
    repo = repository_root(Path(__file__).resolve().parent)
    files = sorted((Path(__file__).parent).glob("*.py"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--short", "--", "fase2/evaluation"],
        capture_output=True, text=True,
    )
    return {
        "repository_head": resolve_commit(repo, "HEAD"),
        "code_sha256": digest.hexdigest(),
        "working_tree_status": status.stdout.strip() if status.returncode == 0 else "unavailable",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate local Git revisions of PictuRAS")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="evaluate a locally available commit")
    run.add_argument("revision", nargs="?", help="local Git branch, tag, or commit")
    run.add_argument("--working-tree", action="store_true",
                     help="evaluate a disposable snapshot of the current checkout")
    run.add_argument("--static", action="store_true", help="run host-side static metrics (default)")
    run.add_argument("--functional", action="store_true", help="run existing revision-specific suites in Docker")
    run.add_argument("--contracts", action="store_true", help="run shared M4 behavioral contracts in Docker")
    run.add_argument("--contract-id", action="append", choices=sorted(SPECS),
                     help="select a shared contract (repeatable; requires --contracts)")
    run.add_argument("--all", action="store_true", help="run M2 static, M3 revision suites and M4 contracts")
    for category in ("performance", "maintenance"):
        run.add_argument(f"--{category}", action="store_true", help="not implemented in M1–M4")
    run.add_argument("--expect-commit", help="fail if the revision resolves to another full commit hash")
    run.add_argument("--role", choices=("baseline", "refactored"),
                     help="classify commit results; never changes the selected revision")
    run.add_argument("--results-root", type=Path, default=default_root())
    run.add_argument("--run-id")
    run.add_argument("--source-repo", type=Path, help="Git repository containing the revision")
    run.add_argument("--python", default=sys.executable, help="host Python with Radon installed")
    run.add_argument("--jscpd", default="jscpd", help="host jscpd executable")
    run.add_argument("--docker-timeout", type=int, default=3600,
                     help="maximum seconds for each Docker build or suite (default: 3600)")
    listing = subparsers.add_parser("list", help="list recorded evaluations")
    listing.add_argument("--results-root", type=Path, default=default_root())
    listing.add_argument("--role", choices=("baseline", "refactored", "framework", "snapshot", "unclassified"))
    listing.add_argument("--revision", help="filter by full commit or commit prefix")
    report = subparsers.add_parser("report", help="show one recorded evaluation")
    report.add_argument("run", help="exact run ID or path relative to results-root")
    report.add_argument("--results-root", type=Path, default=default_root())
    report.add_argument("--format", choices=("terminal", "html"), default="terminal")
    report.add_argument("--output", type=Path, help="HTML output path; existing files are never replaced")
    compare = subparsers.add_parser("compare", help="compare two explicitly selected evaluations")
    compare.add_argument("left", help="baseline or earlier refactored run ID/path")
    compare.add_argument("right", help="refactored run ID/path")
    compare.add_argument("--left-static", help="explicit M2 run for the left commit")
    compare.add_argument("--right-static", help="explicit M2 run for the right commit")
    compare.add_argument("--results-root", type=Path, default=default_root())
    compare.add_argument("--format", choices=("terminal", "html"), default="terminal")
    compare.add_argument("--output", type=Path, help="HTML output path; existing files are never replaced")
    index = subparsers.add_parser("index", help="write an index from existing result metadata")
    index.add_argument("--results-root", type=Path, default=default_root())
    index.add_argument("--output", type=Path, help="default: INDEX.md under results-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "index":
        try:
            output = build_index(args.results_root, args.output)
        except (OSError, ValueError) as error:
            print(f"Cannot build evaluation index: {error}", file=sys.stderr)
            return 2
        print(f"Index: {output}")
        return 0
    if args.command in {"list", "report", "compare"}:
        if args.command != "list" and args.output and args.format != "html":
            parser.error("--output requires --format html")
        try:
            runs = discover(args.results_root)
            if args.command == "list":
                found = [run for run in runs if (not args.role or run["role"] == args.role)
                         and (not args.revision or (run["commit"] or "").startswith(args.revision))]
                print(list_text([load(run) for run in found]))
                return 0
            if args.command == "report":
                run = load(select(runs, args.run))
                if args.format == "terminal":
                    print(run_text(run))
                    return 0
                output = args.output or args.results_root / "reports" / f"{run['run_id']}-{uuid.uuid4().hex[:8]}.html"
                content = run_html(run, output.expanduser().resolve())
            else:
                left, right = load(select(runs, args.left)), load(select(runs, args.right))
                ls = load(select(runs, args.left_static)) if args.left_static else None
                rs = load(select(runs, args.right_static)) if args.right_static else None
                result = compare_runs(left, right, ls, rs)
                if args.format == "terminal":
                    print(comparison_text(result))
                    return 0
                output = args.output or args.results_root / "reports" / f"compare-{uuid.uuid4().hex[:8]}.html"
                content = comparison_html(result, output.expanduser().resolve())
            output = output.expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                stream.write(content)
            print(f"HTML report: {output}")
            return 0
        except (OSError, ValueError) as error:
            print(f"Reporting failed: {error}", file=sys.stderr)
            return 2
    unsupported = [name for name in ("performance", "maintenance") if getattr(args, name)]
    if unsupported:
        parser.error(f"categories not implemented in M1–M4: {', '.join(unsupported)}")
    if args.docker_timeout <= 0:
        parser.error("--docker-timeout must be positive")
    if args.contract_id and not (args.contracts or args.all):
        parser.error("--contract-id requires --contracts or --all")
    if args.all and args.contract_id:
        parser.error("--all runs every M4 contract; use --contracts to select contract IDs")
    if args.working_tree and args.revision:
        parser.error("--working-tree does not accept a revision")
    if not args.working_tree and not args.revision:
        parser.error("run requires a revision or --working-tree")
    if args.working_tree and args.expect_commit:
        parser.error("--expect-commit applies only to Git revision runs")
    if args.working_tree and args.role:
        parser.error("--role applies only to Git revision runs")
    do_static = args.static or args.all or not (args.functional or args.contracts)
    do_functional = args.functional or args.all
    do_contracts = args.contracts or args.all
    requested = ((["static"] if do_static else []) + (["functional"] if do_functional else [])
                 + (["contracts"] if do_contracts else []))
    snapshot = None
    try:
        repo = repository_root(args.source_repo or Path.cwd())
        if args.working_tree:
            snapshot = TemporarySnapshot(repo, args.results_root)
            snapshot.__enter__()
            commit = snapshot.base_commit
        else:
            commit = resolve_commit(repo, args.revision)
            if args.expect_commit and commit != args.expect_commit:
                raise GitError(f"Revision resolved to {commit}, expected {args.expect_commit}")
        role = ("snapshot" if snapshot else args.role or
                ("baseline" if commit == BASELINE else
                 "refactored" if commit == INITIAL_REFACTORED else "unclassified"))
        if not snapshot and role == "baseline" and commit != BASELINE:
            raise ValueError(f"The baseline role is fixed to {BASELINE}; selected {commit}")
        if not snapshot and role == "refactored" and commit == BASELINE:
            raise ValueError("The fixed baseline commit cannot be classified as refactored")
    except (GitError, OSError, ValueError) as error:
        print(f"Git preflight failed: {error}", file=sys.stderr)
        return 2

    try:
        output, run_id = (create_snapshot_run(args.results_root, snapshot.sha256, args.run_id)
                          if snapshot else create_run(args.results_root, role, commit, args.run_id))
    except (OSError, ValueError) as error:
        if snapshot:
            snapshot.__exit__(None, None, None)
        print(f"Cannot create result directory: {error}", file=sys.stderr)
        return 2

    metadata = {
        "schema_version": 1,
        "requested_revision": "working-tree" if snapshot else args.revision,
        "resolved_commit": None if snapshot else commit,
        "role": role,
        "run_id": run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": str(repo),
        "framework": _framework_identity(),
        "requested_categories": requested,
        "categories": {},
        "collection_status": "pending",
        "verification_status": "skipped",
        "results_directory": str(output),
    }
    if snapshot:
        metadata.update({"schema_version": 2, "source_kind": "working_tree_snapshot",
                         "base_commit": commit, "snapshot_sha256": snapshot.sha256,
                         "snapshot_manifest": "snapshot.json"})
        write_json(output / "snapshot.json", {
            "schema_version": 1, "base_commit": commit, "sha256": snapshot.sha256,
            "files": snapshot.files,
            "selection": "tracked and non-ignored untracked files; excludes evaluation code and results",
        })
    else:
        metadata["source_kind"] = "commit"
    write_json(output / "metadata.json", metadata)
    print(f"Captured working tree snapshot {snapshot.sha256} (base {commit})" if snapshot
          else f"Resolved {args.revision!r} to {commit}", flush=True)
    print(f"Results: {output}", flush=True)
    try:
        with (nullcontext(snapshot.path) if snapshot else TemporaryWorktree(repo, commit)) as source:
            if not snapshot:
                metadata["worktree_head"] = resolve_commit(source, "HEAD")
            write_json(output / "metadata.json", metadata)
            if do_static:
                try:
                    summary = collect_static(source, output / "static", args.python, args.jscpd)
                    metadata["categories"]["static"] = {"collection_status": summary["status"],
                                                       "verification_status": "skipped",
                                                       "summary": "static/summary.json"}
                except (OSError, ValueError, RuntimeError) as error:
                    metadata["categories"]["static"] = {"collection_status": "failed",
                                                       "verification_status": "skipped", "error": str(error)}
                write_json(output / "metadata.json", metadata)
            if do_functional:
                try:
                    summary = collect_docker(source, output / "functional", run_id, args.docker_timeout)
                    metadata["categories"]["functional"] = {
                        "collection_status": summary["status"],
                        "verification_status": summary["verification_status"],
                        "summary": "functional/summary.json",
                    }
                except (OSError, ValueError, RuntimeError) as error:
                    metadata["categories"]["functional"] = {"collection_status": "failed",
                                                           "verification_status": "unavailable", "error": str(error)}
                write_json(output / "metadata.json", metadata)
            if do_contracts:
                try:
                    contract_args = (source, output / "contracts", run_id,
                                     args.docker_timeout, args.contract_id)
                    summary = (collect_contracts(*contract_args, source_head=commit,
                                                 snapshot_sha256=snapshot.sha256) if snapshot
                               else collect_contracts(*contract_args))
                    metadata["categories"]["contracts"] = {
                        "collection_status": summary["status"],
                        "verification_status": summary["verification_status"],
                        "summary": "contracts/summary.json",
                    }
                except (OSError, ValueError, RuntimeError) as error:
                    metadata["categories"]["contracts"] = {
                        "collection_status": "failed", "verification_status": "unavailable", "error": str(error)}
                write_json(output / "metadata.json", metadata)
            states = metadata["categories"].values()
            metadata["collection_status"] = "complete" if all(
                item["collection_status"] == "complete" for item in states) else "partial"
            verification = [item["verification_status"] for item in states]
            metadata["verification_status"] = "failed" if "failed" in verification else (
                "unavailable" if "unavailable" in verification else (
                    "passed" if "passed" in verification else "skipped"))
    except KeyboardInterrupt:
        metadata["collection_status"] = "interrupted"
        metadata["error"] = "Evaluation interrupted"
        return 130
    except (GitError, OSError, ValueError, RuntimeError) as error:
        metadata["collection_status"] = "failed"
        metadata["error"] = str(error)
    finally:
        if snapshot:
            try:
                snapshot.__exit__(None, None, None)
            except OSError as error:
                metadata["collection_status"] = "failed"
                metadata["cleanup_error"] = str(error)
        metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "metadata.json", metadata)

    try:
        relative = output.resolve().relative_to(args.results_root.expanduser().resolve()).as_posix()
        print(run_text(load(select(discover(args.results_root), relative))))
    except (OSError, ValueError) as error:
        print(f"Could not display evaluation summary: {error}", file=sys.stderr)

    if metadata["verification_status"] == "failed":
        print(f"Application tests failed; see {output}", file=sys.stderr)
        return 1
    if metadata["collection_status"] != "complete" or metadata["verification_status"] == "unavailable":
        print(f"Evaluation incomplete; see {output}", file=sys.stderr)
        return 3
    print("Requested evaluation complete")
    return 0
