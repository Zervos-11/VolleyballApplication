# Fixed-box anchor versus manual shoe reference

The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/fixed_box_anchor_reference_audit.json) joins the fixed-box pilot to **existing** single-reviewer shoe-midpoint marks on the same source frames. This is a direct anchor check, not a new or independent annotation. Sixteen players match across three anchor frames; two frames have clear grounded shoe marks for all six teammates.

Median court-position discrepancy is 0.277 m and the largest is 0.632 m across the 16 matched players. The existing reference includes only clearly visible grounded shoes and has approximate visual-reading uncertainty.

| Frame | Proxy minus manually marked six-player spacing | Hull area | Dispersion |
| --- | ---: | ---: | ---: |
| S3 P13 f29940 | +0.235 m | +1.881 m^2 | +0.179 m |
| S3 P34 f36072 | +0.048 m | +0.681 m^2 | +0.023 m |

These two complete frames illustrate how position-proxy error propagates into team metrics. They do not validate the other samples in each 0.8 s window, difficult poses, or full-rally trajectories. The figures remain exploratory measurements under the original research-prototype scope.

Reproduce with `python scripts/audit_u5_fixed_box_anchor_reference.py`.
