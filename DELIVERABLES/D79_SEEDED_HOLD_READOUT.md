# D79 pre-rally identity and overlap holds

The clear setup before the point provides a stable starting identity for the six near-side players. [Frame 40](../data/processed/d79_new_source/prerally_40.jpg) shows #8, #9, #23, #15 and jersey 14; [frame 55](../data/processed/d79_new_source/prerally_55.jpg) shows #98 serving. The saved annotation key **#4** is retained for the player whose jersey appears to read **14**. These readings are source-reviewed candidates, not a change to the user's labels.

The [seed and handoff record](../data/processed/d79_new_source/prerally_identity_seed.json) maps those identities to accepted tracker segments across the 257 candidate frames (80–336). An [early source sheet](../data/processed/d79_new_source/prerally_id_handoff_sheet.jpg) catches a raw-ID exchange: raw 7 boxes #9 at frame 80 but #23 by frame 148. Raw 30 later boxes #9 through frame 268, then appears on a far-side teal player at frame 289. The saved #9 identity is **not** attached to that return.

For every player and frame, the [CSV](../data/processed/d79_new_source/seeded_occlusion_hold_positions.csv) distinguishes `observed_proxy`, `held_assumption`, and `airborne_excluded`. During an ambiguous or missing span, the last accepted feet-level box-bottom centre is carried forward unchanged. It is a **stationary display assumption**: no box, floor contact, speed, or true position is claimed for that span. The [timeline](../data/processed/d79_new_source/seeded_hold_timeline.jpg) shows accepted proxy positions in green, held positions in orange, and excluded serve frames in grey.

| Saved player | Accepted proxy frames | Held frames | Excluded frames | Main limitation |
|---|---:|---:|---:|---|
| #8 | 257 | 0 | 0 | Continuous candidate box; floor point remains a proxy. |
| #98 | 239 | 0 | 18 | Airborne serve excluded through frame 97. |
| #23 | 181 | 76 | 0 | Holds at 93–147 and 195–215, including the early ID exchange. |
| #4 / jersey 14 | 173 | 84 | 0 | Late airborne box proxy withheld from frame 305. |
| #9 | 136 | 121 | 0 | Holds at 95–147 and 269–336; no accepted return after 268. |
| #15 | 80 | 177 | 0 | Long uncertain stretch 149–293; late airborne boxes withheld after 304. |
| **Total** | **1,066** | **458** | **18** | Six identities × 257 frames = 1,542 states. |

The [machine-readable result](../data/processed/d79_new_source/seeded_occlusion_holds.json) records exact hold runs and accepted segments. For a gap with accepted positions on both sides, the distance method adds a straight chord between those endpoints to the smoothed visible-segment path. It does not require a speed estimate. The player could have travelled farther during the gap; a gap at the point end has no return endpoint and remains outside the reported scope.

| Player | Endpoint-based candidate distance | Source-frame scope | Limitation |
|---|---:|---:|---|
| #8 | 3.21 m | 80–336 | Continuous proxy, no gap. |
| #98 | 6.77 m | 98–336 | Airborne serve excluded. |
| #23 | 5.66 m | 80–336 | Includes 0.67 m and 0.97 m chords across two missing spans. |
| #4 / jersey 14 | 2.22 m | 80–304 | Final 32 frames have no return endpoint. |
| #9 | Withheld | 80–268 | Near-net proxy crosses uncertain candidate court line; final 68 frames have no return endpoint. |
| #15 | 1.63 m | 80–304 | Includes 1.17 m chord across a 145-frame gap; final 32 frames have no return endpoint. |

These are **approximate box-bottom proxy distances under provisional court geometry**. The straight chord is the shortest link between the accepted proxy endpoints, not a reconstructed hidden trajectory or a guaranteed lower bound on real travel. #4 and #15 endpoint figures do not cover the point end. No measured physical six-player or team distance is available. The earlier #8 and #98 development estimates are unchanged.

## Full-point stationary-hold scenario

A [source-sampled final-frame review](../data/processed/d79_new_source/terminal_hold_source_review.json) and [contact sheet](../data/processed/d79_new_source/terminal_hold_source_sheet.jpg) inspect frames 268–336. #9 has no accepted return after 268; #14 and #15 are airborne in later sampled frames, so their box bottoms are unsuitable floor points. Under the explicitly chosen hold convention, each of these **unclosed** spans contributes zero additional distance through frame 336. Five #9 proxies project at most 0.075 m past the provisional 9 m near-court edge; the scenario clips those points to the edge before smoothing.

| Player | Full-point hold scenario |
|---|---:|
| #8 | 3.21 m |
| #98 | 6.77 m, starting after the serve landing |
| #23 | 5.66 m |
| #4 / jersey 14 | 2.22 m |
| #9 | 2.40 m, with five court-edge clips |
| #15 | 1.63 m |
| **Six-player sum** | **21.89 m** |

This is a **model-based approximate scenario**, not measured physical travel. It answers what the chosen stationary-hold and endpoint-chord rules produce over the full candidate point. Hidden movement, jumping, shoe/box mismatch and provisional court geometry can change real distances. The per-player endpoint estimates above remain separately scoped where a return endpoint is absent.

Regenerate the result with [build_d79_seeded_occlusion_holds.py](../scripts/build_d79_seeded_occlusion_holds.py). The source candidate and saved annotations are unchanged.

The local [D79 playback page](../web/d79_case_study.html) shows the setup frames, exact source stills, the accepted green boxes, orange last-seen markers, and all six player states. The updated local server is running at `http://127.0.0.1:8012/d79-case-study` in this session because port 8011 has an older instance. The page reads the generated [viewer record](../data/processed/d79_new_source/seeded_hold_viewer_record.json); it does not save or alter annotations.
