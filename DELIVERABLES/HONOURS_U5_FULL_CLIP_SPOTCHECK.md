# Full-clip raw-run source spot check

The two longest 18-sample same-six-ID runs were checked on the first, middle and last sampled source frames. These six displayed images are a bounded visual check, not a review of every intervening frame. The [source-linked audit](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck_audit.json) records the reviewed frames, sheet hashes and manual observations.

| Point | Displayed source frames | Observation | Decision |
| --- | --- | --- | --- |
| S1 P5 | 1326, 1380, 1428 | All six boxes appear on the near-side UCLA team at these three frames. | Retain as a raw candidate; exact live phase, intervening identity and court-floor positions remain unchecked. |
| S3 P34 | 36000, 36054, 36102 | Raw ID 8 labels white jersey #28 in all three frames. Close crops show the same player; #28 is the near-side libero. | Retain as a raw candidate; do not certify the uninspected frames or grounded positions. |

The [first sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s1_p05_first_middle_last.png) and [second sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_first_middle_last.png) show the original source frames with the pass's raw-ID boxes. Close crops of ID 8 at [frame 36000](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3p34_id8_f36000.png), [frame 36054](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3p34_id8_f36054.png) and [frame 36102](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3p34_id8_f36102.png) show the same jersey #28. The initial visual classification of white #28 as an opponent was incorrect; #28 is the near-side libero. The [later every-sample review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) checks all 18 five-Hz samples in each run. Neither review validates a full rally or grounded court-coordinate path.

Reproduce the sheets with `python scripts/render_u5_full_clip_run_spotcheck.py` and the audit with `python scripts/audit_u5_full_clip_spotcheck.py`.
