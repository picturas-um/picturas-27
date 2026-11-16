"""Automated tests for video_frames microservice."""
from pathlib import Path
import hashlib
import subprocess

import pytest
from PIL import Image

import frame_extraction
from frame_extraction import InvalidExtraction, sampling_times, validate_params, process_video


def tool(**params):
    return {"procedure": "extract_frames", "params": params}


@pytest.mark.parametrize("fmt,extension", [("png", ".png"), ("jpeg", ".jpg")])
def test_count_images_and_original_preserved(sample_video, tmp_path, fmt, extension):
    source_hash = hashlib.sha256(Path(sample_video).read_bytes()).hexdigest()
    progress = []
    result = process_video(sample_video, str(tmp_path / "result.mp4"),
                           [tool(count=4, format=fmt)], progress.append)
    assert result["output_type"] == "frames"
    assert [f["time"] for f in result["frames"]] == pytest.approx([0, 1, 2, 3], abs=0.05)
    for frame in result["frames"]:
        path = Path(frame["file"])
        assert path.parent == Path(result["output_path"])
        assert path.suffix == extension
        with Image.open(path) as image:
            assert image.size == (320, 240)
            assert image.format == ("PNG" if fmt == "png" else "JPEG")
    assert len({f["file"] for f in result["frames"]}) == 4
    assert hashlib.sha256(Path(sample_video).read_bytes()).hexdigest() == source_hash
    assert progress[-1] == 100 and progress == sorted(progress)
    assert not list(tmp_path.glob("extract-*"))
    assert not list(tmp_path.glob("frame-source-*"))


def test_interval_sampling(sample_video, tmp_path):
    result = process_video(sample_video, str(tmp_path / "result.mp4"),
                           [tool(mode="interval", interval=1.5)])
    assert [f["time"] for f in result["frames"]] == pytest.approx([0, 1.5, 3])


def test_preview_contact_sheet(sample_video, tmp_path):
    result = process_video(sample_video, str(tmp_path / "preview.mp4"),
                           [tool(count=12)], preview=True)
    assert result["output_type"] == "image"
    preview_file = Path(result["output_path"])
    assert preview_file.is_file()
    with Image.open(preview_file) as sheet:
        assert sheet.format == "PNG"
        assert sheet.width > 0 and sheet.height > 0


@pytest.mark.parametrize("tools", [[tool(), {"procedure": "rotate"}], [tool(), tool()]])
def test_extraction_must_be_terminal_once(sample_video, tmp_path, tools):
    with pytest.raises(InvalidExtraction, match="once"):
        process_video(sample_video, str(tmp_path / "result.mp4"), tools)


@pytest.mark.parametrize("params", [None, False, [], "count"])
def test_invalid_parameter_container(params):
    with pytest.raises(InvalidExtraction):
        validate_params(params)


@pytest.mark.parametrize("fmt", ["png", "jpeg"])
def test_extraction_only_seeks_original_without_transcoding(silent_video, tmp_path, fmt):
    result = process_video(silent_video, str(tmp_path / "result.mp4"),
                           [tool(count=100, format=fmt)])
    assert result["output_type"] == "frames"
    assert len(result["frames"]) == 100
    assert result["frames"][-1]["time"] < result["duration"]
    for frame in result["frames"]:
        with Image.open(frame["file"]) as image:
            assert image.format == ("PNG" if fmt == "png" else "JPEG")
    assert not list(tmp_path.glob("frame-source-*"))


def test_extraction_uses_video_duration_when_audio_is_longer(sample_video, tmp_path):
    source = tmp_path / "long-audio.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-i", sample_video,
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", "8", "-c:v", "copy", "-c:a", "aac",
                    "-map", "0:v:0", "-map", "1:a:0",
                    str(source)], check=True)
    result = process_video(str(source), str(tmp_path / "result.mp4"),
                           [tool(mode="interval", interval=2)])
    assert [f["time"] for f in result["frames"]] == pytest.approx([0, 2])


def test_excessive_intervals_rejected(sample_video, tmp_path):
    with pytest.raises(InvalidExtraction, match="more than 100 frames"):
        process_video(sample_video, str(tmp_path / "result.mp4"),
                      [tool(mode="interval", interval=0.01)])


def test_unreadable_video_fails(tmp_path):
    bad = tmp_path / "corrupted.mp4"
    bad.write_bytes(b"not a video file")
    with pytest.raises(frame_extraction.InvalidVideo):
        process_video(str(bad), str(tmp_path / "result.mp4"), [tool(count=1)])
