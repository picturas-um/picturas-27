#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
root=$PWD
commit=$(git rev-parse "${1:-0523102}^{commit}")
out=$(realpath -m "${2:-tests/performance/resultados-desempenho-inicial}")
mkdir -p "$out"
python=${PERF_PYTHON:-$root/.venv/bin/python}
export TZ=Europe/Lisbon
worktree=$(mktemp -d)
scratch=$(mktemp -d)
git worktree add --detach "$worktree" "$commit"
cleanup() {
  git worktree remove "$worktree"
  rm -rf "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ ${PERF_BASELINE_PYTHON:-1} == 1 ]]; then
  date -Iseconds > "$out/regressao-hora.txt"
  (cd "$worktree/Tools/video" && "$python" -m pytest -q tests --junitxml="$out/video.xml") > "$out/video.log" 2>&1 || true
fi

# Copy tests alone. Their relative imports resolve the baseline's projects/utils.
mkdir -p "$scratch/projects/tests"
for part in utils models controllers; do
  ln -s "$worktree/projects/$part" "$scratch/projects/$part"
done
# Node resolves symlinks to their original paths when loading utils, so NODE_PATH
# makes the installed test dependencies available from the isolated checkout.
date -Iseconds > "$out/node-hora.txt"
cp projects/tests/*.test.js "$scratch/projects/tests/"
NODE_PATH="$root/node_modules" node --test --test-reporter=tap "$scratch"/projects/tests/*.test.js > "$out/node-regressao.tap" 2>&1 || true

# Copy only each suite's tests to make missing interfaces explicit at collection.
if [[ ${PERF_CHECK_COMPATIBILITY:-1} == 0 ]]; then exit 0; fi
for part in video_effects video_frames video_subtitles; do
  mkdir -p "$scratch/$part"
  cp -r "Tools/$part/tests" "$scratch/$part/"
  date -Iseconds > "$out/$part-hora.txt"
  (cd "$scratch/$part" && PYTHONPATH="$worktree/Tools/video" "$python" -m pytest --collect-only -q tests) > "$out/$part-compatibilidade.log" 2>&1 || true
done
