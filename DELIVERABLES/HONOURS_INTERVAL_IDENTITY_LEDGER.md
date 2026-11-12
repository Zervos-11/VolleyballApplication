# Frozen-sample interval and identity review ledger

This [source-bound ledger](../data/processed/honours_interval_identity_ledger.json) joins existing score, boundary, saved-label, phase and detector-navigation evidence for all 18 frozen points. It does not change annotations or certify a new rally interval. The near-side team assignment follows the [source adjudication](HONOURS_NEAR_SIDE_SOURCE_ADJUDICATION.md): ProVolley in sets 1 and 3, UTS in set 2.

Annotator-checked intervals: **2/18**; independently reviewed intervals: **0/18**. Points with at least one source-phase-checked live six-nominal-position saved frame: **6/18**. Points whose saved six-ID sets change between frames: **4/18**. Verified continuous six-player trajectories: **0/18**.

| Set | Point | Winner | Near team | Saved interval | Live six-nominal frame(s) | Screened image box frame(s) | Saved ID change | First review anchor |
| ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | UTS | ProVolley | 8571–8840 | 8643 | — | no saved change | 8643 |
| 1 | 7 | ProVolley | ProVolley | pending | 15505 | — | no saved change | 15505 |
| 1 | 9 | ProVolley | ProVolley | pending | 19345 | — | check | 19345 |
| 1 | 23 | ProVolley | ProVolley | pending | 36366 | — | no saved change | 36366 |
| 1 | 32 | UTS | ProVolley | pending | — | — | check | 55065 |
| 1 | 39 | UTS | ProVolley | pending | — | — | no saved change | 65910 |
| 2 | 2 | ProVolley | UTS | 78000–78522 | 78050, 78100, 78400 | — | no saved change | 78050 |
| 2 | 8 | UTS | UTS | pending | — | — | no saved change | 85383 |
| 2 | 12 | UTS | UTS | pending | — | — | no saved change | 90080 |
| 2 | 14 | ProVolley | UTS | pending | — | — | no saved change | — |
| 2 | 21 | UTS | UTS | pending | — | — | check | 102513 |
| 2 | 33 | ProVolley | UTS | pending | — | — | no saved change | 125769 |
| 3 | 5 | ProVolley | ProVolley | pending | — | 155799 | no saved change | 155799 |
| 3 | 11 | UTS | ProVolley | pending | — | 162695 | no saved change | 162695 |
| 3 | 21 | ProVolley | ProVolley | pending | — | — | check | — |
| 3 | 27 | ProVolley | ProVolley | pending | 187701 | — | no saved change | 187955 |
| 3 | 37 | UTS | ProVolley | pending | — | 204263 | no saved change | 204263 |
| 3 | 38 | UTS | ProVolley | pending | — | — | no saved change | 205408 |

Saved-ID changes to inspect: S1 P9 f19854 (17 → 11); S1 P32 f55065 (17 → 11); S2 P21 f102513 (38 → 36); S3 P21 f177778 (5 → 9). These are changes in annotation labels across sparse frames; they are not evidence of a real substitution without checking the video. The JSON records the full ID set at each saved frame.

## Review order

1. Start from the two saved annotator-checked intervals, which still lack independent source review. For the other points, the ledger provides only a heuristic start/end and score-flip search range; verify serve contact and point-ending action in the source video before using a window.
2. At each first review anchor, verify **six distinct near-side players**, their player IDs and the action phase. The screened-image anchors are short source-image checks, not complete tracks. Set-three point 27 frame 187701 is explicitly rejected as a near-side six-player anchor because its saved box includes a far-side opponent. Preserve exclusions and the frozen selection.
3. Resolve changed saved ID sets from the video before temporal matching. In particular, the non-numeric `Hair` identifier is not a jersey number. Unknown or opposite team fields need source reconciliation, but the completed player drawings should be reused.
4. Track only within a verified live interval. Keep occluded/off-screen players missing; bridge a short gap only when the same identity is confirmed on both sides and mark the estimate. Validate grounded box-bottom against an independent floor reference before reporting metres.

The [three existing navigation sheets](../data/processed/honours_sample_sheets/) show source stills for every frozen point. The [dense-window check](HONOURS_DENSE_PROXY_WINDOW_VISUAL_REVIEW.md) explains why six raw boxes are insufficient for a team trajectory.
