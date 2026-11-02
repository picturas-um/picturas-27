# PictuRAS

Context for AI coding agents, so they do not have to rediscover the project on every
session.

## What the app is

PictuRAS is a web editor for images and videos, delivered as SaaS. Users build an
ordered pipeline of effects (brightness, rotate, crop, AI tools, ...) and apply it to
every media item of a project in one batch. There are three profiles: anonymous
(limited), free (5 operations per day) and premium (unlimited).

## What existed before (base project)

An image-only application built as Docker Compose microservices:

- `frontend/` — Next.js (bun). Talks to the backend only through nginx.
- `nginx/` — HTTPS entry point at `https://localhost:8080`; proxies `/` to the frontend,
  `/api-gateway/` to the API gateway and `/socket.io` to the WebSocket gateway.
- `apiGateway/` — Express; validates the JWT and forwards requests.
- `projects/` — Express orchestrator. Owns projects, their media and their tool
  pipeline. Processing sends one RabbitMQ message per (image, tool) step and advances
  the chain when the tool replies on `project_queue`.
- `Tools/<tool>/` — one Python + PIL microservice per image effect, consuming
  `<tool>_queue` on the `picturas` direct exchange and reading/writing files on the
  shared `image_data` volume.
- `wsGateway/` — socket.io; forwards `ws_queue` events to the browser.
- `users/` — accounts, profiles and the daily operations quota.
- `imageStorageService/` — S3-compatible storage (SeaweedFS) with the stages `src`,
  `out`, `preview` and `preview_cache`.

The pipeline belongs to the project, not to each image: applying it processes every
media item of the project.

## What had to be done

Extend the application to support video as an MVP: upload videos, edit them with the
effect pipeline, follow the progress of a long-running job, preview the result and
download it, without rewriting the existing image flow.

## What was added

- **Video worker** (`Tools/video`, service `video_tool`): consumes `video_queue`. One
  message carries one video and its whole pipeline. It probes the file with ffprobe,
  decodes it once, applies the frame effects to every frame with the same PIL
  operations as the image tools (`effects.py`), and encodes once to MP4/H.264 + AAC,
  keeping the audio. It publishes progress (%) to `ws_queue`, acknowledges the message
  only at the end, and never leaves partial output on failure. Supported effects:
  brightness, contrast, saturation, binarization, rotate, resize, cut (crop), border,
  trim and speed. Preview mode processes only the first `VIDEO_PREVIEW_SECONDS` (3 s).
- **Trim**: a video-only effect with `start`/`end` in seconds. It belongs to the video
  it was defined on (`params.imgId`), because its times only make sense for that video;
  every other effect still applies to all media (speed works the same way). It is resolved before decoding, so
  picture and audio are cut on the same window.
- **Speed**: a video-only effect with a `factor` from 0.25x to 5x, also stored per video
  (`params.imgId`). Frame timestamps are rescaled while decoding and resampled to the
  original frame rate, and the audio tempo changes by the same factor (`atempo`), so both
  stay in sync. Trim times always refer to the original video.
- **Projects orchestrator**: new `POST /:user/:project/video` endpoint (images keep
  `/img`; each endpoint rejects the other kind). Uploaded videos are validated with
  ffprobe (container, codec, duration, size, resolution) against per-profile limits and
  stored with `media_type: "video"` and their characteristics. Processing sends each
  video as one job to the worker, images skip video-only tools, and video operations
  are charged as one operation per effect per video. Video logic lives in
  `projects/utils/video.js`.
- **Frontend**: imports MP4/MOV/WebM, plays videos in the grid and carousel, shows the
  trim and speed tools for the selected video, hides image-only tools (AI, watermark) and the PDF
  export in projects with videos, and shows a single progress bar with the real video
  percentage. Preview opens in a video player. The projects sidebar stays open while
  processing.
- **Infrastructure**: `video_queue` in RabbitMQ, `video_tool` in `docker-compose.yaml`,
  larger request bodies in nginx and the API gateway, `video-progress` events in the
  WebSocket gateway.
- **Fixes to the base project** found along the way: the WebSocket gateway now
  reconnects to RabbitMQ after a broker restart; imported media appear without a page
  refresh; the users service's non-standard 701 status is mapped to 403 so the "daily
  limit reached" message reaches the user.

Per-profile video limits are environment variables of the `projects` service:
free 60 s / 100 MB / 1920x1080, premium 600 s / 1 GB / 3840x2160.

## Running and testing

```bash
docker compose up -d --build                 # first build takes 15-30 min
docker compose up -d --build <service>       # rebuild only what changed
docker compose restart nginx                 # after rebuilding the frontend (avoids 502)
docker compose logs -f <service>
docker compose run --rm video_tool sh -c "pip install -q pytest && python -m pytest -q tests"
```

Sample videos for manual tests are in `samples/video/` (see its README).

## Conventions

- All code, comments, identifiers and user-facing messages in English.
- Extend the base project instead of rewriting it; change base behaviour only when it
  blocks a feature.
- Conventional Commits, subject line under 72 characters. Never push without the
  team's explicit approval.
- The checkout is on Windows (CRLF); keep each file's existing line endings.

## Known pitfalls

- RabbitMQ consumers must survive broker restarts.
- The image tools auto-acknowledge messages and swap `messageId`/`correlationId` in
  their error replies, so their errors do not reach the user; the video worker does not
  have this problem.
- After rebuilding the frontend, nginx keeps the old container address until restarted.
