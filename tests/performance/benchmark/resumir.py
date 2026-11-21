"""Render the baseline measurement tables from JSONL and worker logs."""
from collections import Counter, defaultdict
import gzip
import json
import os
from math import ceil
from pathlib import Path
import re
import statistics
import sys

root = Path(sys.argv[1])
selected = set(sys.argv[2:]) or {"low", "mixed", "peak"}
operations = {
    "upload": "Upload", "cut_api": "Pedido de corte", "status": "Consulta de estado",
    "download": "Download", "cut_total": "Corte até resultado disponível",
}


def read(path):
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        return [json.loads(line) for line in stream]


def percentile(values, quantile):
    return sorted(values)[ceil(len(values) * quantile) - 1]


def memory_mib(value):
    number, unit = re.fullmatch(r"([\d.]+)\s*(B|KiB|MiB|GiB|TiB)", value.split("/")[0].strip()).groups()
    return float(number) * {"B": 2**-20, "KiB": 2**-10, "MiB": 1, "GiB": 2**10, "TiB": 2**20}[unit]


def queue_trace(publish, worker_start, start):
    changes = Counter()
    for key, timestamp in publish.items():
        if timestamp >= start:
            changes[timestamp] += 1
            if key in worker_start:
                changes[max(timestamp, worker_start[key])] -= 1
    pending = 0
    for timestamp, change in sorted(changes.items()):
        pending += change
        yield timestamp, pending


def recovery_time(points, start, end):
    zero_since = None
    for timestamp, pending in [*points, (end, None)]:
        if timestamp >= start and zero_since is not None:
            confirmed = max(start, zero_since) + 1000
            if confirmed <= min(timestamp, end):
                return (confirmed - start) / 1000
        if timestamp >= end:
            break
        if pending != 0:
            zero_since = None
        elif zero_since is None:
            zero_since = timestamp
    return None


def measure(directory, scenario, phase_name=None):
    events = read(directory / "api.jsonl")
    phases = [row for row in events if row["op"] == "phase"]
    if not phases:
        return {}
    phase = next((row for row in phases if row["name"] == phase_name), None)
    if phase_name is not None and phase is None:
        return {}
    start = (phase or phases[0])["at"]
    last = phase or phases[-1]
    end = last["at"] + last["seconds"] * 1000
    phase_events = [row for row in events if phase_name is None or row.get("phase") == phase_name]
    by_op = defaultdict(list)
    for row in phase_events:
        by_op[row["op"]].append(row)
    values = {}

    def add(metric, unit, samples, reducer):
        values[metric, unit] = (len(samples), reducer(samples) if samples else None)

    def count(metric, samples, number):
        values[metric, "pedidos"] = (len(samples), number)

    for op, label in operations.items():
        samples = [row["ms"] for row in by_op[op] if row.get("status", 200) in (200, 201, 204)]
        for quantile in ((0.5,) if scenario == "low" else (0.5, 0.95)):
            add(f"{label} p{quantile * 100:.0f}", "ms", samples, lambda data: percentile(data, quantile))

    completed, failed = by_op["completed"], by_op["failed"]
    attempted = completed + failed
    accepted = by_op["accepted"]
    count("Cortes aceites", attempted, len(accepted))
    count("Fluxos concluídos", attempted, len(completed))
    count("Fluxos falhados", attempted, len(failed))
    count("Timeouts", attempted, sum(row["timeout"] for row in failed))
    count("Chegadas descartadas pelo cliente", attempted + by_op["shed"], len(by_op["shed"]))
    add("Taxa de falhas", "%", attempted, lambda rows: 100 * len(failed) / len(rows))
    add("Taxa de timeouts", "%", attempted, lambda rows: 100 * sum(row["timeout"] for row in failed) / len(rows))
    if scenario != "low":
        elapsed_minutes = (end - start) / 60000
        active_completed = [
            row for row in events if row["op"] == "cut_total" and start <= row["at"] < end
        ]
        values["Cortes disponíveis por minuto na janela", "cortes/min"] = (
            len(active_completed), len(active_completed) / elapsed_minutes
        )

    queue = [row for row in read(directory / "rabbit.jsonl") if row.get("messages") is not None]
    if scenario != "low":
        for key, label in (
            ("messages_ready", "Prontos para entrega"), ("messages_unacknowledged", "Entregues sem ACK"),
            ("messages", "Total na fila"),
        ):
            add(f"{label}, máximo amostrado", "mensagens", [
                row[key] for row in queue if start <= row["at"] < end
            ], max)

    publish, worker_start, worker_end, projects = {}, {}, {}, {}
    starts_per_project = Counter()
    trace = directory / "worker.log"
    if trace.exists():
        for line in trace.read_text().splitlines():
            kind, message, timestamp, *project = line.split("|", 1)[1].split()
            {"PERF_PUBLISH": publish, "PERF_START": worker_start, "PERF_END": worker_end}[kind][message] = float(timestamp)
            if project:
                projects[message] = project[0]
                starts_per_project[project[0]] += 1
    ids = {row["projectId"] for row in accepted}
    jobs = {message for message, project in projects.items() if project in ids}
    add("Publicação até entrada no worker p95", "ms", [
        worker_start[key] - publish[key] for key in jobs & publish.keys()
    ], lambda data: percentile(data, 0.95))
    add("Processamento do worker p95", "ms", [
        worker_end[key] - worker_start[key] for key in jobs & worker_end.keys()
    ], lambda data: percentile(data, 0.95))
    if scenario != "low":
        worker_service = os.environ.get("PERF_WORKER_SERVICE", "video_effects_tool")
        for service in (worker_service, "api_gateway", "projects"):
            resources = [
                row for row in read(directory / "stats.jsonl")
                if row.get("Name", "").endswith(f"-{service}-1") and start <= row["at"] < end
            ]
            add(f"CPU média amostrada {service}", "% de um CPU lógico", [
                float(row["CPUPerc"].rstrip("%")) for row in resources
            ], statistics.mean)
            add(f"Memória máxima amostrada {service}", "MiB", [
                memory_mib(row["MemUsage"]) for row in resources
            ], max)

    if scenario == "mixed":
        mongo = [
            row for path in directory.glob("*-mongo.jsonl*") for row in read(path)
            if row["at"] >= start and not row["ns"].endswith(".system.profile")
        ]
        for name, predicate in (
            ("Inserções", lambda row: row["op"] == "insert"),
            ("Atualizações", lambda row: row["op"] == "update" or row["kind"] == "findAndModify"),
            ("Consultas", lambda row: row["op"] in {"query", "getmore"} or row["kind"] in {"aggregate", "count", "distinct"}),
        ):
            add(f"MongoDB {name.lower()} p95", "ms", [
                row["ms"] for row in mongo if predicate(row) and "ms" in row
            ], lambda data: percentile(data, 0.95))
        values["MongoDB operações com erro", "operações"] = (len(mongo), sum(bool(row.get("error")) for row in mongo))
        values["MongoDB operações com espera por bloqueio registada", "operações"] = (
            len(mongo), sum(any(
                "acquireWaitCount" in lock for lock in row.get("lockWaitUs", {}).values()
            ) for row in mongo),
        )

    if scenario == "peak" and phase_name is None and len(phases) == 3:
        audit = by_op["audit"]
        count("Aceites com estado final auditado e correto", accepted, sum(row["ok"] for row in audit))
        count("Aceites sem resultado final esperado", accepted, len(accepted) - sum(row["ok"] for row in audit))
        count("Resultados duplicados detetados na auditoria", audit, sum(row.get("duplicate", False) for row in audit))
        count("Pedidos aceites com processamento repetido", accepted, sum(starts_per_project[key] > 1 for key in ids))
        normal_start, peak_start, recovery_start = [row["at"] for row in phases]
        recovery = [row for row in queue if recovery_start <= row["at"] < end]
        points = list(queue_trace(publish, worker_start, normal_start))
        values["Prontos para entrega, máximo reconstruído pelo traço", "mensagens"] = (
            len(points), max((count for _, count in points), default=None)
        )
        broker_recovery = recovery_time(
            [(row["at"], row["messages_ready"]) for row in recovery], recovery_start,
            recovery[-1]["at"] if recovery else recovery_start,
        )
        values["Recuperação da fila pela API de gestão (1 s sem pedidos prontos)", "s"] = (
            len(recovery), broker_recovery
        )
        values["Recuperação da fila pelo traço durante carga normal", "s"] = (
            len(points), recovery_time(points, recovery_start, end) if points else None
        )
        observation = max([end, *(row["at"] for row in queue), *(row["at"] for row in audit)])
        values["Recuperação da fila pelo traço incluindo a drenagem", "s"] = (
            len(points), recovery_time(points, recovery_start, observation) if points else None
        )
        for op in ("upload", "cut_api", "status", "download"):
            responses = [row for row in by_op[op] if row["status"] in (200, 201, 204)]
            normal = [row["ms"] for row in responses if normal_start <= row["at"] < peak_start]
            threshold = 1.2 * percentile(normal, 0.95) if normal else None
            windows = [
                [row["ms"] for row in responses if lower <= row["at"] < lower + 3000]
                for lower in range(recovery_start, end - 2999, 3000)
            ]
            stable = [
                i + 2 for i, (first, second) in enumerate(zip(windows, windows[1:]))
                if threshold is not None and len(first) >= 3 and len(second) >= 3
                and max(percentile(first, 0.95), percentile(second, 0.95)) <= threshold
            ]
            values[f"Recuperação da latência de {operations[op].lower()}", "s"] = (
                len(responses), stable[0] * 3 if stable else None
            )
    if phase_name is not None:
        return {
            key: value for key, value in values.items()
            if key[0].startswith(("Cortes disponíveis", "Fluxos", "Timeouts", "Chegadas", "Total na fila"))
            or any(key[0].startswith(label) for label in operations.values())
        }
    return values


def rendered(value):
    if value is None:
        return "—"
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}".replace(".", ",")


def rabbit_timeline():
    repetitions = []
    for rep in (1, 2, 3):
        directory = root / f"peak-{rep}"
        phases = [row for row in read(directory / "api.jsonl") if row["op"] == "phase"]
        recovery = next(row["at"] for row in phases if row["name"] == "recovery")
        queue = [row for row in read(directory / "rabbit.jsonl") if row.get("messages_ready") is not None]
        repetitions.append((recovery, queue))
    print("| Segundos desde o fim do pico | R1 | R2 | R3 |")
    print("| ---: | ---: | ---: | ---: |")
    for seconds in (-9, -3, 0, 10, 20, 30, 45, 60, 74):
        counts = []
        for recovery, queue in repetitions:
            expected = recovery + seconds * 1000
            observed = max((row for row in queue if row["at"] <= expected), key=lambda row: row["at"], default=None)
            if observed is None or expected - observed["at"] > 1000:
                counts.append("—")
            else:
                counts.append(f'{observed["messages_ready"]} / {observed["messages_unacknowledged"]}')
        print(f"| {seconds} | " + " | ".join(counts) + " |")


if selected == {"fila"}:
    rabbit_timeline()
    sys.exit()


print("| Cenário | Métrica | Unidade | Amostras R1 / R2 / R3 | R1 | R2 | R3 |")
print("| --- | --- | --- | --- | ---: | ---: | ---: |")
for scenario, title, phase in (
    ("low", "Carga baixa", None), ("mixed", "Carga mista", None),
    ("peak", "Pico e recuperação", None), ("peak", "Pico · normal", "normal"),
    ("peak", "Pico · pico", "peak"), ("peak", "Pico · recuperação", "recovery"),
):
    if scenario not in selected and not (scenario == "peak" and phase is None and "pico-total" in selected):
        continue
    repetitions = [measure(root / f"{scenario}-{n}", scenario, phase) for n in (1, 2, 3)]
    for metric, unit in dict.fromkeys(key for data in repetitions for key in data):
        readings = [data.get((metric, unit), (0, None)) for data in repetitions]
        counts = " / ".join(str(n) for n, _ in readings)
        print(f"| {title} | {metric} | {unit} | {counts} | " + " | ".join(rendered(v) for _, v in readings) + " |")
