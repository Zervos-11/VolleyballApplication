# Non-anchor error sensitivity for the fixed-box proxy

The [manual non-anchor shoe audit](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) found a largest mapped proxy-to-shoe discrepancy of **0.729 m** among 11 clear pairs at +12 frames across eight points. The earlier static reference maximum was 0.632 m. This observed maximum is not a bound.

Using that new radius, 1,000 seeded draws independently move each of the 240 fixed-box court proxies within a uniform disc. For each draw, the three spatial metrics are recomputed at all five instants, summarized by the window median, and compared as an equal-weight win-minus-loss difference across the three matched set-and-phase cells.

| Metric | Original contrast | Scenario range | Fraction positive |
| --- | ---: | ---: | ---: |
| Mean pairwise spacing (m) | -0.089 | -0.404 to +0.181 | 0.139 |
| Convex hull area (m²) | -4.212 | -7.481 to -0.675 | 0.000 |
| Centroid dispersion (m) | -0.104 | -0.310 to +0.065 | 0.042 |

The [machine-readable draws summary](../data/matches/yt_u5HnY2aNW14/screening/dynamic_error_sensitivity.json) is a sensitivity scenario, not a confidence interval, empirical error model or confirmatory significance test. The 11 marks were selected clear contacts, five selected slots were unmarkable, and this 16-slot subset has no complete six-player frame. A separate [one-frame team check](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) reuses two marks and adds four. The manual midpoints have about ±12 source-pixel reading uncertainty per axis. A larger error could occur during occlusion, low posture or jumping. The window sample was also selected by tracker availability.

Reproduce with `python scripts/analyze_u5_dynamic_error_sensitivity.py` after the fixed-box pilot and dynamic shoe-reference audit.
