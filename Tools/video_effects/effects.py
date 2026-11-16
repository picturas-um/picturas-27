"""Video effects and FFmpeg pipeline for video_effects microservice.

Applies PIL frame effects, temporal adjustments (trim, speed), and encodes once
to MP4/H.264 + AAC, keeping audio in sync.
"""
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageEnhance, ImageOps

PREVIEW_SECONDS = float(os.getenv("VIDEO_PREVIEW_SECONDS", "3"))
MIN_SPEED = 0.25
MAX_SPEED = 5.0


class UnsupportedEffect(Exception):
    """Effect is not supported by video_effects."""


class InvalidVideo(Exception):
    """File is not a readable video (corrupted, no video stream, ...)."""


class InvalidTrim(Exception):
    """Trim parameters outside the video duration or with end before start."""


class InvalidSpeed(Exception):
    """Speed factor outside the allowed range or not numeric."""


class ProcessingError(Exception):
    """ffmpeg failure while decoding or encoding."""


def brightness(img: Image.Image, brightness: float) -> Image.Image:
    return ImageEnhance.Brightness(img).enhance(float(brightness))


def contrast(img: Image.Image, contrastFactor: float) -> Image.Image:
    return ImageEnhance.Contrast(img).enhance(float(contrastFactor))


def saturation(img: Image.Image, saturationFactor: float) -> Image.Image:
    return ImageEnhance.Color(img).enhance(float(saturationFactor))


def rotate(img: Image.Image, degrees: float) -> Image.Image:
    return img.rotate(float(degrees), expand=True)


def resize(img: Image.Image, width: int, height: int) -> Image.Image:
    return img.resize((int(width), int(height)))


def binarization(img: Image.Image, threshold: int) -> Image.Image:
    t = int(threshold)
    gray = ImageOps.grayscale(img).point(lambda x: 0 if x < t else 255)
    return gray.convert("RGB")


def cut(img: Image.Image, left: int, top: int, right: int, bottom: int) -> Image.Image:
    return img.crop((int(left), int(top), int(right), int(bottom)))


def border(img: Image.Image, borderWidth: int, r: int, g: int, b: int) -> Image.Image:
    return ImageOps.expand(img, border=int(borderWidth), fill=(int(r), int(g), int(b)))


FRAME_EFFECTS = {
    "brightness": brightness,
    "contrast": contrast,
    "saturation": saturation,
    "rotate": rotate,
    "resize": resize,
    "binarization": binarization,
    "cut": cut,
    "border": border,
}

TIME_EFFECTS = {"trim", "speed"}
SUPPORTED = set(FRAME_EFFECTS) | TIME_EFFECTS


def apply_frame_effects(img: Image.Image, tools: list) -> Image.Image:
    """Applies the frame effects in `tools`, in the given order."""
    for tool in tools:
        name = tool["procedure"]
        if name in TIME_EFFECTS:
            continue
        fn = FRAME_EFFECTS.get(name)
        if fn is None:
            raise UnsupportedEffect(f"Effect '{name}' is not available for video_effects")
        img = fn(img, **(tool.get("params") or {}))
        if img.mode != "RGB":
            img = img.convert("RGB")
    return img


def probe(path: str, prefer_video_duration: bool = False) -> dict:
    """Reads the video characteristics with ffprobe."""
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
    duration = float(
        (video.get("duration") if prefer_video_duration else None)
        or fmt.get("duration") or video.get("duration") or 0
    )
    if duration <= 0:
        raise InvalidVideo("Could not determine the video duration")

    fps_str = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
    try:
        fps = float(Fraction(fps_str))
    except (ZeroDivisionError, ValueError):
        fps = 0.0
    if fps <= 0:
        fps_str, fps = "25/1", 25.0

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


def resolve_trim(tools: list, duration: float) -> tuple:
    start, end = 0.0, float(duration)
    for tool in tools:
        if tool.get("procedure") != "trim":
            continue
        params = tool.get("params") or {}
        try:
            t_start = float(params.get("start", 0))
            t_end = float(params.get("end"))
        except (TypeError, ValueError):
            raise InvalidTrim("Trim requires numeric start and end (seconds)")
        length = end - start
        if t_start < 0 or t_end <= t_start:
            raise InvalidTrim("Trim end must be after its start")
        if t_start >= length or t_end > length + 1e-3:
            raise InvalidTrim(
                f"Trim [{t_start}, {t_end}] s is outside the video duration ({length:.2f} s)"
            )
        start, end = start + t_start, start + min(t_end, length)
    return start, end


def resolve_speed(tools: list) -> float:
    factor = 1.0
    for tool in tools:
        if tool.get("procedure") != "speed":
            continue
        try:
            f = float((tool.get("params") or {}).get("factor"))
        except (TypeError, ValueError):
            raise InvalidSpeed("Speed requires a numeric factor")
        if not MIN_SPEED <= f <= MAX_SPEED:
            raise InvalidSpeed(f"Speed must be between {MIN_SPEED}x and {MAX_SPEED}x (got {f}x)")
        factor *= f
    return factor


def atempo_chain(factor: float) -> str:
    stages = []
    while factor > 2.0:
        stages.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        stages.append(0.5)
        factor /= 0.5
    stages.append(factor)
    return ",".join(f"atempo={s:.6f}" for s in stages)


def validate_tools(tools: list) -> None:
    for tool in tools:
        if tool.get("procedure") not in SUPPORTED:
            raise UnsupportedEffect(
                f"Effect '{tool.get('procedure')}' is not available for video_effects"
            )


def process_video(input_path: str, output_path: str, tools: list,
                  progress_cb=None, preview: bool = False) -> dict:
    validate_tools(tools)
    speed = resolve_speed(tools)
    info = probe(input_path)
    start, end = resolve_trim(tools, info["duration"])
    if preview:
        end = min(end, start + PREVIEW_SECONDS * speed)
    duration = end - start

    w, h = info["width"], info["height"]
    frame_bytes = w * h * 3
    expected_frames = max(1, round(duration / speed * info["fps"]))

    decode_cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
        "-i", input_path, "-map", "0:v:0", "-an",
        "-vf", f"setpts=PTS/{speed:.6f},fps={info['fps_str']}",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tmp_out = output_path + ".part.mp4"
    dec_err = tempfile.TemporaryFile()
    enc_err = tempfile.TemporaryFile()

    try:
        dec = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE, stderr=dec_err)
        enc = None
        frames = 0
        last_pct = -1

        while True:
            raw = dec.stdout.read(frame_bytes)
            if not raw or len(raw) < frame_bytes:
                break

            img = Image.frombytes("RGB", (w, h), raw)
            img = apply_frame_effects(img, tools)

            if enc is None:
                enc = _start_encoder(input_path, tmp_out, img.size, info, start, duration, speed, enc_err)

            enc.stdin.write(img.tobytes())
            frames += 1

            if progress_cb and frames % 10 == 0:
                pct = min(99, int(frames / expected_frames * 100))
                if pct != last_pct:
                    last_pct = pct
                    progress_cb(pct)

        dec.wait()
        if dec.returncode != 0:
            raise ProcessingError(f"ffmpeg decode error: {_read(dec_err)}")

        if enc is not None:
            enc.stdin.close()
            enc.wait()
            if enc.returncode != 0:
                raise ProcessingError(f"ffmpeg encode error: {_read(enc_err)}")

        if frames == 0:
            raise ProcessingError("No frames could be decoded from the video")

        os.replace(tmp_out, output_path)

    except Exception:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        raise
    finally:
        dec_err.close()
        enc_err.close()

    if progress_cb:
        progress_cb(100)

    result = probe(output_path)
    result["frames"] = frames
    return result


def _start_encoder(input_path, out_path, size, info, start, duration, speed, err_file):
    ow, oh = size
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}",
        "-r", info["fps_str"], "-i", "-",
    ]
    if info["has_audio"]:
        cmd += ["-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", input_path,
                "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k"]
        if abs(speed - 1.0) > 1e-6:
            cmd += ["-af", atempo_chain(speed)]
    else:
        cmd += ["-map", "0:v:0"]
    cmd += [
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-shortest", "-f", "mp4", out_path,
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err_file)


def _read(f) -> str:
    f.seek(0)
    return f.read().decode(errors="replace").strip()[-500:]
