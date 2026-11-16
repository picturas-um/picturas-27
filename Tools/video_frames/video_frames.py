"""PictuRAS frame extraction microservice (RabbitMQ worker).

Consumes video_frames_queue, extracts still frames or contact sheet previews,
and replies on project_queue. Sends progress events to ws_queue.
"""
import datetime
import json
import os
import time
import uuid

import pika
import pytz
from pika.exchange_type import ExchangeType

import utils.env as env
from frame_extraction import InvalidExtraction, InvalidVideo, process_video

EXCHANGE = "picturas"
VIDEO_QUEUE = os.getenv("VIDEO_QUEUE", "video_frames_queue")
PROJECT_QUEUE = "project_queue"
WS_QUEUE = "ws_queue"
MICROSERVICE = "picturas-video-frames-tool-ms"

CODES = {
    "wrong_procedure": 2000,
    "error_processing": 2001,
    "invalid_extraction": 2002,
    "invalid_video": 2004,
}


def now():
    return datetime.datetime.now(pytz.utc)


class VideoFramesWorker:
    def __init__(self):
        self._connection = self._connect()
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=EXCHANGE,
                                       exchange_type=ExchangeType.direct, durable=True)
        self._channel.queue_declare(queue=VIDEO_QUEUE, durable=True)
        self._channel.queue_bind(queue=VIDEO_QUEUE, exchange=EXCHANGE, routing_key=VIDEO_QUEUE)
        self._channel.basic_qos(prefetch_count=1)

    @staticmethod
    def _connect():
        credentials = pika.PlainCredentials(env.RABBITMQ_USERNAME, env.RABBITMQ_PASSWORD)
        params = pika.ConnectionParameters(
            env.RABBITMQ_HOST, int(env.RABBITMQ_PORT), "/", credentials,
            heartbeat=0,
        )
        for attempt in range(30):
            try:
                return pika.BlockingConnection(params)
            except pika.exceptions.AMQPConnectionError:
                time.sleep(2)
        raise RuntimeError("Could not connect to RabbitMQ")

    def _publish(self, queue, msg):
        self._channel.basic_publish(exchange=EXCHANGE, routing_key=queue,
                                    body=json.dumps(msg))

    def _reply_success(self, msg_id, started, output_uri, video_info):
        output = {
            "type": video_info.get("output_type", "frames"),
            "imageURI": video_info.get("output_path", output_uri),
        }
        if output["type"] == "frames":
            output["frames"] = video_info.get("frames", [])
        self._publish(PROJECT_QUEUE, {
            "messageId": f"video-frames-{uuid.uuid4()}",
            "correlationId": msg_id,
            "timestamp": now().isoformat(),
            "status": "success",
            "output": output,
            "metadata": {
                "processingTime": (now() - started).total_seconds() * 1000,
                "microservice": MICROSERVICE,
                "video": video_info,
            },
        })

    def _reply_error(self, msg_id, started, code, message, input_uri):
        self._publish(PROJECT_QUEUE, {
            "messageId": f"video-frames-{uuid.uuid4()}",
            "correlationId": msg_id,
            "timestamp": now().isoformat(),
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "msg": message,
                "details": {"inputFileURI": input_uri},
            },
            "metadata": {
                "processingTime": (now() - started).total_seconds() * 1000,
                "microservice": MICROSERVICE,
            },
        })

    def _progress(self, progress, preview, percent):
        if not progress or not progress.get("user"):
            return
        self._publish(WS_QUEUE, {
            "messageId": f"update-client-video-progress-{uuid.uuid4()}",
            "timestamp": now().isoformat(),
            "status": "success",
            "user": progress["user"],
            "projectId": progress.get("projectId"),
            "imgId": progress.get("imgId"),
            "preview": bool(preview),
            "percent": percent,
        })

    def callback(self, ch, method, properties, body):
        started = now()
        try:
            info = json.loads(body.decode())
            msg_id = info["messageId"]
            params = info["parameters"]
            input_uri = params["inputImageURI"]
            output_uri = params["outputImageURI"]
            tools = params.get("tools") or []
            if not tools and "mode" in params:
                tools = [{"procedure": "extract_frames", "params": params}]
            preview = bool(params.get("preview"))
            progress = params.get("progress") or {}
        except (ValueError, KeyError) as e:
            print(f"[video_frames] invalid message discarded: {e}", flush=True)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"[video_frames] msg={msg_id} preview={preview}", flush=True)

        procedure = info.get("procedure")
        if procedure not in ("video_frames", "extract_frames", "video"):
            self._reply_error(msg_id, started, CODES["wrong_procedure"],
                              "The procedure received does not fit into this tool", input_uri)
        else:
            try:
                result = process_video(
                    input_uri, output_uri, tools,
                    progress_cb=lambda pct: self._progress(progress, preview, pct),
                    preview=preview,
                )
                self._reply_success(msg_id, started, output_uri, result)
                print(f"[video_frames] msg={msg_id} ok t={(now() - started).total_seconds():.1f}s",
                      flush=True)
            except InvalidExtraction as e:
                self._reply_error(msg_id, started, CODES["invalid_extraction"], str(e), input_uri)
            except InvalidVideo as e:
                self._reply_error(msg_id, started, CODES["invalid_video"], str(e), input_uri)
            except Exception as e:  # noqa: BLE001
                self._reply_error(msg_id, started, CODES["error_processing"], str(e), input_uri)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        self._channel.basic_consume(queue=VIDEO_QUEUE, on_message_callback=self.callback,
                                    auto_ack=False)
        print(f"[video_frames] waiting for jobs on {VIDEO_QUEUE}", flush=True)
        self._channel.start_consuming()


if __name__ == "__main__":
    VideoFramesWorker().run()
