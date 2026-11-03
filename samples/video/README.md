# Sample videos for manual tests

| File | Purpose | Expected result |
|---|---|---|
| `sample_10s_720p.mp4` | Valid video, 10 s, 1280x720, 30 fps, with audio | Accepted; can be edited, previewed, trimmed and exported |
| `sample_6s.mov` | MOV input | Accepted; the result is exported as MP4 |
| `too_long_90s.mp4` | Exceeds the 60 s limit of the free profile | Rejected on upload with the reason |
| `corrupted.mp4` | Corrupted file | Rejected on upload |
| `speech_mandela_177s_1080p.webm` | Real WebM (VP9 + Opus), 2 min 57 s, 1920x1080, English narration | Rejected on the free profile (over 60 s); accepted on premium. Good input for **Automatic subtitles** and **Extract frames** |

The synthetic samples were generated with ffmpeg (`testsrc2`, `smptebars`, `sine`).

`speech_mandela_177s_1080p.webm` is
[“How Nelson Mandela Fought for Equality and Freedom”](https://commons.wikimedia.org/wiki/File:How_Nelson_Mandela_Fought_for_Equality_and_Freedom.webm)
by [simpleshow foundation](https://www.youtube.com/user/simpleshowfoundation), licensed under
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), via Wikimedia Commons. Unmodified.
