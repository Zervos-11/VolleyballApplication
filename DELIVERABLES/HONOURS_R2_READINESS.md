# Honours R2 point readiness: set 2, point 2

This [source-bound audit](../data/processed/honours_r2_readiness.json) tests the saved R2 pilot against the three-team-metric gate. The score outcome is **ProVolley 2-0**, with the point to ProVolley. The annotator saved a boundary at **frames 78000-78521**, but independent boundary review remains pending. The [sample sheet](../data/processed/honours_sample_sheets/set_2_sample_navigation.jpg) shows this point in its first row.

The [saved player annotations](../data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json) contain **12 sparse frames** of the 522-frame interval, six named slots per saved frame, and **65/72** footpoints. All 12 frames remain marked `unreviewed`. The labels call 69 slots `away` and three `unknown`, but the source record does not verify home/away team identity; the [set-side map](../data/processed/honours_near_side_assignment.json) remains provisional.

The user [confirmed the proposed R2 starting setup](../data/processed/honours_r2_user_confirmation.json) as correct on 2 November. That reply did not name exact frames or certify individual foot clicks, visibility states, the full rally roster, or court landmarks. It records useful visual confirmation without changing the saved annotation review flags or the metric gates.

The [slot-42 source adjudication](../data/processed/honours_r2_roster_source_screen.json) resolves the overlap for the saved anchors: slot 42 follows near-side **UTS jersey #22**, visible in the [12-anchor sheet](../data/processed/honours_r2_slot42_source_sheets/saved_slot42_12_sparse_frames.jpg) and continuously across the [78100-78150 source sheets](../data/processed/honours_r2_slot42_source_sheets/frames_78139_78150.jpg). Its saved footpoint at 78100 lies by #22's shoe in the [saved-versus-raw overlay](../data/processed/honours_r2_slot42_overlap_78100.jpg). The assisted raw track 10 followed a **far-side blue player on frames 78100-78105**, whereas assisted track 221 follows near-side #22 on frames 78122-78150. Thus the historical [276-box continuity review](../data/processed/pilot_tracker_evaluation/dense_identity_validation_r2/visual_review.json) is not a 276/276 validation of intended player identities: at least those six assisted assignments are wrong. Saved slot 4 already covers near-side white/aqua jersey #2; saved slot IDs are not jersey numbers. The historical labels and tracker files were preserved, with this adjudication recorded as an erratum.

The [staged R2-R5 court transform](../data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json) projects **4** saved footpoints outside the nominal 9 m near court. The [four-frame source overlay](../data/processed/honours_r2_off_court_review.jpg) marks those saved points in red for inspection. Only **3/12 saved frames** have six candidate footpoints that project in court: **78050, 78100, 78400**. These are *candidate coordinates*, not accepted physical positions. The original held-out net-line check is reported in pixels; the court-metre conversion below is a line diagnostic. No independent player-floor position error or approval for metric use is recorded.

The overlay shows slot 1 at or beyond the **right sideline** on three sampled frames. This is plausible actual off-court movement, so its `x > 9 m` values do not by themselves imply bad footpoints. Slot 42 is UTS #22 near the net at frame 78300; its saved footpoint is only **3.3 source pixels** beyond the staged net boundary. That strict `y > 9 m` exclusion is sensitive to a small click or calibration change, not proof of wrong identity. The current strict metric gate excludes all four positions by design. If the research includes players outside the court, define that measure explicitly and validate homography extrapolation before changing the gate.

For this **R2 point only**, the near-side team is source-reviewed as **UTS**: near-side jerseys show UTS text, and the [boundary-side source sheet](../data/processed/honours_r2_boundary_side_spotcheck.jpg) supports a continuous side assignment through the sampled interval. The broader set-two side map remains provisional. ProVolley won this point, so a valid near-side spatial observation here would belong to the losing team.

The [12-frame label source screen](../data/processed/honours_r2_saved_label_source_screen.json) packages [all six saved slots](../data/processed/honours_r2_all_slots_source_sheets/saved_frames_01_04.jpg) and identifies status contradictions without rewriting the historical file: at frame **78500**, UTS #22 remains visible although saved slot 42 says `out_of_frame`; at **78521**, slot 7 has a short, crowded box and no verified floor point. Frames 78050 and 78100 look promising for a six-player still-frame check, but their footpoints have not been independently clicked. The [exact-frame ball sequence](../data/processed/honours_r2_boundary_close_78516_78525.jpg) shows the ball descending to the near-side floor around frames 78520-78522, supporting the saved 78522 exclusive end as plausible. The later score update is not a rally-end timestamp.

The [exact-frame candidate screen](HONOURS_R2_CANDIDATE_SOURCE_REVIEW.md) now inspects full-resolution boxes, shoe crops and court overlays at **78050, 78100 and 78400**. All six boxes visually correspond to near-side UTS players on each frame; shoe-level markers are plausible proposals, with overlap or stepping uncertainty near the net. The fitted court lines remain visually aligned on these exact frames. This source screen has not measured individual click error or changed any review gate.

A [versioned visibility draft](../data/processed/honours_r2_visibility_draft_manifest.json) corrects two source-visible but floor-unknown records: slot 42 at **78500** and slot 7 at **78521** move from `out_of_frame` to `uncertain` with partial occlusion. It adds no footpoints and keeps all 12 frames `unreviewed`. The historical saved annotations remain intact.

The held-out net line, projected into the staged court and evaluated at court x=0 and x=9, has depth residuals of **+0.013 m** and **+0.157 m** relative to y=9 m. This independent line diagnostic does not establish the error of player floor points or approve the homography for final metric use.

| Source frame | Saved footpoints | Inside staged court | Off-court player IDs |
| ---: | ---: | ---: | --- |
| 78000 | 5/6 | 5/6 | - |
| 78050 | 6/6 | 6/6 | - |
| 78100 | 6/6 | 6/6 | - |
| 78150 | 6/6 | 5/6 | 1 |
| 78200 | 6/6 | 5/6 | 1 |
| 78250 | 6/6 | 5/6 | 1 |
| 78300 | 5/6 | 4/6 | 42 |
| 78350 | 5/6 | 5/6 | - |
| 78400 | 6/6 | 6/6 | - |
| 78450 | 4/6 | 4/6 | - |
| 78500 | 5/6 | 5/6 | - |
| 78521 | 5/6 | 5/6 | - |

**Result:** slot 42 is source-adjudicated as near-side #22 at the dense anchors, but the strict [team-metric calculator](HONOURS_METRIC_INPUT.md) still has **zero validated R2 team-metric frames**. The three rows with six projected candidate points remain unreviewed positions, not validated formations. Do not calculate a win/loss spatial comparison from them. The next source work is to check the remaining roster slots, the four flagged projections and missing footpoints, independent court landmarks in metres, and a denser six-player floor-position record over a reviewed analysis interval. Preserve unknown or airborne states rather than filling them with still positions.
