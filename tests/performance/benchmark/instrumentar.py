"""Add timestamp probes to copies of the baseline sources for bind mounting."""
import os
import pathlib
import re
import sys

source, target = map(pathlib.Path, sys.argv[1:])
target.mkdir(parents=True, exist_ok=True)
worker_queue = os.environ.get("PERF_WORKER_QUEUE", "video_effects_queue")


def probe(relative, pattern, replacement):
    path = source / relative
    data, count = re.subn(pattern, lambda match: replacement(match[0]), path.read_text(), count=1)
    if count != 1:
        raise SystemExit(f"Probe location missing: {path}")
    (target / path.name).write_text(data)


probe(
    "projects/utils/rabbit_mq.js",
    r"(?m)^ +channel.publish\(exchange, queue, Buffer.from\(JSON.stringify\(msg\)\)\);",
    lambda line: (
        f'            if (queue === "{worker_queue}") '
        'console.log("PERF_PUBLISH", msg.messageId, Date.now());\n' + line
    ),
)

current_worker = source / "Tools/video_effects/video_effects.py"
worker = current_worker if current_worker.exists() else source / "Tools/video/video.py"
data = worker.read_text()
start_anchor = '            msg_id = info["messageId"]'
end_anchor = '                self._reply_success(msg_id, started, output_uri, result)'
for anchor in (start_anchor, end_anchor):
    if data.count(anchor) != 1:
        raise SystemExit(f"Probe location missing: {anchor}")

start_probe = """            project = info.get('parameters', {}).get('progress', {}).get('projectId', '-')
            print(f"PERF_START {msg_id} {started.timestamp() * 1000:.3f} {project}", flush=True)"""
end_probe = '                print(f"PERF_END {msg_id} {now().timestamp() * 1000:.3f}", flush=True)'
data = data.replace(start_anchor, f"{start_anchor}\n{start_probe}")
data = data.replace(end_anchor, f"{end_probe}\n{end_anchor}")
(target / worker.name).write_text(data)
