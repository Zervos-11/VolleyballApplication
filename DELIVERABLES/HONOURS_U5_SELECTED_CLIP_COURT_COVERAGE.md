# Court-candidate coverage across the 18 selected edited clips

The [source-bound export](../data/matches/yt_u5HnY2aNW14/screening/selected_clip_court_candidate_coverage.json) joins the frozen score-only sample, score-aligned hard-edit clip boundaries and existing dense 5 Hz detector screen. It lists every sixth source frame **inside each edited clip**, including frames not screened by the dense pass. The edit bounds are not exact serve or point-end times. This is the earlier core-only screen; the later [full-clip tracklet pass](HONOURS_U5_FULL_CLIP_TRACKLET_AUDIT.md) screens all 1,005 grid instants with a new point-local tracker start, so its raw IDs and candidate totals are separate diagnostics.

| Coverage state | 5 Hz instants | Meaning |
| --- | ---: | --- |
| Not screened | 370 | No detector positions in the saved dense core |
| Fewer than six near-side candidates | 421 | Partial raw proposals; no player filled in |
| Exactly six candidates | 206 | Six raw box-bottom court points; identity and grounded status unvalidated |
| More than six candidates | 8 | Ambiguous selection; no six-person subset chosen |
| **Total** | **1005** | Across 18 edited clips and 6030 source frames |

| Set | Point | Near team won | 5 Hz instants | Not screened | <6 | Exactly 6 | >6 |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 5 | Yes | 45 | 20 | 15 | 10 | 0 |
| 1 | 6 | No | 60 | 30 | 19 | 10 | 1 |
| 1 | 18 | Yes | 30 | 10 | 15 | 5 | 0 |
| 1 | 27 | Yes | 45 | 15 | 21 | 9 | 0 |
| 1 | 34 | No | 60 | 25 | 23 | 12 | 0 |
| 1 | 37 | No | 110 | 15 | 61 | 33 | 1 |
| 2 | 2 | No | 75 | 20 | 37 | 17 | 1 |
| 2 | 6 | No | 115 | 25 | 74 | 16 | 0 |
| 2 | 14 | Yes | 35 | 25 | 4 | 6 | 0 |
| 2 | 26 | No | 70 | 15 | 35 | 20 | 0 |
| 2 | 28 | Yes | 30 | 15 | 6 | 9 | 0 |
| 2 | 37 | Yes | 45 | 20 | 17 | 7 | 1 |
| 3 | 11 | No | 45 | 20 | 19 | 6 | 0 |
| 3 | 13 | Yes | 50 | 25 | 16 | 9 | 0 |
| 3 | 23 | Yes | 35 | 30 | 4 | 1 | 0 |
| 3 | 27 | No | 55 | 20 | 22 | 12 | 1 |
| 3 | 33 | Yes | 50 | 15 | 25 | 10 | 0 |
| 3 | 34 | No | 50 | 25 | 8 | 14 | 3 |

The 206 exactly-six instants are **candidate court-coordinate data**, not six validated player positions. Raw track IDs can transfer, a box bottom can move away from the floor during a jump, and the clip includes pre- and post-play frames. The existing [eight-window fixed-box pilot](HONOURS_U5_FIXED_BOX_COURT_PROXY.md) is the smaller source-screened analysis used for exploratory metrics. This full-clip register preserves missingness for all 18 selected points and cannot be used to infer a winner effect by treating candidate frames as reviewed rallies.

Reproduce with `python scripts/export_u5_selected_clip_court_candidates.py`.
