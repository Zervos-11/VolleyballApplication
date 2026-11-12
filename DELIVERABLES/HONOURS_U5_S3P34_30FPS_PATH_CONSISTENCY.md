# S3 P34 30-fps diagnostic path consistency

The [completed position comparison](HONOURS_U5_S3P34_30FPS_POSITION_COMPARISON.md) provides 30 clicked shoe midpoints per player slot in the selected 36066–36102 segment. For each of six slots, this audit compares the manual and box-bottom straight-line chords between the same successive marked frames. The seven earlier sampled frames are not inserted into either path, so no position is imputed.

There are **174 matched player-interval chords**: 144 span one source frame and 30 span two. The manual chord sum is **12.860 m** and the proxy sum is **7.591 m**, a signed difference of **-5.269 m**. The median absolute paired chord difference is **0.048 m** and the largest is **0.573 m**. Median individual chords are 0.068 m for manual marks and 0.024 m for box bottoms.

For one-frame gaps, the median manual and proxy chords are 0.066 and 0.022 m; for two-frame gaps they are 0.071 and 0.045 m. The manual median changes little with the longer gap, which is compatible with shoe stance or clicking variation contributing to the manual sum. This comparison cannot determine how much of the sum difference is true missed movement.

The largest disagreement is stored slot 7 between frames 36089 and 36091: its clicked midpoint chord is 0.000 m while its box-bottom chord is 0.573 m. The two source frames show the player near the net with little change in shoe-midpoint location; this pattern is consistent with a changing detector box bottom, although annotation uncertainty also matters.

| Stored slot | Manual chord sum (m) | Proxy chord sum (m) | Proxy − manual (m) |
| --- | ---: | ---: | ---: |
| 28 | 2.169 | 1.164 | -1.006 |
| 12 | 1.995 | 0.399 | -1.596 |
| 15 | 2.544 | 1.545 | -0.999 |
| 7 | 1.300 | 2.489 | +1.189 |
| 19 | 2.442 | 0.578 | -1.864 |
| 21 | 2.411 | 1.417 | -0.994 |

These sums describe displacement of two point proxies at the sampled instants. They are not foot travel, step counts, or speed. A shoe midpoint can move with stance even when the player's court position changes little. The existing 12–15-pixel per-axis reading uncertainty is substantial relative to these one-frame chords, so summing them may amplify manual-click jitter. Signed differences may cancel, and all chords come from one previously tracker-exposed reviewer and one availability-selected segment under a staged court transform. The [machine-readable audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_path_consistency.json) retains every paired chord; strict metric approval remains false.

Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_30fps_path_consistency.py`.
