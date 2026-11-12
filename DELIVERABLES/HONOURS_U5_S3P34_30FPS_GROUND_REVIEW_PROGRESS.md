# S3 P34 30-fps diagnostic ground review result

The [source-first review packet](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/README.md) contains 37 native-resolution unboxed frames from 36066–36102. Seven frames already had six accepted 5-Hz grounded proxies. A single human reviewer completed the remaining 30 frames in the local website, marking all 180 player slots on unboxed source images before saving tracker comparisons for each frame. The [completed form](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv) is frozen and hash-checked by the [scorer](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_score.json).

| Evidence level | Count | Interpretation |
| --- | ---: | --- |
| Source frames in diagnostic segment | 37 | All have six jersey-keyed candidate boxes |
| Previously reviewed 5-Hz complete frames | 7 | Frames 36066, 36072, 36078, 36084, 36090, 36096 and 36102 |
| Newly reviewed intervening frames | 30 | All six slots marked grounded, same player and plausible box-bottom proxy |
| Newly accepted player slots under the single-reviewer rule | 180/180 | All have clicked shoe midpoints; no exception was recorded |
| Complete six-player frames in this diagnostic segment | 37/37 | Seven prior sampled frames plus 30 newly reviewed frames |

The [30-frame position comparison](HONOURS_U5_S3P34_30FPS_POSITION_COMPARISON.md) reports a **0.300 m median** and **0.551 m largest observed** projected shoe-to-box-bottom difference over the 180 new marks. Across the 30 frames, median proxy-minus-manual differences are **+0.004 m** in spacing, **−0.256 m²** in hull area and **+0.007 m** in centroid dispersion. These are within-frame, single-reviewer comparisons under the staged court transform. The reviewer had previously seen tracker output, and the review defaults were accepted for every slot; there is no independent adjudication or inter-observer reliability estimate.

The next [matched path check](HONOURS_U5_S3P34_30FPS_PATH_CONSISTENCY.md) finds a **12.860 m** manual shoe-midpoint chord sum against **7.591 m** from box bottoms over 174 matched player intervals. These short-interval sums are sensitive to shoe stance, box extent and manual reading uncertainty; neither is a measured foot-travel distance.

The segment was identified after candidate availability was known, so it is a diagnostic segment rather than a prespecified strict fixed window. The [calibration readiness audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_readiness.json) reports held-out attack-line residuals near **0.096 m** and **0.121 m**, but the transform's `use_for_final_metrics` flag remains false. Serve and point-ending frames remain bracketed, and S3 P34 has missing and airborne floor positions outside this segment. The [readiness audit](HONOURS_U5_S3P34_VALIDATION_READINESS.md) therefore still records **zero approved strict fixed-window results and zero validated complete six-player rally trajectories**.

The packet's original `audit.json` and blank form preserve the pre-review intake state; the completed CSV, scorer output and position comparison record the subsequent human review. Reproduce the scoring with `.\.venv\Scripts\python.exe scripts/score_u5_s3p34_single_reviewer_30fps.py`, the position comparison with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_30fps_single_reviewer_reference.py`, and readiness with `.\.venv\Scripts\python.exe scripts/audit_u5_s3p34_validation_readiness.py`.
