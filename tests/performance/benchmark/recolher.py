"""Sample queue depth and container resource usage from the isolated Compose project."""
import base64
import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.request

project, rabbit_port, destination = sys.argv[1:]
headers = {"Authorization": "Basic " + base64.b64encode(b"user:password").decode()}
queue = urllib.request.Request(
    f"http://127.0.0.1:{rabbit_port}/api/queues/%2F/video_queue", headers=headers
)


def rabbit(out):
    while True:
        sample = {"at": time.time_ns() // 1_000_000}
        try:
            with urllib.request.urlopen(queue, timeout=2) as response:
                data = json.load(response)
            sample.update({key: data.get(key) for key in (
                "messages", "messages_ready", "messages_unacknowledged", "consumers", "message_stats"
            )})
        except (OSError, ValueError) as error:
            sample["error"] = str(error)
        print(json.dumps(sample), file=out, flush=True)
        time.sleep(0.5)


def stats(out):
    names = [f"{project}-{service}-1" for service in ("video_tool", "api_gateway", "projects")]
    while True:
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}", *names],
                capture_output=True, text=True, timeout=8, check=True,
            )
            timestamp = time.time_ns() // 1_000_000
            for line in result.stdout.splitlines():
                print(json.dumps({"at": timestamp, **json.loads(line)}), file=out, flush=True)
        except (ValueError, subprocess.SubprocessError) as error:
            print(json.dumps({"at": time.time_ns() // 1_000_000, "error": str(error)}), file=out, flush=True)
        time.sleep(0.2)



with (
    open(os.path.join(destination, "rabbit.jsonl"), "w") as queue_out,
    open(os.path.join(destination, "stats.jsonl"), "w") as stats_out,
    concurrent.futures.ThreadPoolExecutor() as pool,
):
    pool.submit(rabbit, queue_out)
    stats(stats_out)
