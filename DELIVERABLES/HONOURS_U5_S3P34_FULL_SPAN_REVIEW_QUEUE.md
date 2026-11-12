# S3 P34 full-span validation review queue

The [machine-readable queue](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/review_queue.json) covers source frames 36001–36138, the 138-frame candidate interval. The [preparation script](../scripts/prepare_u5_s3p34_full_span_review.py) joins the dense tracker output, jersey-keyed candidate paths and existing 5 Hz source ledger, then renders paired unboxed/boxed source views. It does **not** make new validation claims.

| Candidate availability | Source frames |
| --- | ---: |
| Six box-bottom candidates | 104/138 |
| At least one missing candidate | 34/138 |
| Missing #28 / #12 / #19 | 0 / 0 / 0 |
| Missing #15 / #7 / #21 | 15 / 11 / 22 |

The per-jersey counts overlap in time, so they do not sum to 34. Missing candidate runs are #15: 36110–36124; #7: 36015, 36026, 36030–36031, 36124, 36126–36131; #21: 36047–36050, 36059–36060, 36107–36122. The priority queue selects 79 source frames: 78 within the candidate interval and the previously reviewed frame 36000 immediately before it. It includes the existing 5 Hz samples, gap frames and their neighbours, the ID-transition region, and the beginning and end of the candidate interval. Paired source/box contact sheets cover **every** frame in the 138-frame candidate interval plus frame 36000. The [frame/player template](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/frame_player_review_template.csv) preserves all 828 frame–jersey slots and existing 5 Hz verdicts in a separate column; all new source-review fields remain blank pending inspection.

Two examples from the new sheets illustrate why a candidate count is not floor-position validation. [Review page 6](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/review_page_06.jpg) shows UCLA #7 visible at frame 36015 while the candidate slot is missing. The source sequence at frames 36111–36113 shows front players #15 and #21 airborne as their candidates disappear. A visible body in either case does not establish a grounded court point.

The next visual pass must assign each jersey and frame a status: grounded usable box, visible unboxed, airborne, occluded or off screen. Candidate identities at unreviewed 30 fps frames remain provisional. Unavailable court positions stay null; any gap-filling model must be reported and evaluated separately. Serve contact and point end remain bracketed, and the staged homography has not been independently approved for strict metric use. Therefore **the validated full-rally count remains zero**.

Rebuild from the repository root with `.\.venv\Scripts\python.exe scripts/prepare_u5_s3p34_full_span_review.py`. Run the [annotation checker](../scripts/audit_u5_s3p34_full_span_review.py) with `.\.venv\Scripts\python.exe scripts/audit_u5_s3p34_full_span_review.py`. It currently reports 828 unreviewed slots and zero completed 30-fps team frames. The checker verifies annotation completeness and internal consistency only; a completed CSV would still need calibration, event-boundary and manual-reference assessment.
