# Short-window image-plane geometry diagnostic

The [source-bound calculation](../data/matches/yt_u5HnY2aNW14/screening/flow_window_image_geometry.json) uses the [optical-flow pilot](HONOURS_U5_BOX_CENTRE_FLOW_PILOT.md) at five 5 Hz samples per window. Eight of the frozen 18 points remain after the displayed-endpoint, open-play-anchor and set-by-phase screens. The eight comprise four wins and four losses in three set-and-phase cells. Every metric here uses full image-box centres in **pixels**, including airborne people.

| Image metric | Mean winning minus losing window median | At anchor only | Across five individual offsets |
| --- | ---: | ---: | ---: |
| Mean pairwise spacing (px) | +36.503 | +35.638 | +28.057 to +48.957 |
| Convex hull area (px^2) | -8166.551 | -7407.911 | -11094.059 to -6354.848 |
| Centroid dispersion (px) | +23.946 | +23.923 | +19.294 to +32.400 |

The comparison averages within-cell differences equally across the three set-and-phase cells. The five-offset range shows how the descriptive contrast changes when each of the five sample times is used alone; it is not an error interval. Box translations can drift when people cross or change pose, and four such windows were excluded by endpoint review. A later [five-instant source review](HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) found no obvious wrong-person transfer in the eight retained windows at their five displayed samples. Unsampled frames, named identities and the entire live phase are not certified even in these eight. The sample was selected by detector and review availability, so these figures are **not a statistical association with winning**. Court positions and rotation/transition measures are still missing.

Reproduce with `python scripts/analyze_u5_flow_window_geometry.py` after the optical-flow pilot and endpoint audit.
