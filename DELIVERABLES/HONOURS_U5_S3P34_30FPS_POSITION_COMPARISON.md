# S3 P34 single-reviewer 30-fps position comparison

The [completed 180-row review](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_unsampled_completed.csv) covers the 30 intervening frames in the selected 36066–36102 diagnostic segment. All six stored slots were marked grounded with a shoe midpoint and judged to have a matching, plausible candidate box. The [scorer](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_score.json) accepted all 180 slots under that single-reviewer rule. The reviewer had previously seen tracker output, so the source-first step in this pass does not create an independent blinded reference.

The 180 shoe-to-box-bottom projected distances have median **0.300 m** and largest observed value **0.551 m**. In image pixels, the median is **11.738 px** and the largest is **23.555 px**. These are within-frame differences from one reviewer, not independently established floor-position errors.

| Proxy minus manual team metric across 30 frames | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: |
| Mean pairwise spacing (m) | +0.004 | -0.051 | +0.114 |
| Convex-hull area (m²) | -0.256 | -0.911 | +0.842 |
| Centroid dispersion (m) | +0.007 | -0.029 | +0.076 |

The [machine-readable comparison](../data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review/single_reviewer_position_comparison.json) retains all 30 frame-level and 180 player-level values. The four-corner court transform is still staged, and this segment was selected after box availability was known. These comparisons do not certify a strict fixed window or complete rally; the source-bracketed S3 P34 rally still includes missing and airborne floor positions outside this segment.

Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_30fps_single_reviewer_reference.py`.
