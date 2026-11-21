"""Identical behavioral assertions for both selected source revisions."""

import hashlib
import io
import json
import math
import os
import struct
import subprocess
import sys
import wave
from array import array
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageChops, ImageEnhance, ImageOps, ImageStat

sys.path.insert(0, str(Path(__file__).parent))
from adapters import selected_adapter


INPUTS = Path("/inputs")
EVIDENCE = Path("/evidence")
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def media(name: str) -> Path:
    path = INPUTS / name
    assert _hash(path) == CASES["inputs"][name], f"Fixture hash mismatch: {name}"
    return path


def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json",
                             "-show_format", "-show_streams", str(path)],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def duration(data: dict) -> float:
    return float(data["format"]["duration"])


def streams(data: dict, kind: str) -> list[dict]:
    return [item for item in data["streams"] if item.get("codec_type") == kind]


def frame(path: Path, second: float) -> Image.Image:
    result = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(second), "-i", str(path),
                             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                            capture_output=True, check=True)
    return Image.open(io.BytesIO(result.stdout)).convert("RGB")


def difference(a: Image.Image, b: Image.Image) -> float:
    assert a.size == b.size
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def save(name: str, **values) -> None:
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / f"{name}.json").write_text(json.dumps(values, indent=2, default=str) + "\n")


def test_vf01_effect_order():
    """Brightness then threshold differs from threshold then brightness, at equal dimensions."""
    source = media("sample_6s.mov")
    output = EVIDENCE / "vf01.mp4"
    tools = [{"procedure": "brightness", "params": {"brightness": 0.5}},
             {"procedure": "binarization", "params": {"threshold": 128}}]
    result = selected_adapter().execute(source, output, tools)
    before, after = frame(source, 1), frame(output, 1)
    expected = ImageOps.grayscale(ImageEnhance.Brightness(before).enhance(0.5)).point(
        lambda value: 0 if value < 128 else 255).convert("RGB")
    reversed_order = ImageEnhance.Brightness(ImageOps.grayscale(before).point(
        lambda value: 0 if value < 128 else 255).convert("RGB")).enhance(0.5)
    expected_error, reversed_error = difference(after, expected), difference(after, reversed_order)
    save("vf01", result=result, expected_mae=expected_error, reversed_mae=reversed_error,
         input_sha256=_hash(source))
    assert difference(expected, reversed_order) > 20
    assert expected_error < 20
    assert expected_error + 10 < reversed_error
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf02_trim_speed():
    source = media("sample_10s_720p.mp4")
    output = EVIDENCE / "vf02.mp4"
    tools = [{"procedure": "trim", "params": {"start": 1, "end": 4}},
             {"procedure": "speed", "params": {"factor": 2}}]
    result = selected_adapter().execute(source, output, tools)
    data = probe(output)
    save("vf02", result=result, ffprobe=data, input_sha256=_hash(source))
    assert duration(data) == pytest.approx(1.5, abs=0.20)
    assert streams(data, "audio")
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf03_output_streams():
    source = media("sample_10s_720p.mp4")
    output = EVIDENCE / "vf03.mp4"
    result = selected_adapter().execute(source, output,
                                        [{"procedure": "saturation", "params": {"saturationFactor": 0}}])
    data = probe(output)
    video, audio = streams(data, "video"), streams(data, "audio")
    save("vf03", result=result, ffprobe=data, input_sha256=_hash(source))
    assert "mp4" in data["format"]["format_name"]
    assert len(video) == 1 and video[0]["codec_name"] == "h264"
    assert len(audio) == 1 and audio[0]["codec_name"] == "aac"
    assert abs(float(video[0].get("duration", duration(data))) -
               float(audio[0].get("duration", duration(data)))) <= 0.25


def test_vf04_audio_visual_sync():
    """A flash and a beep at 1 s must stay aligned after trim and 2x speed."""
    EVIDENCE.mkdir(exist_ok=True)
    raw_video = EVIDENCE / "vf04-source.rgb"
    raw_audio = EVIDENCE / "vf04-source.wav"
    source = EVIDENCE / "vf04-source.mp4"
    output = EVIDENCE / "vf04-output.mp4"
    width, height, fps, seconds, sample_rate = 160, 120, 25, 3, 16000
    with raw_video.open("wb") as handle:
        for index in range(fps * seconds):
            level = 255 if fps <= index < fps + 4 else 0
            handle.write(bytes([level]) * (width * height * 3))
    with wave.open(str(raw_audio), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        samples = [int(12000 * math.sin(2 * math.pi * 1000 * index / sample_rate))
                   if sample_rate <= index < sample_rate + int(0.16 * sample_rate) else 0
                   for index in range(sample_rate * seconds)]
        handle.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                    "-s", f"{width}x{height}", "-r", str(fps), "-i", str(raw_video),
                    "-i", str(raw_audio), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-map_metadata", "-1", str(source)], check=True)
    source_hash = _hash(source)
    tools = [{"procedure": "trim", "params": {"start": 0.5, "end": 2.5}},
             {"procedure": "speed", "params": {"factor": 2}}]
    result = selected_adapter().execute(source, output, tools)
    data = probe(output)
    decoded_video = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output),
                                    "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                                   capture_output=True, check=True).stdout
    frame_bytes = width * height
    bright_frames = [index for index in range(len(decoded_video) // frame_bytes)
                     if sum(decoded_video[index * frame_bytes:(index + 1) * frame_bytes]) / frame_bytes > 128]
    decoded_audio = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output),
                                    "-map", "0:a:0", "-ac", "1", "-ar", str(sample_rate),
                                    "-f", "s16le", "-acodec", "pcm_s16le", "-"],
                                   capture_output=True, check=True).stdout
    values = array("h")
    values.frombytes(decoded_audio)
    window = sample_rate // 50
    active_windows = [index for index in range(len(values) // window)
                      if max(abs(value) for value in values[index * window:(index + 1) * window]) > 1500]
    visual_time = bright_frames[0] / fps if bright_frames else None
    audio_time = active_windows[0] / 50 if active_windows else None
    save("vf04", result=result, generated_input_sha256=source_hash, ffprobe=data,
         visual_marker_seconds=visual_time, audio_marker_seconds=audio_time,
         generator="rawvideo-25fps-pcm16k-marker-v1")
    assert bright_frames and active_windows
    assert duration(data) == pytest.approx(1.0, abs=0.20)
    assert visual_time == pytest.approx(0.25, abs=0.12)
    assert audio_time == pytest.approx(0.25, abs=0.12)
    assert abs(visual_time - audio_time) <= 0.12
    assert _hash(source) == source_hash


def test_vf05_video_preview():
    source = media("sample_6s.mov")
    output = EVIDENCE / "vf05.mp4"
    result = selected_adapter().execute(source, output,
                                        [{"procedure": "rotate", "params": {"degrees": 180}}], preview=True)
    data = probe(output)
    save("vf05", result=result, ffprobe=data, input_sha256=_hash(source))
    assert duration(data) == pytest.approx(3, abs=0.20)
    assert streams(data, "video")[0]["codec_name"] == "h264"
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf06_frame_extraction():
    source = media("sample_6s.mov")
    output = EVIDENCE / "vf06.mp4"
    result = selected_adapter().execute(source, output,
                                        [{"procedure": "extract_frames", "params": {"count": 4, "format": "png"}}])
    records = result.get("frames", [])
    save("vf06", result=result, input_sha256=_hash(source))
    assert result["output_type"] == "frames"
    assert len(records) == 4 and len({item["file"] for item in records}) == 4
    for item, expected in zip(records, (0, 1.5, 3, 4.5)):
        assert item["time"] == pytest.approx(expected, abs=0.08)
        with Image.open(item["file"]) as image:
            assert image.format == "PNG" and image.size == (result["width"], result["height"])
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf06_jpeg_and_preview():
    source = media("sample_6s.mov")
    adapter = selected_adapter()
    jpeg = adapter.execute(source, EVIDENCE / "vf06-jpeg.mp4",
                           [{"procedure": "extract_frames", "params": {"count": 4, "format": "jpeg"}}])
    preview = adapter.execute(source, EVIDENCE / "vf06-preview.mp4",
                              [{"procedure": "extract_frames", "params": {"count": 12}}], preview=True)
    save("vf06-variants", jpeg=jpeg, preview=preview, input_sha256=_hash(source))
    assert jpeg["output_type"] == "frames" and len(jpeg["frames"]) == 4
    for item in jpeg["frames"]:
        with Image.open(item["file"]) as image:
            assert image.format == "JPEG" and image.size == (jpeg["width"], jpeg["height"])
    assert preview["output_type"] == "image" and preview["frames"] == 6
    with Image.open(preview["output_path"]) as image:
        assert image.format == "PNG" and image.size == (1152, 480)
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf07_composed_extraction():
    source = media("sample_6s.mov")
    output = EVIDENCE / "vf07.mp4"
    tools = [{"procedure": "trim", "params": {"start": 1, "end": 3}},
             {"procedure": "brightness", "params": {"brightness": 0.3}},
             {"procedure": "resize", "params": {"width": 80, "height": 60}},
             {"procedure": "extract_frames", "params": {"count": 2, "format": "png"}}]
    result = selected_adapter().execute(source, output, tools)
    save("vf07", result=result, pipeline=tools, input_sha256=_hash(source))
    assert result["output_type"] == "frames"
    assert result["duration"] == pytest.approx(2, abs=0.20)
    assert [item["time"] for item in result["frames"]] == pytest.approx([0, 1], abs=0.08)
    for item in result["frames"]:
        with Image.open(item["file"]) as image:
            assert image.size == (80, 60)
            assert sum(ImageStat.Stat(image.convert("RGB")).mean) / 3 < 85
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf07_effect_before_extraction():
    source = media("sample_6s.mov")
    tools = [{"procedure": "trim", "params": {"start": 1, "end": 3}},
             {"procedure": "brightness", "params": {"brightness": 0.3}},
             {"procedure": "resize", "params": {"width": 80, "height": 60}},
             {"procedure": "extract_frames", "params": {"count": 2, "format": "png"}}]
    result = selected_adapter().execute(source, EVIDENCE / "vf07-effect.mp4", tools)
    with Image.open(result["frames"][0]["file"]) as image:
        mean = sum(ImageStat.Stat(image.convert("RGB")).mean) / 3
    save("vf07-effect", result=result, mean_brightness=mean, input_sha256=_hash(source))
    assert mean < 85


def test_vf09_invalid_input():
    source = media("corrupted.mp4")
    output = EVIDENCE / "vf09.mp4"
    try:
        selected_adapter().execute(source, output,
                                   [{"procedure": "brightness", "params": {"brightness": 1.2}}])
    except Exception as error:
        save("vf09", error_type=type(error).__name__, error=str(error), input_sha256=_hash(source))
        assert type(error).__name__ == "InvalidVideo"
    else:
        pytest.fail("Corrupted video was accepted")
    assert not output.exists() and not Path(str(output) + ".part.mp4").exists()


def test_vf09_invalid_trim_and_speed():
    source = media("sample_6s.mov")
    adapter = selected_adapter()
    cases = [("trim", {"start": 4, "end": 2}, "InvalidTrim"),
             ("speed", {"factor": 6}, "InvalidSpeed")]
    observed = []
    for name, params, expected in cases:
        output = EVIDENCE / f"vf09-{name}.mp4"
        try:
            adapter.execute(source, output, [{"procedure": name, "params": params}])
        except Exception as error:
            observed.append({"case": name, "type": type(error).__name__, "message": str(error)})
            assert type(error).__name__ == expected
        else:
            pytest.fail(f"Invalid {name} parameters were accepted")
        assert not output.exists() and not Path(str(output) + ".part.mp4").exists()
    save("vf09-parameters", observed=observed, input_sha256=_hash(source))


def test_vf09_extraction_must_be_terminal():
    source = media("sample_6s.mov")
    output = EVIDENCE / "vf09-extraction.mp4"
    tools = [{"procedure": "extract_frames", "params": {"count": 2}},
             {"procedure": "brightness", "params": {"brightness": 0.8}}]
    try:
        selected_adapter().execute(source, output, tools)
    except Exception as error:
        save("vf09-extraction", error_type=type(error).__name__, error=str(error), input_sha256=_hash(source))
        assert type(error).__name__ == "InvalidExtraction"
    else:
        pytest.fail("Non-terminal frame extraction was accepted")
    assert not output.exists()


def test_vf08_deterministic_subtitles(monkeypatch):
    source = media("sample_6s.mov")
    import subtitles

    class Recognizer:
        def transcribe(self, path, **options):
            assert options["language"] is None and options["task"] == "transcribe"
            return iter([SimpleNamespace(start=0.3, end=2.0,
                                         text="Hello from PictuRAS")]), None

    monkeypatch.setattr(subtitles, "speech_model", Recognizer)
    output = EVIDENCE / "vf08.mp4"
    result = selected_adapter().execute(
        source, output, [{"procedure": "subtitles", "params": {}}])
    data = probe(output)
    before, after = frame(source, 1), frame(output, 1)
    width, height = before.size
    region = (int(width * 0.1), int(height * 0.7), int(width * 0.9), int(height * 0.97))
    visual_difference = difference(before.crop(region), after.crop(region))
    save("vf08", result=result, ffprobe=data, caption_region_mae=visual_difference,
         recognizer="deterministic-stub-v1", input_sha256=_hash(source))
    assert duration(data) == pytest.approx(6, abs=0.20)
    assert streams(data, "video")[0]["codec_name"] == "h264"
    assert streams(data, "audio")
    assert visual_difference > 3
    assert _hash(source) == CASES["inputs"][source.name]


def test_vf10_worker_message_and_progress():
    source = media("sample_6s.mov")
    output = EVIDENCE / "vf10.mp4"
    observed = selected_adapter().invoke_worker(
        source, output, [{"procedure": "brightness", "params": {"brightness": 1.1}}])
    replies = [entry["body"] for entry in observed["messages"] if entry["queue"] == "project_queue"]
    progress = [entry["body"] for entry in observed["messages"] if entry["queue"] == "ws_queue"]
    save("vf10", observed=observed, input_sha256=_hash(source))
    assert observed["acks"] == [7]
    assert len(replies) == 1
    assert replies[0]["status"] == "success"
    assert replies[0]["correlationId"] == "m4-vf10-request"
    assert replies[0]["output"]["type"] == "video"
    assert replies[0]["output"]["imageURI"] == str(output)
    assert output.is_file() and streams(probe(output), "video")
    values = [item["percent"] for item in progress]
    assert values and values == sorted(values) and values[-1] == 100
    assert all(0 <= value <= 100 for value in values)
    assert all(item["projectId"] == "m4-project" and item["imgId"] == "m4-video"
               for item in progress)


def test_vf11_prepare_worker_manifest():
    source = media("sample_6s.mov")
    observed = selected_adapter().invoke_worker(
        source, EVIDENCE / "vf11.mp4",
        [{"procedure": "extract_frames", "params": {"count": 3, "format": "png"}}],
        message_id="m4-vf11-request")
    replies = [entry["body"] for entry in observed["messages"] if entry["queue"] == "project_queue"]
    save("vf11-worker", observed=observed, input_sha256=_hash(source))
    assert observed["acks"] == [7] and len(replies) == 1
    assert replies[0]["status"] == "success"
    assert replies[0]["correlationId"] == "m4-vf11-request"
    assert replies[0]["output"]["type"] == "frames"
    assert len(replies[0]["output"]["frames"]) == 3
    (EVIDENCE / "vf11-reply.json").write_text(json.dumps(replies[0], indent=2) + "\n")


def test_vf11_verify_persisted_results():
    reply = json.loads((EVIDENCE / "vf11-reply.json").read_text())
    persisted = json.loads((EVIDENCE / "vf11-persisted.json").read_text())
    output = reply["output"]
    created = persisted["created"]
    uploaded = persisted["uploaded"]
    save("vf11-verification", reply=reply, persisted=persisted)
    assert persisted["status"] == "success"
    assert len(output["frames"]) == len(created) == len(uploaded) == 3
    assert len({item["_id"] for item in created}) == 3
    assert len({item["file_name"] for item in created}) == 3
    assert all(item["img_id"] == "m4-video" and item["project_id"] == "m4-project"
               and item["type"] == "image" for item in created)
    assert all(item["file_name"].startswith("m4-video-") for item in created)
    assert all(Path(entry["file"]).is_file() for entry in output["frames"])
