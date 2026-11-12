# S3 P34 source-only calibration review

The [frozen protocol](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/protocol.json) required twelve court-line intersections on two unboxed S3 P34 frames. The same reviewer marked these after earlier exposure to the staged calibration. The [machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/score.json) contains each projected residual and hashes the completed form.

**Operational screen:** did not pass. 12/12 intersections were marked. Median projected residual: 0.1099 m; maximum: 0.2037 m. The frozen rule required all twelve, a maximum residual no greater than 0.2 m, and at most 2.0 px static registration shift over the existing sampled camera check (observed 0.293 px).

The only threshold exceedance is the first frame's near-baseline/right-sideline mark, 0.0037 m above the 0.200 m limit. The same landmark in the second frame is 0.1969 m from its target, and the two source-image clicks are 0.58 px apart. Given manual line-centre selection and manually chosen original transform corners, this marginal difference cannot be attributed specifically to the click, the camera or the original transform. The frozen operational screen still records a failure.

The court-line check is scoped to this camera and near-court mapping. It does not establish independent player floor-position truth or fix the post hoc selection of the 37-frame diagnostic segment. Strict full-rally and fixed-window approval remains separate.

Reproduce with `.\.venv\Scripts\python.exe scripts/score_u5_s3p34_calibration_review.py`.
