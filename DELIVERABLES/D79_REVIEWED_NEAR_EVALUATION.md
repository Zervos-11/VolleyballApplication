# D79 reviewed near-side tracker evaluation

The user checked the player boxes and redrew incorrect suggestions in excerpt frames **240–289**. The frozen tracker was run before these labels were saved. [This reproducible evaluation](../scripts/evaluate_d79_reviewed_near.py) compares all raw detections with the checked near-side boxes using a one-to-one, maximum-IoU match on each frame. It does not use the saved proposal-origin links to choose matches. The [JSON result](../data/processed/d79_new_source/reviewed_near_evaluation.json) records source, prediction, and label hashes.

| Measure | Result |
| --- | ---: |
| Complete near-side review frames | 50/50 |
| Saved visible near-side boxes | 232 |
| Matched raw boxes at IoU ≥ 0.5 | 232/232 (100%) |
| Matched raw boxes at IoU ≥ 0.75 | 232/232 (100%) |
| Matched raw boxes at IoU ≥ 0.9 | 231/232 (99.6%) |
| Median / minimum matched IoU | 1.000 / 0.809 |
| Raw ID changes inside uninterrupted visible runs | 0 |

The 68 other near-player slots have no distinct saved box and are excluded from the box-match denominator. The user retained six named slots on every frame; #9 is occluded after frame 268, and #15 gets a distinct box only on frames 287–289. The frozen tracker has **660 person boxes across all 50 frames**, including people outside the target team. It emits unclassified person boxes rather than a final six-player near-team output, so this evaluation cannot calculate **near-team precision** from that raw file. A near-team prediction would count as a false positive whenever it fails to match one of the six checked target slots; no separate far-side player labels are needed for that check. The raw ID 2 return at frame 289 is a known identity failure: it encloses a non-target player and must not be joined to near-side #9.

**Interpretation:** This is a valid bounded agreement result against the user's human-verified near-side reference. The reviewer saw this tracker's suggestions while labeling and corrected errors, so the measurement is model-assisted rather than blind. It does not establish whole-match accuracy, near-team precision for a named six-player output, or physical movement accuracy. Far-side player tracking is outside the chosen product scope.

The user's confirmation is recorded in a [hash-bound review record](../data/matches/yt_D79JrsJsFgs/pilot/player_annotations/reviews/in_play_20m24_near.json). The [300-row near-side CSV](../data/processed/d79_new_source/near_reviewed_240_289.csv) now exports `reviewed` with the reviewer ID and retains `assisted` as its annotation source. If the saved JSON changes, the export falls back to `unreviewed` until the changed labels are checked again. The reviewed status certifies human inspection of this near-side slice; it does not certify blind annotation or physical court positions.

## Six-player near-team output

The [source-seeded identity plan](../data/processed/d79_new_source/prerally_identity_seed.json) and [box-only extension policy](../data/processed/d79_new_source/named_near_box_policy.json) generate a [257-frame six-player named-box output](../data/processed/d79_new_source/named_near_boxes_80_336.json). The #15 extension keeps raw ID 202 attached from frame 287 through 336 while leaving the floor position null; further source-sampled box-only segments cover #98's serve, #23's partial overlap, and #4's late jump. The existing feet-level hold and distance records remain unchanged. A [one-to-one evaluation](../scripts/evaluate_d79_named_near.py) scores every emitted box against the six checked target slots on those 50 frames; its [JSON result](../data/processed/d79_new_source/named_near_reviewed_evaluation.json) hashes the generated output and labels.

| Measure | Result |
| --- | ---: |
| Visible target boxes | 232 |
| Emitted named near-team boxes | 232 |
| Matched boxes at IoU ≥ 0.5 | 232 |
| Correct named identity among matches | 232/232 |
| Target-box recall on this slice | 232/232 (100%) |
| Precision of emitted named near-team boxes on this slice | 232/232 (100%) |
| Missed checked boxes | 0 |

Before the box-only extension, the conservative feet-level policy missed #15's checked boxes at frames 287–289 (229/232 target boxes). The new box output includes them without inventing floor contacts; its 232/232 result is a **regression check on frames used to make the fix**, not fresh held-out evidence. There are no false near-team assignments in this checked slice. The policy is source-seeded and the labels were model-assisted, so this result does not establish autonomous held-out performance, whole-point accuracy, or physical distance. No far-side player labels are required for this six-player target evaluation.

Across the **257-frame candidate point**, the generated output contains **1,246 accepted named boxes** in 1,542 player-frame slots; **36 frames** have six accepted boxes at once. The [full-point near-side QC](D79_FULL_POINT_NEAR_QC.md) lists the remaining 296 missing slots in eleven source-sampled runs. These are coverage counts of a conservative source-seeded policy, not accuracy measures outside the 50 reviewed frames. Missing slots retain null boxes, and box-only slots retain null floor positions.
