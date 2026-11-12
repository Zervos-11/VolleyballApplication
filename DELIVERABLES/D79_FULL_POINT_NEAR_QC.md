# D79 full-point near-side box QC

The chosen target is the six near-side players in candidate point frames **80–336**. The [generated named-box output](../data/processed/d79_new_source/named_near_boxes_80_336.json) has one slot per player per frame. Its accepted boxes are source-seeded raw detections; a null box remains null through an unresolved handoff or overlap. This QC is about named boxes, not court-floor positions or physical distance.

| Player | Accepted boxes / 257 frames | Missing-box slots |
| --- | ---: | ---: |
| #4 (jersey candidate 14) | 207 | 50 |
| #8 | 257 | 0 |
| #9 | 147 | 110 |
| #15 | 168 | 89 |
| #23 | 210 | 47 |
| #98 | 257 | 0 |
| **All six** | **1,246 / 1,542 slots** | **296** |

All six players have accepted boxes together on **36/257 frames**. These counts describe conservative output coverage; they do not prove that all six were source-visible on every frame. The [reviewed 50-frame slice](D79_REVIEWED_NEAR_EVALUATION.md) still matches 232/232 visible target boxes with the correct names. Those reviewed frames were used to fix #15's handoff, so the score is an in-sample regression check.

## What the missing slots mean

The [reproducible visibility audit](../data/processed/d79_new_source/named_gap_visibility_audit.json) checks every null named-box slot against the hash-bound human review of frames 240–289. It refuses stale labels or a stale gap queue.

| Missing-box state | Slots | Evidence |
| --- | ---: | --- |
| Fully occluded | 53 | Human-reviewed frame label; #9 accounts for 21, #15 for 32. |
| Partly occluded, no usable box | 15 | Human-reviewed #15 frame label. |
| Source-visible, no accepted named box | 24 | Dense assistant review of #4's 311–316 and 319–336 jump frames; jersey 14 remains distinct. |
| No distinct source identity, no accepted named box | 47 | Dense assistant review of #9's 290–336 terminal gap; this does not distinguish occlusion from leaving view. |
| Visibility unknown | 157 | No dense reviewed label for that player and frame. |
| **All null boxes** | **296** | |

In the reviewed window, the output covers **232/232 players with a saved visible box**. The other **68/300 near-player slots** have a reviewed no-box status and are not detector misses. This is an in-sample agreement check because those labels informed the identity fix. A [dense source review](../data/processed/d79_new_source/named_gap_review/source_visibility_review.json) separately checked every frame in #4's late jump gaps, establishing 24 visible named-box misses without inferring floor points. It also checked #9's 290–336 terminal gap: no distinct #9 appears, but the images cannot prove whether he is fully occluded or outside the view. Its [frame sheets](../data/processed/d79_new_source/named_gap_review/dense_visibility/manifest.json) include every player-frame outside the human-reviewed window. These assistant checks are separate from the user's reviewed labels. Full-point visible-player recall cannot yet be calculated because the other 157 slots may contain visible players, occlusions, or uncertain identities. The [audit script](../scripts/audit_d79_named_gap_visibility.py) preserves a status for each missing player-frame slot and summarizes each run.

The [gap queue](../data/processed/d79_new_source/named_gap_review/gap_queue.json) lists eleven remaining missing-box runs and links to sampled source sheets. The sheets show the source image with accepted near-player boxes in green and all raw person boxes in grey. This is a sampled visual audit; it does not certify every unsampled frame.

| Player and missing frames | Slots | Source-sample finding |
| --- | ---: | --- |
| [#9, 269–336](../data/processed/d79_new_source/named_gap_review/p9_269_336.jpg) | 68 | No accepted return after 268. A raw ID later surrounds a non-target player; it must not be stitched to #9. |
| [#15, 233–286](../data/processed/d79_new_source/named_gap_review/p15_233_286.jpg) | 54 | After raw ID 134 ends, #15 is near #23 and is not consistently distinct in sampled views until raw ID 202 starts at 287. |
| [#9, 95–136](../data/processed/d79_new_source/named_gap_review/p9_95_136.jpg) | 42 | Raw ID 30 overlaps #23 and #9 in the enlarged early frames; #9 is not distinctly enclosed until the accepted return at 137. |
| [#15, 149–183](../data/processed/d79_new_source/named_gap_review/p15_149_183.jpg) | 35 | The prior raw ID 4 ends at 148, while raw ID 134 starts at 184; sampled intermediate views do not establish a continuous distinct box. |
| [#23, 93–124](../data/processed/d79_new_source/named_gap_review/p23_93_124.jpg) | 32 | Raw ID 30 initially encloses #23, then overlaps both players before raw ID 7 returns on #23 at 125. The handoff point is not densely established. |
| [#4, 319–336](../data/processed/d79_new_source/named_gap_review/p4_319_336.jpg) | 18 | The candidate remains source-visible near the net in samples, amid jumping and overlap; raw ID 162 ends at 318. |
| [#4, 217–233](../data/processed/d79_new_source/named_gap_review/p4_217_233.jpg) | 17 | #14 is partly hidden by #8 in samples after raw ID 131 ends; no accepted successor until frame 234. |
| [#23, 195–209](../data/processed/d79_new_source/named_gap_review/p23_195_209.jpg) | 15 | #23 is largely behind #8 in enlarged source frames; no distinct raw box can be safely named. A separate box returns at 210. |
| [#4, 183–190](../data/processed/d79_new_source/named_gap_review/p4_183_190.jpg) | 8 | #14 is visible in samples but no source-checked raw handoff bridges frames 182 to 191. |
| [#4, 311–316](../data/processed/d79_new_source/named_gap_review/p4_311_316.jpg) | 6 | The player is visible during airborne overlap, while raw ID 162 is absent. No floor point is inferred. |
| [#4, 181](../data/processed/d79_new_source/named_gap_review/p4_181_181.jpg) | 1 | One-frame detector gap; surrounding accepted raw ID 3 boxes do not justify inventing a box at 181. |

Source sheets support **141 added box-only slots** outside the reviewed slice: #98's airborne serve (80–97), #23's clear return on raw ID 7 (125–147) and later partial overlap (210–215), #9's clear raw ID 30 return (137–147), #4's jersey-14 handoff (191–216) and late jump (305–310, 317–318), and #15 on raw ID 134 (184–232). The [#15 enlarged frames](../data/processed/d79_new_source/named_gap_review/p15_raw_detail_184.jpg) show raw ID 134 enclosing the jersey-15 player from 184 through sampled [200](../data/processed/d79_new_source/named_gap_review/p15_raw_detail_200.jpg) and [232](../data/processed/d79_new_source/named_gap_review/p15_raw_detail_232.jpg). The [early #9/#23 frames](../data/processed/d79_new_source/named_gap_review/p9_p23_raw_detail_137.jpg) distinguish raw ID 30 on #9 and raw ID 7 on #23 at 137 and [147](../data/processed/d79_new_source/named_gap_review/p9_p23_raw_detail_147.jpg). The [box policy](../data/processed/d79_new_source/named_near_box_policy.json) records these source-sampled extensions alongside #15's previously reviewed return. All box-only slots have null floor positions in the named output; the original grounded proxy and hold distances were not changed.

The next accuracy step is dense source review of the **157 unknown slots**, starting with the early #9/#23 exchange, #15's 149–183 gap, and #4's 181, 183–190 and 217–233 gaps. Where the player is distinguishable, attach only a source-confirmed box; where an overlap prevents a distinct assignment, keep the slot null and record that visibility state. Only after the denominator is known can a full-point visible-player coverage rate be reported. No far-side player annotation is required.
