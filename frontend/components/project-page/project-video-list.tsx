
"use client";

import { useState } from "react";
import type { SingleProject } from "@/lib/projects";

type SavedVideo = NonNullable<SingleProject["videos"]>[number];

export function ProjectVideoList({
  videos,
  onRefresh,
}: {
  videos: SavedVideo[];
  onRefresh?: () => Promise<unknown>;
}) {
  const [refreshing, setRefreshing] = useState(false);

  const refreshLinks = async () => {
    if (!onRefresh) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  if (videos.length === 0) return null;

  return (
    <section className="w-full p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Saved Videos</h2>
        <button
          type="button"
          onClick={refreshLinks}
          disabled={!onRefresh || refreshing}
          className="rounded border px-3 py-2 text-sm"
        >
          {refreshing ? "Refreshing..." : "Refresh video links"}
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {videos.map((video, index) => (
          <div
            key={video._id ?? `${video.name}-${index}`}
            className="min-w-0 rounded-lg border p-3"
          >
            <p className="mb-2 truncate font-medium" title={video.name}>
              {video.name}
            </p>

            {video.url ? (
              <>
                <video
  key={video.url}
  controls
  preload="metadata"
  className="w-full rounded bg-black"
  src={video.url}
  onPlay={(event) => {
    const currentVideo = event.currentTarget;

    document.querySelectorAll("video").forEach((otherVideo) => {
      if (otherVideo !== currentVideo) {
        otherVideo.pause();
      }
    });
   }}
>
  Your browser does not support video playback.
</video>

<a
                  href={video.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block rounded bg-blue-600 px-4 py-2 text-sm text-white"
                >
                  Open / Download Video
                </a>
              </>
            ) : (
              <p className="text-sm text-red-500">
                Video link unavailable. Try refreshing.
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
