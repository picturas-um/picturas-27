#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
root=$PWD
commit=$(git rev-parse "${1:-0523102}^{commit}")
out=$(realpath -m "${2:-tests/performance/resultados-desempenho-inicial}")
mkdir -p "$out"
export PERF_HTTPS_PORT=${PERF_HTTPS_PORT:-18443}
export PERF_RABBIT_PORT=${PERF_RABBIT_PORT:-18672}
export TEST_BASE_URL="https://localhost:$PERF_HTTPS_PORT"
export TZ=Europe/Lisbon
stack=picturas-perf-$$
worktree=$(mktemp -d)
git worktree add --detach "$worktree" "$commit"
if [[ -f "$worktree/Tools/video_effects/video_effects.py" ]]; then
  worker_service=video_effects_tool
  worker_file=video_effects.py
  worker_queue=video_effects_queue
else
  worker_service=video_tool
  worker_file=video.py
  worker_queue=video_queue
fi
export PERF_WORKER_SERVICE=$worker_service PERF_WORKER_QUEUE=$worker_queue
scratch=$(mktemp -d)
base=(docker compose -p "$stack" -f "$worktree/docker-compose.yaml" -f "$root/tests/performance/benchmark/compose-isolado.yaml")
compose=("${base[@]}" -f "$scratch/probes.yaml")
sampler=
cleanup() {
  if [[ -n $sampler ]]; then kill -- "-$sampler" 2>/dev/null || true; fi
  "${base[@]}" down -t 2 -v --remove-orphans >> "$out/isolamento.log" 2>&1 || true
  git worktree remove "$worktree" >> "$out/isolamento.log" 2>&1
  rm -rf "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
python3 tests/performance/benchmark/instrumentar.py "$worktree" "$scratch"
cat > "$scratch/probes.yaml" <<PROBES
services:
  projects:
    volumes:
      - "$scratch/rabbit_mq.js:/app/utils/rabbit_mq.js:ro"
  $worker_service:
    volumes:
      - "$scratch/$worker_file:/app/$worker_file:ro"
PROBES
services=(nginx frontend "$worker_service" img_storage subscriptions)
ready() {
  for ((attempt=0; attempt<120; attempt++)); do
    if curl -kfsS --max-time 3 "$TEST_BASE_URL" >/dev/null &&
       curl -fsS -u user:password "http://127.0.0.1:$PERF_RABBIT_PORT/api/queues/%2F/$worker_queue" |
         python3 -c 'import json,sys; assert json.load(sys.stdin)["consumers"] == 1' 2>/dev/null; then
      return
    fi
    sleep 2
  done
  return 1
}
mongo() {
  "${compose[@]}" exec -T "$1" mongo --quiet --port "$2" "$3" --eval "$4"
}
video=${PERF_VIDEO:-tests/fixtures/videos/clip.mp4}
dbs=(projects_mongoDB:27018:project users_mongoDB:27019:user subscriptions_mongoDB:27017:subscription)
{
  echo "$commit"
  date -Iseconds
  lscpu
  free -b
  docker version --format '{{.Server.Version}}'
  docker compose version
  node --version
  ffprobe -v error -show_format -show_streams "$video"
  sha256sum "$video"
} > "$out/ambiente.txt"
"${base[@]}" build --with-dependencies "${services[@]}" > "$out/arranque.log" 2>&1
docker image inspect "$stack-$worker_service" --format '{{.Id}} {{.Size}}' > "$out/imagem-worker.txt"
for scenario in ${PERF_SCENARIOS:-low mixed peak}; do
  for rep in ${PERF_REPETITIONS:-1 2 3}; do
    run="$out/$scenario-$rep"
    mkdir -p "$run"
    "${compose[@]}" down -t 2 -v --remove-orphans >> "$out/isolamento.log" 2>&1
    "${compose[@]}" up --no-build -d "${services[@]}" > "$run/startup.log" 2>&1
    if ! ready 2>>"$run/startup.log"; then
      "${compose[@]}" logs --tail=100 > "$run/diagnostico.log"
      exit 1
    fi
    export TEST_REGISTRY_PATH="$run/contas.jsonl"
    node tests/performance/benchmark/carga.cjs warmup "$run/warmup.jsonl"
    if [[ $(rg -c '"op":"completed"' "$run/warmup.jsonl") != 4 ]]; then
      "${compose[@]}" logs --tail=100 > "$run/diagnostico.log"
      exit 1
    fi
    for entry in "${dbs[@]}"; do
      IFS=: read -r svc port db <<< "$entry"
      mongo "$svc" "$port" "$db" 'db.getCollectionNames().forEach(n => printjson({collection:n,count:db[n].countDocuments({})})); db.createCollection("system.profile",{capped:true,size:67108864}); db.setProfilingLevel(2)' > "$run/$db-inicial.log"
    done
    "${compose[@]}" images > "$run/images.txt"
    "${compose[@]}" ps -q | xargs docker inspect --format '{{.Name}} {{.Image}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}' > "$run/limites.txt"
    setsid python3 tests/performance/benchmark/recolher.py "$stack" "$PERF_RABBIT_PORT" "$run" &
    sampler=$!
    node tests/performance/benchmark/carga.cjs "$scenario" "$run/api.jsonl"
    kill -- "-$sampler" 2>/dev/null || true
    wait "$sampler" 2>/dev/null || true
    sampler=
    for entry in "${dbs[@]}"; do
      IFS=: read -r svc port db <<< "$entry"
      mongo "$svc" "$port" "$db" 'db.setProfilingLevel(0); db.system.profile.find().forEach(x=>print(JSON.stringify({at:+x.ts,op:x.op,ns:x.ns,ms:x.millis,kind:Object.keys(x.command||{})[0],error:x.errCode||x.errName,lockWaitUs:x.locks,waiting:x.flowControl})))' > "$run/$db-mongo.jsonl"
    done
    "${compose[@]}" logs --no-color projects "$worker_service" | awk '/PERF_(PUBLISH|START|END)/' > "$run/worker.log"
  done
done
if [[ ${PERF_REGRESSION:-1} == 1 ]]; then
  "${base[@]}" up -d --build resize_tool > "$out/resize-regressao.log" 2>&1
  export TEST_REGISTRY_PATH="$out/regressao-contas.jsonl"
  export COMPOSE_PROJECT_NAME="$stack"
  export COMPOSE_FILE="$worktree/docker-compose.yaml:$root/tests/performance/benchmark/compose-isolado.yaml"
  date -Iseconds > "$out/api-hora.txt"
  node --test --test-concurrency=1 --test-reporter=tap \
    --test-name-pattern='trim and speed|video progress|silent video|edited timeline and ZIP|mixed media applies|failed video stage' \
    tests/functional/integration/processing.test.js > "$out/api-regressao.tap" 2>&1 || true
fi
