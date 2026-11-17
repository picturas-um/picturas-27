"""Worker progress-message contract, without a broker or FFmpeg dependency."""
import ast
import datetime
from pathlib import Path
import unittest
import uuid


class ProgressRecoveryTests(unittest.TestCase):
    def setUp(self):
        # Compile the production method in isolation; only the transport is fake.
        source = Path(__file__).resolve().parents[3] / "Tools/video/video.py"
        worker = next(node for node in ast.parse(source.read_text()).body
                      if isinstance(node, ast.ClassDef) and node.name == "VideoWorker")
        method = next(node for node in worker.body
                      if isinstance(node, ast.FunctionDef) and node.name == "_progress")
        namespace = {"PROJECT_QUEUE": "project_queue", "WS_QUEUE": "ws_queue", "uuid": uuid,
                     "now": lambda: datetime.datetime.now(datetime.timezone.utc)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
        self.published = []
        self.worker = type("Transport", (), {})()
        self.worker._publish = lambda queue, message: self.published.append((queue, message))
        self.progress = lambda preview=False: namespace["_progress"](
            self.worker, {"user": "owner", "projectId": "project", "imgId": "video"},
            preview, 42, "request-original")

    def test_full_run_progress_is_correlated_for_persistence_and_still_reaches_websocket(self):
        self.progress()
        queue, message = self.published[0]
        self.assertEqual(queue, "project_queue")
        self.assertEqual(message, {"type": "video-progress", "correlationId": "request-original", "percent": 42})
        queue, message = self.published[1]
        self.assertEqual(queue, "ws_queue")
        self.assertEqual(message["percent"], 42)
        self.assertEqual(message["projectId"], "project")

    def test_preview_does_not_change_persisted_full_run_progress(self):
        self.progress(preview=True)
        self.assertEqual(len(self.published), 1)
        self.assertEqual(self.published[0][0], "ws_queue")
        self.assertTrue(self.published[0][1]["preview"])


if __name__ == "__main__":
    unittest.main()
