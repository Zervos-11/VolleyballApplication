# Candidate frame phase check

The [source-bound audit](../data/processed/honours_candidate_phase_qc.json) checks the 13 nominal six-player court candidates against five exact video frames around each candidate (up to 1.5 s either side at the recorded 50 fps). Linked sheets are visual evidence, and the original labels are untouched.

**Result:** 8 show live play, 3 are before the serve, 1 is between points, and 1 is uncertain at the end of play. The live snapshots cover 6 of the 18 frozen sampled points. Only 4 live snapshots have all six saved team fields consistent with the provisional side map. The other four live snapshots have 5 unknown fields between them, with no explicitly opposite-team fields. The source sheets show those boxes on the near side, but the provisional team-name mapping and player identity still need independent confirmation.

| Set | Point | Frame | Phase | Saved team fields | Source context and observation |
| ---: | ---: | ---: | --- | --- | --- |
| 1 | 2 | 8643 | live_play | unknown field(s) | [Ball travels above the court through adjacent frames.](../data/processed/honours_annotation_workspace/qc_context/s1_p2_f8643_context.jpg) |
| 1 | 7 | 15252 | pre_serve | unknown field(s) | [Both sides remain in starting positions; near-right player prepares the serve.](../data/processed/honours_annotation_workspace/qc_context/s1_p7_f15252_context.jpg) |
| 1 | 7 | 15505 | live_play | yes | [Ball and near-side reception/return movement continue across adjacent frames.](../data/processed/honours_annotation_workspace/qc_context/s1_p7_f15505_context.jpg) |
| 1 | 9 | 19345 | live_play | unknown field(s) | [Ball crosses near the net and the near side makes a defensive play.](../data/processed/honours_annotation_workspace/qc_context/s1_p9_f19345_context.jpg) |
| 1 | 9 | 19854 | uncertain_end_phase | yes | [Far-side player is already on the floor; adjacent frames do not establish whether the point ended before this instant.](../data/processed/honours_annotation_workspace/qc_context/s1_p9_f19854_context.jpg) |
| 1 | 23 | 36366 | live_play | yes | [Ball is in flight above the net with continuing play on both sides.](../data/processed/honours_annotation_workspace/qc_context/s1_p23_f36366_context.jpg) |
| 1 | 39 | 65656 | pre_serve | yes | [Near-side formation stays largely fixed while the far side prepares with the ball.](../data/processed/honours_annotation_workspace/qc_context/s1_p39_f65656_context.jpg) |
| 2 | 2 | 78050 | live_play | unknown field(s) | [Ball and both teams move through a continuing exchange.](../data/processed/honours_annotation_workspace/qc_context/s2_p2_f78050_context.jpg) |
| 2 | 2 | 78100 | live_play | yes | [Ball is airborne over the court during continuing exchange.](../data/processed/honours_annotation_workspace/qc_context/s2_p2_f78100_context.jpg) |
| 2 | 2 | 78400 | live_play | yes | [Ball is airborne over the court during continuing exchange.](../data/processed/honours_annotation_workspace/qc_context/s2_p2_f78400_context.jpg) |
| 2 | 12 | 90335 | between_points | yes | [Earlier ball drops near the near-side baseline, then a player handles it and both teams disperse; no live exchange at this instant.](../data/processed/honours_annotation_workspace/qc_context/s2_p12_f90335_context.jpg) |
| 2 | 21 | 102259 | pre_serve | yes | [Receiving posture remains fixed; ball enters the court only in later context frames.](../data/processed/honours_annotation_workspace/qc_context/s2_p21_f102259_context.jpg) |
| 3 | 27 | 187701 | live_play | unknown field(s) | [Net attack/block and subsequent ball trajectory show continuing play.](../data/processed/honours_annotation_workspace/qc_context/s3_p27_f187701_context.jpg) |

| Set | Winner | Points with live candidate / 3 sampled | Live candidate frames |
| ---: | --- | ---: | ---: |
| 1 | ProVolley | 3/3 | 3 |
| 1 | UTS | 1/3 | 1 |
| 2 | ProVolley | 1/3 | 3 |
| 2 | UTS | 0/3 | 0 |
| 3 | ProVolley | 1/3 | 1 |
| 3 | UTS | 0/3 | 0 |

These phase judgments remove pre-serve, between-point and uncertain-end frames from a rally-action analysis. The remaining nominal formula values are retained in the JSON solely for reproducibility. Camera calibration, exact floor contacts, team identity and comparable rally phases remain unvalidated. In sets 2 and 3 there are no UTS-won points with a live six-player candidate, so a set-stratified winner comparison cannot be estimated. Do not infer an outcome effect from the surviving snapshots or report their metre values as validated.
