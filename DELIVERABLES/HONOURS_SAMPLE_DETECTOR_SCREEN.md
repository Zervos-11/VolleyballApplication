# Frozen-sample detector feasibility screen

The [machine-readable screen](../data/processed/honours_sample_detector_feasibility.json) applies the local YOLOv8n person model to three **heuristic navigation frames** for each of the 18 frozen ProVolley vs UTS points. It counts detector boxes whose bottom centre projects into the nominal near-side 9 m square using staged camera geometry. These are proposals, not identified players or accepted floor positions.

14/18 points have at least one navigation frame with six or more projected near-court person boxes. A lower count does not exclude a point: the heuristic frames may miss play, a player may be hidden, or the detector may miss a person. A count of six does not establish that six distinct target-team players are present. The score sample remains frozen; do not substitute points based on this screen.

| Set | Point | Winner | Three frame candidate counts | Maximum |
| ---: | ---: | --- | --- | ---: |
| 1 | 2 | UTS | 4, 5, 5 | 5 |
| 1 | 7 | ProVolley | 6, 6, 6 | 6 |
| 1 | 9 | ProVolley | 7, 5, 7 | 7 |
| 1 | 23 | ProVolley | 7, 5, 5 | 7 |
| 1 | 32 | UTS | 8, 5, 3 | 8 |
| 1 | 39 | UTS | 6, 5, 5 | 6 |
| 2 | 2 | ProVolley | 8, 6, 5 | 8 |
| 2 | 8 | UTS | 4, 5, 5 | 5 |
| 2 | 12 | UTS | 7, 4, 6 | 7 |
| 2 | 14 | ProVolley | 4, 6, 6 | 6 |
| 2 | 21 | UTS | 7, 6, 5 | 7 |
| 2 | 33 | ProVolley | 5, 6, 4 | 6 |
| 3 | 5 | ProVolley | 4, 6, 6 | 6 |
| 3 | 11 | UTS | 6, 6, 6 | 6 |
| 3 | 21 | ProVolley | 6, 7, 3 | 7 |
| 3 | 27 | ProVolley | 6, 5, 5 | 6 |
| 3 | 37 | UTS | 5, 4, 5 | 5 |
| 3 | 38 | UTS | 5, 5, 3 | 5 |

The [R2 source audit](HONOURS_R2_READINESS.md) remains the only point with linked pilot player annotations. This detector screen is a review-navigation aid and contributes **zero validated metric frames**.

Best-frame sheets: [set 1](../data/processed/honours_sample_detector_sheets/set_1_best_navigation_frames.jpg), [set 2](../data/processed/honours_sample_detector_sheets/set_2_best_navigation_frames.jpg), [set 3](../data/processed/honours_sample_detector_sheets/set_3_best_navigation_frames.jpg). Green boxes are automatic near-court proposals; they may include opponents or miss target players.
