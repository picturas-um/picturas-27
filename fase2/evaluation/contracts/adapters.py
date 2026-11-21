"""Call the selected revision's native processor without altering its pipeline."""

import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace


MODULES = {
    ("baseline", "video_tool"): "video_processor",
    ("refactored", "video_effects_tool"): "effects",
    ("refactored", "video_frames_tool"): "frame_extraction",
    ("refactored", "video_subtitles_tool"): "subtitles",
}

WORKERS = {
    ("baseline", "video_tool"): ("video", "VideoWorker", "video"),
    ("refactored", "video_effects_tool"): ("video_effects", "VideoEffectsWorker", "video_effects"),
    ("refactored", "video_frames_tool"): ("video_frames", "VideoFramesWorker", "video_frames"),
}


class ProcessorAdapter:
    def __init__(self, architecture: str, service: str):
        try:
            module_name = MODULES[(architecture, service)]
        except KeyError as error:
            raise ValueError(f"No adapter for {architecture}/{service}") from error
        self.architecture = architecture
        self.service = service
        self.module = importlib.import_module(module_name)
        source = Path(self.module.__file__).resolve()
        if Path("/app") not in source.parents:
            raise RuntimeError(f"Processor was loaded outside the selected image: {source}")
        self.source = str(source)

    def execute(self, source: Path, output: Path, pipeline: list[dict],
                preview: bool = False, progress=None) -> dict:
        return self.module.process_video(str(source), str(output), pipeline,
                                         progress_cb=progress, preview=preview)

    def invoke_worker(self, source: Path, output: Path, pipeline: list[dict],
                      message_id: str = "m4-vf10-request") -> dict:
        module_name, class_name, procedure = WORKERS[(self.architecture, self.service)]
        module = importlib.import_module(module_name)
        if Path("/app") not in Path(module.__file__).resolve().parents:
            raise RuntimeError("Worker was loaded outside the selected image")

        class CaptureChannel:
            def __init__(self):
                self.messages = []
                self.acks = []

            def basic_publish(self, exchange, routing_key, body):
                self.messages.append({"exchange": exchange, "queue": routing_key,
                                      "body": json.loads(body)})

            def basic_ack(self, delivery_tag):
                self.acks.append(delivery_tag)

        channel = CaptureChannel()
        worker = getattr(module, class_name).__new__(getattr(module, class_name))
        worker._channel = channel
        request = {"messageId": message_id, "procedure": procedure,
                   "parameters": {"inputImageURI": str(source), "outputImageURI": str(output),
                                  "tools": pipeline, "preview": False,
                                  "progress": {"user": "m4-user", "projectId": "m4-project",
                                               "imgId": "m4-video"}}}
        worker.callback(channel, SimpleNamespace(delivery_tag=7), None,
                        json.dumps(request).encode())
        return {"request": request, "messages": channel.messages, "acks": channel.acks,
                "worker_source": str(Path(module.__file__).resolve())}


def selected_adapter() -> ProcessorAdapter:
    return ProcessorAdapter(os.environ["EVAL_ARCHITECTURE"], os.environ["EVAL_SERVICE"])
