"""PictuRAS video microservice (RabbitMQ worker).

Receives the video and the whole effect pipeline in a single message (DA-01),
processes it with video_processor and replies to the projects orchestrator on
project_queue. Progress is sent straight to the WebSocket gateway (ws_queue),
as a percentage (REQ-VID-STATUS-002).

Unlike the image tools, the message is only acknowledged after the job ends:
if the worker dies midway, RabbitMQ redelivers it (DA-03, REQ-VID-FAIL-004).
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
from effects import UnsupportedEffect
from video_processor import InvalidSpeed, InvalidTrim, InvalidVideo, process_video

EXCHANGE = "picturas"
VIDEO_QUEUE = "video_queue"
PROJECT_QUEUE = "project_queue"
WS_QUEUE = "ws_queue"
MICROSERVICE = "picturas-video-tool-ms"

CODES = {
    "wrong_procedure": 2000,
    "error_processing": 2001,
    "unsupported_effect": 2002,
    "invalid_trim": 2003,
    "invalid_video": 2004,
    "invalid_speed": 2005,
}


def now():
    return datetime.datetime.now(pytz.utc)


class VideoWorker:
    def __init__(self):
        self._connection = self._connect()
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=EXCHANGE,
                                       exchange_type=ExchangeType.direct, durable=True)
        self._channel.queue_declare(queue=VIDEO_QUEUE, durable=True)
        self._channel.queue_bind(queue=VIDEO_QUEUE, exchange=EXCHANGE, routing_key=VIDEO_QUEUE)
        # one video at a time per replica; parallelism comes from replicas
        self._channel.basic_qos(prefetch_count=1)

    @staticmethod
    def _connect():
        credentials = pika.PlainCredentials(env.RABBITMQ_USERNAME, env.RABBITMQ_PASSWORD)
        params = pika.ConnectionParameters(
            env.RABBITMQ_HOST, int(env.RABBITMQ_PORT), "/", credentials,
            # processing a video blocks this thread for minutes; without a
            # heartbeat the broker does not drop the connection midway (MVP, DA-08)
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
        self._publish(PROJECT_QUEUE, {
            "messageId": f"video-{uuid.uuid4()}",
            "correlationId": msg_id,
            "timestamp": now().isoformat(),
            "status": "success",
            "output": {"type": "video", "imageURI": output_uri},
            "metadata": {
                "processingTime": (now() - started).total_seconds() * 1000,
                "microservice": MICROSERVICE,
                "video": video_info,
            },
        })

    def _reply_error(self, msg_id, started, code, message, input_uri):
        self._publish(PROJECT_QUEUE, {
            "messageId": f"video-{uuid.uuid4()}",
            "correlationId": msg_id,
            "timestamp": now().isoformat(),
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "msg": message,  # the orchestrator reads error.msg
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
        info = {}
        try:
            info = json.loads(body.decode())
            msg_id = info["messageId"]
            params = info["parameters"]
            input_uri = params["inputImageURI"]
            output_uri = params["outputImageURI"]
            tools = params.get("tools") or []
            preview = bool(params.get("preview"))
            progress = params.get("progress") or {}
        except (ValueError, KeyError) as e:
            print(f"[video] invalid message discarded: {e}", flush=True)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        print(f"[video] msg={msg_id} preview={preview} tools={[t.get('procedure') for t in tools]}",
              flush=True)

        if info.get("procedure") != "video":
            self._reply_error(msg_id, started, CODES["wrong_procedure"],
                              "The procedure received does not fit into this tool", input_uri)
        else:
            try:
                result = process_video(
                    input_uri, output_uri, tools, preview=preview,
                    progress_cb=lambda pct: self._progress(progress, preview, pct),
                )
                self._reply_success(msg_id, started, output_uri, result)
                print(f"[video] msg={msg_id} ok frames={result['frames']} "
                      f"t={(now() - started).total_seconds():.1f}s", flush=True)
            except UnsupportedEffect as e:
                self._reply_error(msg_id, started, CODES["unsupported_effect"], str(e), input_uri)
            except InvalidTrim as e:
                self._reply_error(msg_id, started, CODES["invalid_trim"], str(e), input_uri)
            except InvalidSpeed as e:
                self._reply_error(msg_id, started, CODES["invalid_speed"], str(e), input_uri)
            except InvalidVideo as e:
                self._reply_error(msg_id, started, CODES["invalid_video"], str(e), input_uri)
            except Exception as e:  # noqa: BLE001 - any other failure is reported
                self._reply_error(msg_id, started, CODES["error_processing"], str(e), input_uri)

        # manual ack only at the end (DA-03)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        self._channel.basic_consume(queue=VIDEO_QUEUE, on_message_callback=self.callback,
                                    auto_ack=False)
        print("[video] waiting for jobs on video_queue", flush=True)
        self._channel.start_consuming()


if __name__ == "__main__":
    VideoWorker().run()
