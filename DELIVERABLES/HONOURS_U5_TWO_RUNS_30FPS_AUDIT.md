# Thirty-frame-per-second screen of two long candidate runs

The [source-bound dense audit](../data/matches/yt_u5HnY2aNW14/screening/two_long_runs_30fps_audit.json) reruns YOLOv8n and ByteTrack at every decoded source frame inside the two longest 5 Hz candidate spans. It independently resets tracking at each span and maps its first-frame raw IDs to the [reviewed 5 Hz jerseys](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) by unique box overlap above 0.5. The dense pass is an algorithmic continuity screen, not a human jersey check of every 30 fps frame.

| Point | Source frames | Exactly six near-side candidates | Temporary missing frames | New raw IDs |
| --- | ---: | ---: | ---: | ---: |
| S1 P5 | 103 | 103 | 0 | 0 |
| S3 P34 | 103 | 93 | 10 | 0 |

| S3 P34 jersey | Dense ID | Frames present | Missing source frames |
| --- | ---: | ---: | --- |
| #28 | 1 | 103/103 | None |
| #12 | 3 | 103/103 | None |
| #15 | 6 | 103/103 | None |
| #7 | 9 | 99/103 | 36015, 36026, 36030–36031 |
| #19 | 10 | 103/103 | None |
| #21 | 13 | 97/103 | 36047–36050, 36059–36060 |

S1 P5 retains the same six raw IDs in all 103 decoded frames. S3 P34 retains the same six ID values when present, but #7 is missing for four frames and #21 for six frames. The missing states are explicit; no position is held still or interpolated. A [source-image check of all ten missing frames](../data/matches/yt_u5HnY2aNW14/screening/two_long_runs_30fps_gap_qc.json) finds the missing teammate visible but unboxed in each image; the [first five-frame sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_30fps_missing_1.png) and [second sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_30fps_missing_2.png) show the source evidence. Some players are adjacent; the precise detector-versus-tracker cause is not adjudicated. The every-sample 5 Hz crop review found stable jerseys at 18 anchor frames in each run, but the dense pass does not certify jersey identity in every inter-sample frame. The [manual position comparison](HONOURS_U5_FULL_RUN_POSITION_REFERENCE.md) has only two clear shoes at one source frame. Neither run is a validated full-rally grounded trajectory.

Reproduce with `python scripts/screen_u5_two_long_runs_30fps.py` and `python scripts/audit_u5_two_long_runs_30fps.py`.
