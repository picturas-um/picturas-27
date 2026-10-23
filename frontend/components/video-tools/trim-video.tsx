
"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSession } from "@/providers/session-provider";
import { fetchProject } from "@/lib/projects";
import { api } from "@/lib/axios";

export default function TrimVideo() {
  const searchParams = useSearchParams();
  const session = useSession();
  const projectId = searchParams.get("pid");
  const ownerId = searchParams.get("owner");
  const shareId = searchParams.get("share");
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState("");
  const [duration, setDuration] = useState(0);
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(0);
  const [previewing, setPreviewing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState("");

  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl);
    };
  }, [videoUrl]);

  function handleFile(file?: File) {
    if (!file) return;

    if (!file.type.startsWith("video/")) {
      alert("Please select a video file.");
      return;
    }

    setVideoFile(file);
    setVideoUrl(URL.createObjectURL(file));
    setDuration(0);
    setStart(0);
    setEnd(0);
    setPreviewing(false);
    setProgress("");
  }

  function preview() {
    const video = videoRef.current;
    if (!video || end - start < 1) return;

    video.currentTime = start;
    setPreviewing(true);
    void video.play().catch(() => setPreviewing(false));
  }

  function stopPreview() {
    const video = videoRef.current;
    if (!video) return;

    if (video.currentTime >= end) {
      video.pause();
      setPreviewing(false);
    }
  }

  
async function saveVideoToProject(blob: Blob) {
  if (!projectId) {
    throw new Error(
      "Project ID is missing. Open Trim Video from a PictuRAS project."
    );
  }

  setProgress("Getting current project information...");

  const project = await fetchProject(
    session.user._id,
    projectId,
    session.token,
    ownerId ?? undefined,
    shareId ?? undefined
  );

  const formData = new FormData();

  formData.append(
    "video",
    new File([blob], "trimmed-video.mp4", {
      type: "video/mp4",
    })
  );

  setProgress("Saving video to PictuRAS...");

  const query = new URLSearchParams();

  if (shareId) {
    if (ownerId) query.set("owner", ownerId);
    query.set("share", shareId);
  }

  const queryString = query.toString();
  const url = `/projects/${session.user._id}/${projectId}/video${
    queryString ? `?${queryString}` : ""
  }`;

  const response = await api.post(url, formData, {
    headers: {
      Authorization: `Bearer ${session.token}`,
      "X-Project-Version": String(project.version),
    },
  });

  if (response.status !== 204) {
    throw new Error("Failed to save video to project.");
  }

  setProgress("Video saved to PictuRAS successfully!");
}

  async function trimAndDownload(saveToProject = false) {
    if (!videoFile || end - start < 1 || processing) return;

    setProcessing(true);
    setProgress("Loading video processor...");

    try {
      const { FFmpeg } = await import("@ffmpeg/ffmpeg");
      const { fetchFile, toBlobURL } = await import("@ffmpeg/util");

      const ffmpeg = new FFmpeg();

      const baseURL =
        "https://unpkg.com/@ffmpeg/core@0.12.10/dist/umd";

      await ffmpeg.load({
        coreURL: await toBlobURL(
          `${baseURL}/ffmpeg-core.js`,
          "text/javascript"
        ),
        wasmURL: await toBlobURL(
          `${baseURL}/ffmpeg-core.wasm`,
          "application/wasm"
        ),
      });

      setProgress("Trimming video...");

      await ffmpeg.writeFile("input.mp4", await fetchFile(videoFile));

      const result = await ffmpeg.exec([
        "-i",
        "input.mp4",
        "-ss",
        start.toString(),
        "-t",
        (end - start).toString(),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "output.mp4",
      ]);

      if (result !== 0) {
        throw new Error("FFmpeg could not process this video.");
      }

      const data = await ffmpeg.readFile("output.mp4");

      if (!(data instanceof Uint8Array)) {
        throw new Error("Invalid video output.");
      }

      const outputBytes = new Uint8Array(data.byteLength);
      outputBytes.set(data);

      const blob = new Blob([outputBytes], {
        type: "video/mp4",
      });

      if (saveToProject) {
  await saveVideoToProject(blob);
} else {
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = downloadUrl;
  link.download = "trimmed-video.mp4";

  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(downloadUrl), 60000);

  setProgress("Video trimmed and downloaded successfully!");
}
      ffmpeg.terminate();
    } catch (error) {
      console.error(error);
      setProgress("Trimming failed. Check the browser console.");
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-6">
      <h2 className="text-2xl font-bold">Trim Video</h2>

      <input
        type="file"
        accept="video/*"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />

      {videoUrl && (
        <>
          <video
            ref={videoRef}
            src={videoUrl}
            controls
            className="w-full rounded-lg bg-black"
            onLoadedMetadata={(e) => {
              const seconds = e.currentTarget.duration;
              if (!Number.isFinite(seconds)) return;
              setDuration(seconds);
              setStart(0);
              setEnd(seconds);
            }}
            onTimeUpdate={() => {
              if (previewing) stopPreview();
            }}
            onEnded={() => setPreviewing(false)}
          />

          <div className="space-y-3">
            <label className="block">
              Start: {start.toFixed(1)} seconds
              <input
                className="w-full"
                type="range"
                min={0}
                max={duration}
                step={0.1}
                value={start}
                onChange={(e) =>
                  setStart(Math.min(Number(e.target.value), end))
                }
              />
            </label>

            <label className="block">
              End: {end.toFixed(1)} seconds
              <input
                className="w-full"
                type="range"
                min={0}
                max={duration}
                step={0.1}
                value={end}
                onChange={(e) =>
                  setEnd(Math.max(Number(e.target.value), start))
                }
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label>
                Start time (seconds)
                <input
                className="w-full rounded border p-2 bg-white text-black"
                type="number"
                onFocus={(e) => e.target.select()}
                min={0}
                max={duration}
                step={0.1}
                value={start}
                onChange={(e) => {
                  const newStart = Math.max(
                    0,
                    Math.min(Number(e.target.value), duration)
                  );
                  setStart(newStart);
                  if (newStart > end) {
                    setEnd(newStart);
                  }
                }}
              />
              </label>

              <label>
                End time (seconds)
                <input
                className="w-full rounded border p-2 bg-white text-black"
                type="number"
                onFocus={(e) => e.target.select()}
                min={0}
                max={duration}
                step={0.1}
                value={end}
                onChange={(e) => {
                  const newEnd = Math.max(
                    0,
                    Math.min(Number(e.target.value), duration)
                  );
                  setEnd(newEnd);
                  if (newEnd < start) {
                    setStart(newEnd);
                  }
                }}
              />
              </label>
            </div>

            <p>
              Selected duration: {(end - start).toFixed(1)} seconds
            </p>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={preview}
                disabled={end - start < 1 || processing}
                className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
              >
                Preview Selection
              </button>

              <button
                type="button"
                onClick={() => trimAndDownload(false)}
                disabled={end - start < 1 || processing}
                className="rounded bg-green-600 px-4 py-2 text-white disabled:opacity-50"
              >
                {processing ? "Processing..." : "Trim & Download"}
              </button>
              <button
              type="button"
              onClick={() => trimAndDownload(true)}
              disabled={end - start < 1 || processing || !projectId}
              className="rounded bg-purple-600 px-4 py-2 text-white disabled:opacity-50"
            >
              {processing ? "Processing..." : "Trim & Save to Project"}
            </button>
            </div>

            {progress && <p>{progress}</p>}

            {end - start < 1 && (
              <p className="text-red-500">
                Select at least 1 second of video.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
