"""Local speech recognition and burned-in captions for video_subtitles microservice.

The Whisper model is loaded lazily and cached on a Docker volume.
No speech/audio is a successful no-op; model or encoder failures are errors.
"""
import json
import math
import os
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import tempfile

PREVIEW_SECONDS = float(os.getenv("VIDEO_PREVIEW_SECONDS", "3"))


class InvalidVideo(Exception):
    """File is not a readable video (corrupted, no video stream, ...)."""


@lru_cache(maxsize=1)
def speech_model():
    from faster_whisper import WhisperModel
    return WhisperModel(
        os.getenv("WHISPER_MODEL", "small"), device="cpu", compute_type="int8",
        cpu_threads=int(os.getenv("WHISPER_CPU_THREADS", "2")),
        download_root=os.getenv("WHISPER_CACHE_DIR", "/models/whisper"),
    )


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def write_captions(segments, path, duration, progress):
    """Bound timestamps and strip markup so recognition cannot inject ASS styles."""
    count = 0
    with open(path, "w", encoding="utf-8") as captions:
        for segment in segments:
            if not math.isfinite(segment.start) or not math.isfinite(segment.end):
                raise ValueError("Speech recognition returned invalid timestamps")
            start, end = max(0, segment.start), min(duration, segment.end)
            text = " ".join(segment.text.split())
            for char in "<>{}\\":
                text = text.replace(char, "")
            if not text or end <= start:
                continue
            count += 1
            captions.write(f"{count}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n\n")
            progress(min(80, int(end / duration * 80)))
    return count


def probe(path: str) -> dict:
    """Reads video characteristics with ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise InvalidVideo(f"Unreadable video file: {res.stderr.strip()[:200]}")

    data = json.loads(res.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        raise InvalidVideo("The file has no video stream")

    fmt = data.get("format", {})
    duration = float(video.get("duration") or fmt.get("duration") or 0)
    if duration <= 0:
        raise InvalidVideo("Could not determine the video duration")

    fps_str = video.get("avg_frame_rate") or video.get("r_frame_rate") or "25/1"
    try:
        fps = float(Fraction(fps_str))
    except (ZeroDivisionError, ValueError):
        fps = 25.0

    return {
        "duration": duration,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": fps,
        "fps_str": fps_str,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name") if audio else None,
        "has_audio": audio is not None,
        "format_name": fmt.get("format_name"),
        "size_bytes": int(fmt.get("size") or os.path.getsize(path)),
    }


def caption_video(input_path, output_path, info, progress):
    if not info["has_audio"]:
        shutil.copyfile(input_path, output_path)
        progress(100)
        return

    with tempfile.TemporaryDirectory(prefix="speech-", dir=Path(output_path).parent) as work:
        segments, _ = speech_model().transcribe(
            input_path, task="transcribe", language=None, beam_size=5,
            vad_filter=True, condition_on_previous_text=False,
        )
        captions = Path(work) / "captions.srt"
        if not write_captions(segments, captions, info["duration"], progress):
            shutil.copyfile(input_path, output_path)
            progress(100)
            return

        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", str(Path(input_path).resolve()),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", "subtitles=captions.srt:force_style='FontName=DejaVu Sans,FontSize=20,Outline=1,MarginV=16'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
            str(Path(output_path).resolve()),
        ]
        result = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=1800)
        if result.returncode:
            raise RuntimeError(f"Could not render subtitles: {result.stderr[-500:]}")
        progress(100)


def process_video(input_path: str, output_path: str, tools=None,
                  progress_cb=None, preview: bool = False) -> dict:
    info = probe(input_path)
    target = Path(output_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="captions-", dir=target.parent) as work:
        work_path = Path(work)
        current_input = input_path

        if preview and info["duration"] > PREVIEW_SECONDS:
            preview_cut = str(work_path / "preview_cut.mp4")
            cmd = [
                "ffmpeg", "-y", "-v", "error",
                "-ss", "0", "-t", f"{PREVIEW_SECONDS:.3f}",
                "-i", input_path, "-c", "copy", "-movflags", "+faststart",
                preview_cut,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                current_input = preview_cut
                info = probe(current_input)

        tmp_out = str(work_path / "subtitled.mp4")
        caption_video(current_input, tmp_out, info, progress_cb or (lambda _: None))
        os.replace(tmp_out, str(target))

    result = probe(str(target))
    result["frames"] = round(result["duration"] * result["fps"])
    return result
