# S3 P34 court-line click review

**Completed 4 November 2026.** All twelve marks were saved and frozen in
[completed.csv](completed.csv). The [predeclared staged-transform score](score.json)
did not pass: its largest landmark residual was 0.2037 m against the 0.200 m
screen. The 0.0037 m exceedance is within plausible manual line-centre selection
variation and cannot identify its cause. A separate [refined candidate analysis](../../../../../DELIVERABLES/HONOURS_U5_S3P34_REFINED_CALIBRATION_CANDIDATE.md)
fits four first-frame corners and reports eight held-out residuals. Neither
result approves a strict full-rally or fixed-window metric.

Open the local [court-line review](http://127.0.0.1:8040/s3p34-calibration-review). Enter your reviewer code. For each of the two unboxed frames, select each numbered court intersection, click its centre in the image, and refine the point in the enlarged crop. Save the six marks on each frame, then choose **Freeze completed 12-point review**. The page fills pixel coordinates; you do not need to type them.

The six points are the near baseline at both sidelines, the attack line at both sidelines, and the floor line under the net at both sidelines. Click the centre of the *painted line intersection*. If a point is genuinely unreadable, choose **Uncertain** or **Occluded** and leave its coordinates empty. Do not guess a coordinate. Saved marks reload if you return to the page. The staged transform and tracker overlays are withheld while marking.

The [protocol](protocol.json) froze the frames, source-image hashes, court coordinates, and operational screen before these new marks. The same reviewer previously saw the staged transform, so this is a single-reviewer source-image check, not an independent calibration study. A completed form is scored with `\.venv\Scripts\python.exe scripts/score_u5_s3p34_calibration_review.py` from the repository root. Passing the operational screen would support this camera's court-line mapping only. It would not validate true shoe-floor positions, make the 37-frame diagnostic segment a prespecified window, or validate the full rally.

The previous [30-fps ground review](../s3p34_30fps_ground_review/README.md) is complete and remains frozen.
