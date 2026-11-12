# Phase-matched court-proxy diagnostic

This [source-bound analysis](../data/matches/yt_u5HnY2aNW14/screening/phase_matched_proxy_diagnostic.json) projects the bottom centre of six locally source-checked player boxes through the staged 9 m court transform. These are **approximate floor-plane proxies at one frame per point**, not verified shoe contacts or player trajectories. The separately [reviewed phase tags](HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md) restrict the calculation to open-play set-by-phase cells that contain both outcomes.

The frozen denominator is **18** points. There are 17 correct six-box snapshots, of which 13 fall in 5 comparable set-by-phase cells. Two serve/reset frames and two set-two defensive losses lack a within-cell counterpart; one set-three win has no six-box snapshot. None is silently replaced. One recovered set-one player projects 0.158 m beyond the sideline; court-relative coordinates can extend beyond painted court bounds during play. The convex hull is calculated from all six proxies and is not clipped to the painted 9 m square.

| Court proxy | Equal-cell mean win minus loss | Two-sided conditional label reference | Observed-error perturbation range |
| --- | ---: | ---: | ---: |
| Mean pairwise spacing (m) | +0.104 | 0.843 (108 assignments) | -0.230 to +0.455 |
| Convex hull area (m^2) | +0.309 | 0.954 (108 assignments) | -3.671 to +4.350 |
| Centroid dispersion (m) | +0.032 | 0.926 (108 assignments) | -0.200 to +0.282 |

## Detector-pass sensitivity

Removing the one higher-resolution recovered snapshot in the matched group leaves 12 original-pass snapshots across the same five set-and-phase cells. The second higher-resolution recovery was a serve and was already excluded.

| Court proxy | All 13 matched snapshots | Original-pass 12 only |
| --- | ---: | ---: |
| Mean pairwise spacing (m) | +0.104 | -0.023 |
| Convex hull area (m^2) | +0.309 | -0.754 |
| Centroid dispersion (m) | +0.032 | -0.041 |

The conditional reference enumerates all assignments of the observed number of wins within each set-and-phase cell. It is **not a valid confirmatory p-value**: the snapshots were selected where detector boxes were available, within-cell outcome exchangeability is unestablished, one winning point is missing, and the cells have only one or two observations per outcome. The last column perturbs each proxy by up to the observed clear-shoe maximum of 0.632 m across 2,000 seeded draws. It is a scenario range, not a confidence interval or guaranteed error bound, and does not cover airborne posture bias.

**Conclusion:** This is the strongest reproducible *single-frame* court-proxy comparison presently available from the frozen sample. It cannot satisfy the signed requirement for validated trajectories, movement/transition measures or a reliable statistical outcome association. The strict court-metric result remains zero eligible points.

Reproduce with `python scripts/analyze_u5_phase_matched_proxy.py` after the snapshot and phase audits.
