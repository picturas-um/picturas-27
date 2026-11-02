# Sample videos for manual tests

| File | Purpose | Expected result |
|---|---|---|
| `sample_10s_720p.mp4` | Valid video, 10 s, 1280x720, 30 fps, with audio | Accepted; can be edited, previewed, trimmed and exported |
| `sample_6s.mov` | MOV input | Accepted; the result is exported as MP4 |
| `too_long_90s.mp4` | Exceeds the 60 s limit of the free profile | Rejected on upload with the reason |
| `corrupted.mp4` | Corrupted file | Rejected on upload |

Generated with ffmpeg (`testsrc2`, `smptebars`, `sine`).
