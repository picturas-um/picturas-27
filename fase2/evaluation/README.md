# PictuRAS evaluation: M1–M4

This package evaluates **locally available Git commits** or a snapshot of the
current checkout without changing the checkout or Git history. Commit runs
create a detached worktree from a disposable local bare clone. The clone uses
Git object alternates, so the original object database must remain available
until the run finishes.

## Current revision and scope

The original source commit is `ab3ae9cf8efcfa444e9599f8e291551c5930c289`.
The refactored source observed on the remote `main` on 2026-11-21 was
`914476a92b4e4bc51f925ba2c4ef9468988e57c8`. The CLI evaluates a hash
only when it is available locally and never fetches implicitly; never assume
the local `main` or `origin/main` tracking ref is current. The historical artifacts in the
`baseline` branch belong to its separate evidence commit `93746e4` and are not
overwritten by this package.

The **Python processing core** is selected from every present top-level
production `.py` file in these directories:

| Revision layout | Responsibility |
| --- | --- |
| `Tools/video/` | Original effects, temporal editing, subtitles, frame extraction, probe/encode, and RabbitMQ worker. |
| `Tools/video_effects/` | Refactored frame effects, trim/speed, probe/encode, and worker. |
| `Tools/video_subtitles/` | Speech recognition, probing, caption rendering, and worker. |
| `Tools/video_frames/` | Frame validation, probing, sampling, output/preview, and worker. |

The refactored `main` has no production `Tools/video/` directory, but Compose
still defines a compatibility `video_tool` using the `video_effects` Dockerfile.
The **complete video subsystem** also includes video validation, project
pipeline dispatch, result persistence and batch processing in `projects/`,
API forwarding, WebSocket progress, storage interfaces, RabbitMQ queue
definitions, and Compose service wiring. Direct integration files are listed
in `scope.json`; Radon and Python LOC do not include them. The new worker
modules each implement their own RabbitMQ response and progress path, and
probing remains present in all three processing domains. Image effect
implementations are a separate boundary used only for the video/image
duplication check. This prevents an image tool or a compatibility service
name from being counted as another video core module.

## Host tools and commands

Use Python 3 with Radon 6.0.1, and jscpd 5.4.3 on the host. Docker is not
needed for static metrics. A host environment can be prepared, for example, with a virtual
environment and `pip install radon==6.0.1 pytest==9.2.0`; install jscpd with
`npm install --prefix <tool-directory> jscpd@5.4.3`. Pass the resulting
executables explicitly when they are not on `PATH`.

```bash
python -m fase2.evaluation run ab3ae9cf8efcfa444e9599f8e291551c5930c289 --static \
  --python /path/to/python --jscpd /path/to/jscpd --results-root /path/to/results

python -m fase2.evaluation run 914476a92b4e4bc51f925ba2c4ef9468988e57c8 --static \
  --python /path/to/python --jscpd /path/to/jscpd --results-root /path/to/results

# Later refactoring commits need an explicit role:
python -m fase2.evaluation run NEW_FULL_COMMIT_HASH --role refactored --static \
  --python /path/to/python --jscpd /path/to/jscpd --results-root /path/to/results

python -m pytest -q fase2/tests/evaluation

# Existing application suites, built from the selected commit and run in Docker:
python -m fase2.evaluation run ab3ae9cf8efcfa444e9599f8e291551c5930c289 --functional
python -m fase2.evaluation run 914476a92b4e4bc51f925ba2c4ef9468988e57c8 --functional

# Shared M4 contracts, independent of the source commit:
python -m fase2.evaluation run ab3ae9cf8efcfa444e9599f8e291551c5930c289 --contracts
python -m fase2.evaluation run 914476a92b4e4bc51f925ba2c4ef9468988e57c8 --contracts
python -m fase2.evaluation run 914476a92b4e4bc51f925ba2c4ef9468988e57c8 --contracts --contract-id VF-07

# Complete implemented evaluation (M2, M3, M4 only):
python -m fase2.evaluation run ab3ae9cf8efcfa444e9599f8e291551c5930c289 --all \
  --python /path/to/python-with-radon --jscpd /path/to/jscpd --results-root fase2/resultados/evaluations
python -m fase2.evaluation index --results-root fase2/resultados/evaluations

# Current, uncommitted checkout (static metrics need host Radon and jscpd):
python -m fase2.evaluation run --working-tree --static

# Docker categories use the same captured source, not the developer checkout:
python -m fase2.evaluation run --working-tree --contracts --contract-id VF-07
```

`run REV` means a **local** Git reference and defaults to static metrics.
Commit results use `evaluations/<role>/<full-commit>/<run-id>/`. The fixed
baseline and initial refactored commits receive their roles automatically.
Other commits require `--role refactored` for that classification; without it,
they go under `unclassified/`. `--role` never changes the selected revision.
The baseline role accepts only the fixed baseline commit. Existing directories
under the earlier `evaluations/<commit>/<run-id>/` layout remain untouched;
`index` still reads their metadata.
`run --working-tree` captures tracked and non-ignored untracked files, including
local edits and new files; deleted files remain absent. Git-ignored files and
`fase2/evaluation/`, `fase2/tests/evaluation/`, and `fase2/resultados/` are
excluded. These exclusions keep framework code and evidence external to the
evaluated source. A symlink in the selected file list causes a preflight error.
The resulting source has no `.git` directory. The SHA-256 identity is derived
from its file paths, content hashes, modes and base commit. The per-file manifest
is saved as `snapshot.json`; the source copy is removed after the run. Results
go to `evaluations/snapshots/<snapshot-sha256>/<run-id>/`, separate from commit
results. `metadata.json` sets `resolved_commit` to null and records the full
`base_commit`, snapshot digest and framework identity. The base commit is
provenance, not a claim that its bytes were evaluated. Use a fresh run after
each edit; a snapshot is captured at CLI invocation. Explicit `run REV` keeps
its existing commit-only behavior.
`--all` runs static metrics, revision-specific Docker suites and shared Docker
contracts independently in one worktree. The categories keep separate collection
and verification statuses, so a contract failure preserves M2 and M3 evidence.
`--static --functional` runs those two categories in one worktree.
Use `--expect-commit FULL_HASH` when a branch may move. Remote reference
lookup, performance benchmarks, maintenance scenarios, and `compare` are later
milestones. Their CLI commands fail explicitly in this increment.

`index` reads recorded identities and summaries and writes `INDEX.md` under
`--results-root`. It classifies the two fixed commits, snapshots and framework
test reports by metadata content, without moving any historical directory.
Missing suite digests in older framework reports are shown as unrecorded.

Results default to `$XDG_STATE_HOME/picturas-evaluation/evaluations` (or
`~/.local/state/picturas-evaluation/evaluations`). Each run gets a new ID;
`--run-id` permits a chosen ID but refuses overwrites. Results are outside
the temporary worktree and outside the developer checkout by default.

## Measurements and evidence

`static/scope.json` records included file paths and SHA-256 hashes.
`static/inventory.json` follows the AST import/function/class and physical
line procedure of `baseline:fase2/scripts/collect_video_baseline.py`.
`static/radon-cc.json` and `radon-raw.json` preserve Radon JSON output.
The historical 4.56 complexity mean was computed over Radon's top-level
blocks, including classes; `mean_block_complexity` preserves that definition.
`mean_function_method_complexity` is reported separately and excludes class
blocks. LOC and SLOC come from Radon `raw`.

jscpd runs over staged copies of the exact selected production files, with
Python tokenization, a five-line and 50-token minimum, and no tests or
generated files. `static/internal/jscpd-report.json` is the raw internal
report. `static/video_image/jscpd-report.json` contains video and matching
image effects. Its combined percentage includes image/image clones, so the
summary separately filters clones whose two endpoints cross the video/image
boundary and does **not** invent a cross-boundary percentage. This exact
clone measurement does not measure semantic similarity.

`static/summary.json` contains metrics, tool versions, command arguments,
working directories, durations, exit codes, and log paths. `metadata.json`
contains the requested revision, resolved commit, framework code digest,
timestamps, and collection status. Missing tools leave the inventory and
other successful measurements in place and produce a nonzero exit status.

## Existing application suites in Docker (M3)

The original revision runs `Tools/video/tests` in `video_tool` and the Node
tests in `projects`. The refactored revision runs the existing tests of
`video_effects_tool`, `video_subtitles_tool`, `video_frames_tool`, and
`projects` separately. These revision-specific test counts are **not** a
common behavioral contract. The historical `baseline` branch also contains
an extra Node test that is absent from the original `ab3ae9c` commit.

M3 reuses the procedure of `baseline:fase2/scripts/test_video_docker.py`:
build the revision's service image, mount that revision's tests read-only,
install pinned pytest only in a disposable test container, then run pytest.
The original script cannot be invoked directly because its root and service
are fixed. The Node suites use the existing `node --test` runner with the
revision's test files passed explicitly.

Before any build, the framework resolves Compose configuration from the
selected worktree and rejects external or fixed-name volumes/networks,
`container_name`, bind mounts, external image tags, unexpected build contexts,
and other service isolation exceptions. The Compose project has a random
evaluation-only name and runs tests with `--no-deps --rm`; no dependency
services or published service ports are started. The production images are
not modified by pytest installation. A separate disposable container checks
SHA-256 hashes of production and mounted test files against the worktree.

Each suite has its own build, provenance, test, and log records in
`functional/summary.json`. A test failure is recorded as `failed`; build,
tool, provenance, or timeout failures are `infrastructure_error`. Other suites
continue after either kind of failure. Cleanup runs before worktree removal:
Compose `down` for the unique project, then removal of only project-owned
named volumes and uniquely tagged images. The framework does not run
`docker compose down -v` or touch the existing `picturas` deployment. Any
cleanup failure is recorded and leaves the resource for manual inspection.

## Shared behavioral contracts (M4)

`--contracts` runs the same external pytest suite from `evaluation/contracts/`
against either selected commit. It does not alter the source worktree or the
production images. The runner verifies the SHA-256 of the suite, adapter,
sample media and selected source files inside disposable containers. It reuses
M3's Compose validation, unique project name, image builds and safe cleanup.
The baseline adapter calls `video_processor`; the refactored adapter calls the
processor in the selected service. Both forward the pipeline without editing
or completing it. VF-07 asks the revision's own `projects` code to build and
route the pipeline; its chosen service receives that full pipeline.

The implemented set is VF-01 (noncommutative effect order), VF-02 (trim and
speed), VF-03 (MP4/H.264/AAC stream properties), VF-04 (audio/visual markers
after trim and speed), VF-05 (video preview), VF-06
(PNG/JPEG extraction and contact sheet), VF-07 (trim, effects and extraction
in one pipeline), VF-08 (deterministic caption rendering), VF-09 (invalid
video/trim/speed), VF-09X (non-terminal extraction), VF-10 (worker reply
and progress), and VF-11 (worker reply and `projects` frame result helper with
controlled storage). VF-01 compares a decoded output frame with both effect orders,
using the same image dimensions. `contracts/summary.json` records the contract
ID, level, exact assertions and tolerances, suite and adapter hashes, input
hashes, image IDs, native route, JUnit counts, command logs and cleanup status.
Individual evidence and JUnit files are under `contracts/<contract-id>/`.
Assertion failures are `failed`; missing test reports, build failures and
provenance failures are `infrastructure_error`. Other contracts continue.

This increment covers processor, native routing, and worker-callback contracts.
VF-04 generates a small marker video within the disposable container and records
its SHA-256; only matching input hashes across runs permit comparison.
Model-backed speech recognition (the real speech variant of VF-08), and a full
deployment integration with RabbitMQ, MongoDB, object storage and the HTTP API
are still pending. The real speech case uses
`speech_mandela_177s_1080p.webm`, requires Faster-Whisper with
`WHISPER_MODEL=small`, CPU/int8, `WHISPER_CPU_THREADS=2`, a recorded model
identity and an isolated `WHISPER_CACHE_DIR`. It will require a separate opt-in
command because model initialization and recognition are expensive. VF-03 checks stream
codecs and end times; VF-04 adds a marker-based A/V sync check. VF-05 checks the three-second
preview, not every composition of temporal effects. VF-10 captures the actual
worker callback with a controlled channel; it does not start RabbitMQ or the
browser. VF-11 executes native `projects` routing, the selected worker callback,
and `persistFrameResults` from the selected `projects` image. Storage is a
controlled in-memory implementation, so it does not verify MongoDB or S3.
No general claim of functional equivalence should be based on the implemented
subset alone.

Completed runs can be archived under `fase2/resultados/evaluations/`, separate
from the historical `fase2/resultados/baseline/` evidence. Archived raw JSON
retains the absolute execution-time command and log paths; the log files are
copied alongside it, with `archive.json` documenting the relocation.
