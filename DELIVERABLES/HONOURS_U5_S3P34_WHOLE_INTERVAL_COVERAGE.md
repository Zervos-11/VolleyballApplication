# S3 P34 whole candidate-interval coverage baseline

This report joins the [138-frame observation ledger](HONOURS_U5_S3P34_SIX_PLAYER_OBSERVATION_LEDGER.md) to the [completed 30-fps single-reviewer segment](HONOURS_U5_S3P34_30FPS_GROUND_REVIEW_PROGRESS.md). The interval is source-bracketed frames 36001–36138, **not** exact serve contact to dead ball. [Machine-readable output](../data/matches/yt_u5HnY2aNW14/screening/s3p34_whole_interval_coverage.json) retains per-frame counts and input hashes.

| Evidence tier | Count | Denominator | Meaning |
| --- | ---: | ---: | --- |
| Jersey-keyed candidate boxes | 780 | 828 player slots | 94.2% candidate availability; not verified grounded positions |
| Frames with six candidate boxes | 104 | 138 frames | 75.4% candidate team availability |
| Source-reviewed player states | 318 | 828 player slots | 138 previously sampled slots plus 180 new single-reviewer slots |
| Frames with six source-reviewed states | 53 | 138 frames | 23 prior sampled frames plus 30 new frames |
| Accepted grounded proxies under those reviews | 301 | 828 player slots | 36.4% **known lower bound**; unreviewed slots are unknown |
| Frames with six accepted grounded proxies | 41 | 138 frames | 29.7% **known lower bound**, not full-interval success rate |

The accepted 301 slots comprise 121 accepted positions from 23 sampled five-Hz frames inside this interval and 180 from 30 new source-reviewed frames. The 41 complete frames comprise 11 sampled frames and 30 newly reviewed frames. The remaining 510 player slots have no individual 30-fps source-state verdict in these joined forms. They are **not counted as failed floor positions**; their status is unknown. The 48 missing box candidates stay missing even where sequence review saw a player in the source image. The 37-frame chosen diagnostic has six accepted positions throughout, but it was selected after box availability was known.

These counts answer how much of the **candidate interval is already supported by each evidence tier**. They do not yet estimate the proportion of the full serve-to-dead-ball rally that can be reliably tracked: exact events, source states outside the reviewed frames and the calibration decision remain unresolved. A player can remain identified and boxed while airborne, with a null floor coordinate. Do not treat structural airborne nulls as identity failures or fill them with a held position.

Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_whole_interval_coverage.py` from the repository root. This script reads completed human annotations and writes only derived files.
