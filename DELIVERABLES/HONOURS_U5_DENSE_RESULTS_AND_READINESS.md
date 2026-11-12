# UCLA–Concordia dense tracking and metric readiness

This is the new primary-source feasibility result for the [18-point score-only frozen sample](../data/matches/yt_u5HnY2aNW14/screening/rally_sample_score_only.json). The full local video is SHA-256 `da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b`. The earlier ProVolley–UTS outputs remain a separate development dataset.

## Edited rally clip boundaries

The recording already has hard edits between points. The [cut scanner](../scripts/scan_u5_rally_cuts.py) found **124 cuts**: exactly **122** align one-to-one with all visible +1 scoreboard changes and the other **2** align with set resets. On [source before/after sheets](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_boundary_review/), a [single-reviewer check](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_boundary_source_qc.json) confirms the edit bounds for all **18** frozen point clips. Every previously sampled dense tracking frame falls within its corresponding clip. The [full clip register](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_clip_register.json) supplies exact source-frame bounds for all 122 visible points.

| Set | Point | Clip start (s, inclusive) | Clip end (s, exclusive) | Duration (s) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 5 | 44.033 | 53.033 | 9.000 |
| 1 | 6 | 53.033 | 65.033 | 12.000 |
| 1 | 18 | 176.033 | 182.033 | 6.000 |
| 1 | 27 | 241.033 | 250.033 | 9.000 |
| 1 | 34 | 317.033 | 329.033 | 12.000 |
| 1 | 37 | 346.033 | 368.033 | 22.000 |
| 2 | 2 | 400.033 | 415.033 | 15.000 |
| 2 | 6 | 438.033 | 461.033 | 23.000 |
| 2 | 14 | 531.033 | 538.033 | 7.000 |
| 2 | 26 | 625.033 | 639.033 | 14.000 |
| 2 | 28 | 648.033 | 654.033 | 6.000 |
| 2 | 37 | 734.033 | 743.033 | 9.000 |
| 3 | 11 | 973.033 | 982.033 | 9.000 |
| 3 | 13 | 993.033 | 1003.033 | 10.000 |
| 3 | 23 | 1088.033 | 1095.033 | 7.000 |
| 3 | 27 | 1132.033 | 1143.033 | 11.000 |
| 3 | 33 | 1187.033 | 1197.033 | 10.000 |
| 3 | 34 | 1197.033 | 1207.033 | 10.000 |

These are edited **clip** boundaries, not serve-contact or dead-ball frames. The first and last portions of a clip may contain formation setup or celebration. The clip bounds should constrain tracking and review; only source-confirmed live frames should enter court metrics.

## Cut-bounded phase contamination check

The [anonymous six-box screen](../data/matches/yt_u5HnY2aNW14/screening/cut_bounded_provisional_rally_metrics.json) found **177** geometrically plausible candidate frames in **16** points, all within the edited clips. Source-image [review sheets](../data/matches/yt_u5HnY2aNW14/screening/provisional_core_review/) exposed **4 confirmed non-live candidates** in **3 points**: set-two point 28 includes a pre-serve frame and a post-point frame; set-two point 26 and set-three point 34 include post-point frames. The [counterexample register](../data/matches/yt_u5HnY2aNW14/screening/provisional_core_phase_counterexamples.json) records exact source frames and sheet hashes. This review covered only the illustrated examples, so the other candidate frames have not been cleared. The screen's per-point and winner-stratified medians are **quarantined** and must not be interpreted as rally metrics or outcome evidence.

The [18-clip phase review pack](../data/matches/yt_u5HnY2aNW14/screening/frozen_clip_phase_review/) now provides **219 source navigation frames** at one-second spacing, including the exact first and last source frames of each edited clip. This makes the pre-serve and post-point portions visible for interval review. One-second stills are navigation evidence; serve contact and dead ball still need closer source-frame or video review before an interval is certified.

A [single-reviewer phase bracket register](../data/matches/yt_u5HnY2aNW14/screening/coarse_phase_brackets.json) records pre-play, active-looking and post-play source marks for all **18** clips. The two shortest points use existing 5 Hz [focus sequences](../data/matches/yt_u5HnY2aNW14/screening/focus_phase_sequence/) to locate their brief exchange; both previously selected six-box navigation frames occur after the point. These marks are **coarse navigation brackets**, not exact serve/dead-ball decisions or continuous live-frame review. The [availability check](../data/matches/yt_u5HnY2aNW14/screening/coarse_phase_candidate_coverage.json) retains **126/177** geometric candidates across **15/18** points. It excludes all four documented non-live counterexamples. Within the narrow 5 Hz spans of the two short points, the existing dense screen has **0** frames with exactly six geometric near-side candidates. None of these retained candidates is a validated metric frame; frame-by-frame phase, team membership and ground positions remain open.

For one bracketed candidate per available point, the [unboxed source and detector overlay sheets](../data/matches/yt_u5HnY2aNW14/screening/bracketed_candidate_qc/) and [shoe-level crops](../data/matches/yt_u5HnY2aNW14/screening/selected_floor_qc/) were visually compared. The [corrected single-reviewer local QC](../data/matches/yt_u5HnY2aNW14/screening/bracketed_candidate_source_qc.json) records **15/15** selected instants with six correct near-side teammates. The original set-one point 37 frame 10722 included far-side white raw box 87; it was rejected after a [22-frame source review](../data/matches/yt_u5HnY2aNW14/screening/s1p37_replacement_review/) and replaced by live frame 10488, showing five blue UCLA players and white UCLA libero #28. This is a local membership check, not an independent reference or whole-rally identity trace. It does not validate box-bottom court positions or promote the 126 candidate frames to final results.

A [source-bound short identity audit](../data/matches/yt_u5HnY2aNW14/screening/s1p37_short_identity_run.json) now follows UCLA #1, #7, #12, #19, #21 and libero #28 through ten consecutive 5 Hz samples in set-one point 37 (1.8 s between first and last), with a largest same-ID box-bottom step of **0.709 m**. This confirms a short local six-player identity run; it does not validate floor-contact coordinates or the rest of that rally.

Across all 18 conservative live interiors, the [run availability audit](../data/matches/yt_u5HnY2aNW14/screening/interior_identity_run_availability.json) finds at least five consecutive six-ID samples in **7/18** points. Only the set-one point-37 short run has been source-checked for named jersey continuity; the other runs are detector proposals. None yet has validated grounded positions throughout.

All seven longer six-ID runs in the **original pass** are near-team losses (0 wins, 7 losses). That pass alone cannot support the contract's winner comparison. The separate higher-resolution winning-point pass is evaluated below.

The [full 5 Hz source sheets](../data/matches/yt_u5HnY2aNW14/screening/all_interior_run_frames/) were checked for those seven runs. The [run source audit](../data/matches/yt_u5HnY2aNW14/screening/interior_run_source_qc.json) finds six correct near-side teammates at all **53** displayed instants across **7/7** candidate runs. The frames between 5 Hz samples remain unobserved, named jersey continuity is certified only for set-one point 37, and no run has validated grounded coordinates.

The [winning-point short-run source review](../data/matches/yt_u5HnY2aNW14/screening/winning_short_run_source_qc.json) finds six correct near-side teammates in **10** sampled instants across **5/9** near-team wins. Three wins have no same-six candidate run in the conservative interior. The one-frame run at set-three point 33 is rejected: raw box 40 follows a far-side white player while a near-side blue player is missing. The separate selected frame 35844 for that point remains a locally correct six-box snapshot, but it does not repair this run. These short and unequal windows cannot be treated as a balanced rally-level comparison.

The [full-image source stills](../data/matches/yt_u5HnY2aNW14/screening/zero_run_source_review/) for those three detector-zero wins show all six near-side teammates in each point. The [source visibility audit](../data/matches/yt_u5HnY2aNW14/screening/zero_run_source_qc.json) covers **18** stills. Set-one point 18 has a player near the right sideline; the servers in set-two point 14 and set-three point 23 are airborne in early stills. These are recoverable detector gaps, but no continuous six-player track or grounded position is established for them. Counting visible players as measured court coordinates would overstate the evidence.

A [higher-resolution, lower-threshold detector pass](../data/matches/yt_u5HnY2aNW14/screening/zero_run_high_res_source_qc.json) recovers one locally correct six-box instant in each of set-one point 18 and set-two point 14. It leaves set-three point 23 unresolved because near-net overlap creates duplicate and merged boxes. Across tested detector settings, **17/18** frozen points now have at least one locally correct six-box instant. This is single-frame availability, not a six-player trajectory or validated ground measurement.

A separate [higher-resolution winning-point tracking screen](../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_screen.json) finds a 13-sample exact-six-ID run in set-three point 13. The [all-frame source check](../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_source_qc.json) identifies the same six UCLA teammates in all **13** displayed frames. Its first five samples span **0.8 s** of active-looking play; later samples may include point-end movement. Across tested settings, eight points have at least five six-ID samples (one near-team win, seven losses). No grounded floor positions or exact fixed analysis interval is certified for this new run.

The [joined visibility ledger](../data/matches/yt_u5HnY2aNW14/screening/source_visibility_ledger.json) accounts for **all 18 frozen points in the original pass**: 15 have one locally correct six-box instant and the other three show six teammates in source-only stills. The higher-resolution recovery above updates local box availability to 17/18. Both nine-point outcome groups have visible players. The missing final results stem from short or interrupted identity runs, unverified ground positions and uncertain exact intervals. The strict metric-frame count remains **zero**.

The [held-out shoe-reference audit](../data/matches/yt_u5HnY2aNW14/screening/heldout_box_floor_error.json) adds **21** clear grounded shoe-pair midpoints on four source frames across three sets, separate from the earlier nine reference boxes. Three unclear pairs were excluded. The median box-bottom discrepancy is **0.273 m**, with a maximum of **0.632 m**. These are approximate single-reviewer readings with about ±8 px visual uncertainty; clear shoe pairs underrepresent jumps and occlusions. The larger maximum shows that the earlier nine-box sample did not bound this proxy's error.

The [selected-frame proxy sensitivity audit](../data/matches/yt_u5HnY2aNW14/screening/selected_proxy_sensitivity.json) applies the three formulas to the **15** locally correct single-frame six-box snapshots (six near-team wins, nine losses). A deterministic perturbation probe moves each box-bottom court point by at most **0.632 m**, the largest discrepancy in the combined 30-box clear-shoe reference. Across snapshots, the median width between the 5th and 95th percentile perturbation values is **0.612 m** for spacing, **7.181 m²** for hull area and **0.417 m** for dispersion. This is a method-sensitivity demonstration, not a statistical confidence interval or a validated error bound. The snapshots were selected by box availability, three wins lack a locally correct six-box snapshot, and no full analysis window has passed ground and identity validation. The illustrative winner medians in the JSON must not be read as an outcome association.

The [source-image court registration audit](../data/matches/yt_u5HnY2aNW14/screening/selected_camera_registration.json) compares static floor features from the staged calibration excerpt with **24** source frames covering **18/18** frozen points. All **24** register, and the fitted displacement at six calibration/held-out landmarks is at most **0.293 px**. This supports reusing the fixed image coordinate system across those reviewed instants. It does not independently validate the four manually placed court corners, the held-out attack-line mark, or any player-floor anchor. Those distinct accuracy gates remain open.

The [5 Hz transition sheets](../data/matches/yt_u5HnY2aNW14/screening/event_transition_review/) cover serve and point-ending windows for all 18 frozen points (36 sheets). The [source-bound transition register](../data/matches/yt_u5HnY2aNW14/screening/event_transition_source_qc.json) records a conservative active-looking interior for each point. The server's action is in view for **9/18** points; exact contact is not frame-certified even there. Other serve contacts are outside the image or visually uncertain. These interiors exclude ambiguous starts and ends; they are not exact serve/dead-ball labels and do not pass the final boundary gate.

Geometric six-box candidate availability remains present in both frozen winner groups in every set, but coverage is uneven. The table is a review queue, not an outcome comparison. Winner side is the scoreboard side, and these counts are not validated metric frames.

| Set | Winner scoreboard side | Frozen points | Points with at least one bracketed six-box candidate |
| ---: | --- | --- | ---: |
| 1 | left | 5, 18, 27 | 2/3 |
| 1 | right | 6, 34, 37 | 3/3 |
| 2 | left | 2, 6, 26 | 3/3 |
| 2 | right | 14, 28, 37 | 2/3 |
| 3 | left | 13, 23, 33 | 2/3 |
| 3 | right | 11, 27, 34 | 3/3 |

## Reproducible screening

The [dense tracker](../scripts/screen_u5_dense_live_tracks.py) sampled the 18 source-reviewed coarse live cores at 5 Hz. YOLOv8n proposed people; ByteTrack supplied point-local raw IDs. A staged 9×9 m homography gated box bottoms, and the floor centreline under the net separated geometric near-side candidates from boundary cases. The [dense screen](../data/matches/yt_u5HnY2aNW14/screening/dense_live_track_screen.json) has **635 sampled frames**, of which **214** have six or more geometric candidates. Net-boundary review is needed in **74** dense frames. On the earlier one-frame-per-second screen, [source review](../data/matches/yt_u5HnY2aNW14/screening/net_boundary_adjudication.json) classified **18 far-side** and **10 near-side** boundary boxes; a hard line alone would lose real blockers.

The [continuity audit](../data/matches/yt_u5HnY2aNW14/screening/dense_live_continuity_audit.json) finds a same-six-raw-ID run of at least five sampled frames in **11/18** points. The [selected-frame roster diagnostic](../data/matches/yt_u5HnY2aNW14/screening/seeded_roster_coverage.json) finds those six selected raw IDs together in **83/635** sampled frames. Those raw IDs are not independently established jersey identities. Missing boxes remain missing; no stationary hold has been counted as measured position.

The [anchor-run audit](../data/matches/yt_u5HnY2aNW14/screening/anchor_live_window_availability.json) looks for an uninterrupted six-ID run containing each locally live selected frame. **6/16** local live anchors have at least five adjacent 5 Hz samples with the same six raw IDs, while **3** have only the anchor sample. This is availability around a reviewed instant; the other samples and identities have not been source-validated.

| Set | Point | Six geometric candidate frames | Longest same-six raw-ID run (5 Hz frames) | All selected raw IDs present | Anchor run frames | Selected time (s) | Selected-frame phase |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 5 | 10/25 | 9 | 9 | 9 | 47.4 | visible_live_play |
| 1 | 6 | 11/30 | 5 | 7 | 5 | 58.4 | visible_live_play |
| 1 | 18 | 5/20 | 3 | 1 | 1 | 179.0 | visible_live_play |
| 1 | 27 | 9/30 | 6 | 3 | 3 | 244.6 | visible_live_play |
| 1 | 34 | 12/35 | 7 | 3 | 3 | 322.4 | visible_live_play |
| 1 | 37 | 34/95 | 11 | 2 | 2 | 357.4 | visible_live_play |
| 2 | 2 | 18/55 | 9 | 9 | 9 | 410.4 | visible_live_play |
| 2 | 6 | 16/90 | 7 | 7 | 7 | 451.6 | visible_live_play |
| 2 | 14 | 6/10 | 6 | 6 | 6 | 535.8 | after_point |
| 2 | 26 | 20/55 | 7 | 2 | 2 | 631.4 | visible_live_play |
| 2 | 28 | 9/15 | 7 | 7 | 7 | 651.2 | visible_live_play |
| 2 | 37 | 8/25 | 2 | 1 | 1 | 739.8 | visible_live_play |
| 3 | 11 | 6/25 | 3 | 2 | 2 | 976.0 | visible_live_play |
| 3 | 13 | 9/25 | 4 | 6 | 1 | 997.6 | visible_live_play |
| 3 | 23 | 1/5 | 1 | 1 | 1 | 1092.8 | after_point |
| 3 | 27 | 13/35 | 3 | 3 | 3 | 1137.4 | visible_live_play |
| 3 | 33 | 10/35 | 3 | 3 | 3 | 1194.4 | visible_live_play |
| 3 | 34 | 17/25 | 9 | 11 | 9 | 1202.4 | visible_live_play |

The [source-image and motion review](../data/matches/yt_u5HnY2aNW14/screening/phase_six_candidate_review/) checked one six-box navigation frame per point. Seven [5 Hz focus sequences](../data/matches/yt_u5HnY2aNW14/screening/focus_phase_sequence/) resolved the three formerly uncertain instants and exposed a second after-point candidate at set-two point 14. The [phase register](../data/matches/yt_u5HnY2aNW14/screening/selected_phase_source_qc.json) marks **16 locally visible live**, **0 uncertain** and **2 after the point**. Set-three point 23's six-box frame is also after its short serve. Neither after-point frame can become a rally metric frame. These local decisions do not give exact serve-contact or dead-ball boundaries.

## Box-bottom court-position diagnostic

On [unboxed source crops](../data/matches/yt_u5HnY2aNW14/screening/floor_reference_crops/), one reviewer estimated the midpoint of two visible grounded shoes for **9** clear player boxes from two frames, including both near-side team colours. The [audit](../data/matches/yt_u5HnY2aNW14/screening/floor_proxy_reference_audit.json) finds median projected box-bottom disagreement **0.309 m** and maximum **0.442 m**. Pixel marks have roughly ±8 px reading uncertainty. Net jumps, clipping and occlusion were excluded from this small check. It is a local proxy diagnostic, not independent calibration validation or a declared acceptable-error threshold.

## Three metric formulas executed, with strict status retained

The [calculator](../scripts/compute_honours_team_metrics.py) implements mean pairwise spacing, convex-hull formation area and centroid dispersion. It now accepts either frozen match sample through `--sample` while still requiring reviewed boundaries, six named near-side players, validated calibration and reviewed ground positions. No U5 point currently passes that final gate.

As a method demonstration, [provisional snapshot values](../data/matches/yt_u5HnY2aNW14/screening/provisional_live_snapshot_metrics.json) were calculated from the six box-bottom projections in **15** locally screened live frames. One further locally live frame was excluded because a candidate projected outside the strict 9 m court. Each value is one availability-selected frame, not a rally median or phase-matched outcome observation.

| Set | Point | Near team result | Pairwise spacing (m) | Hull area (m²) | Centroid dispersion (m) |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 5 | win | 4.286 | 14.324 | 2.876 |
| 1 | 6 | loss | 4.541 | 23.335 | 3.070 |
| 1 | 27 | win | 4.410 | 19.397 | 2.915 |
| 1 | 34 | loss | 4.631 | 21.590 | 3.131 |
| 1 | 37 | loss | 3.865 | 14.854 | 2.376 |
| 2 | 2 | loss | 4.659 | 25.096 | 3.135 |
| 2 | 6 | loss | 4.256 | 21.014 | 2.868 |
| 2 | 26 | loss | 5.382 | 32.657 | 3.693 |
| 2 | 28 | win | 4.475 | 22.015 | 2.989 |
| 2 | 37 | win | 3.694 | 13.191 | 2.272 |
| 3 | 11 | loss | 5.320 | 23.646 | 3.484 |
| 3 | 13 | win | 4.368 | 21.280 | 2.943 |
| 3 | 27 | loss | 5.106 | 28.425 | 3.467 |
| 3 | 33 | win | 4.213 | 18.962 | 2.769 |
| 3 | 34 | loss | 4.885 | 26.526 | 3.300 |

Descriptive medians of these **provisional snapshots only**:

| Set | Near team result | Snapshots | Spacing (m) | Hull area (m²) | Dispersion (m) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | win | 2 | 4.348 | 16.860 | 2.896 |
| 1 | loss | 3 | 4.541 | 21.590 | 3.070 |
| 2 | win | 2 | 4.085 | 17.603 | 2.630 |
| 2 | loss | 3 | 4.659 | 25.096 | 3.135 |
| 3 | win | 2 | 4.290 | 20.121 | 2.856 |
| 3 | loss | 3 | 5.106 | 26.526 | 3.467 |

The values cannot establish that spacing or coverage predicts winning. The navigation frame was selected using box availability, selected phases differ, ground positions are proxies, and each set-by-result group has only two or three snapshots. No significance test is warranted. Rotation and transition movement were not measured by these three static formulas.

## Contract-level completion decision

**Validated six-player metric frames: 0. Validated rally summaries: 0. Outcome comparison from validated court metrics: unavailable.** The scoreboard result and method prototype are complete, but the signed spatial-outcome study is not yet empirically complete. The remaining source work is exact live interval review, six jersey identities through those intervals, player-ground proxy validation across net actions, and enough eligible frames in both winner groups. A reduced feasibility-only thesis would require an explicit academic scope decision; this report does not assume one.

## Focused source review queue

The table's selected times are direct navigation points in the local source video. Set-one point 18 is locally live but one of its six projected box bottoms falls outside the strict 9 m metric court. Set-two point 14 and set-three point 23 have after-point selected frames; both need a different live anchor or an explicit availability exclusion. For every retained point, establish the serve contact and dead ball from the video, confirm six near-side jersey identities across that interval, then review grounded box bottoms at the frames used for metrics. The existing raw IDs and provisional numbers are navigation aids; they do not substitute for those checks.

## Reproduce

From the project root, run these in order with `.\.venv\Scripts\python.exe`:

```text
scripts/scan_u5_rally_cuts.py
scripts/render_u5_cut_boundary_pairs.py
scripts/adjudicate_u5_cut_boundaries.py
scripts/screen_u5_dense_live_tracks.py
scripts/audit_u5_dense_continuity.py
scripts/render_u5_dense_continuity_review.py
scripts/screen_u5_six_candidate_phase.py
scripts/render_u5_phase_six_candidates.py
scripts/render_u5_phase_context.py
scripts/render_u5_uncertain_phase_context.py
scripts/render_u5_focus_phase_sequence.py
scripts/adjudicate_u5_selected_phase.py
scripts/audit_u5_seeded_roster_coverage.py
scripts/audit_u5_anchor_live_windows.py
scripts/render_u5_floor_reference_crops.py
scripts/audit_u5_floor_proxy_reference.py
scripts/build_u5_provisional_snapshot_metrics.py
scripts/build_u5_cut_bounded_provisional_rally_metrics.py
scripts/render_u5_provisional_core_review.py
scripts/audit_u5_provisional_core_phase.py
scripts/render_u5_frozen_clip_phase_review.py
scripts/adjudicate_u5_coarse_phase_brackets.py
scripts/render_u5_event_transition_sheets.py
scripts/audit_u5_event_transition_windows.py
scripts/screen_u5_coarse_phase_coverage.py
scripts/render_u5_bracketed_candidate_qc.py
scripts/adjudicate_u5_bracketed_candidate_qc.py
scripts/render_u5_selected_floor_qc.py
scripts/render_u5_s1p37_replacement_candidates.py
scripts/audit_u5_s1p37_identity_run.py
scripts/audit_u5_interior_identity_runs.py
scripts/render_u5_interior_run_review.py
scripts/render_u5_all_interior_run_frames.py
scripts/adjudicate_u5_interior_run_anchors.py
scripts/render_u5_winning_short_runs.py
scripts/adjudicate_u5_winning_short_runs.py
scripts/render_u5_zero_run_source.py
scripts/adjudicate_u5_zero_run_source.py
scripts/recover_u5_zero_run_detections.py
scripts/adjudicate_u5_zero_run_high_res.py
scripts/screen_u5_highres_winning_runs.py
scripts/render_u5_highres_winning_run_review.py
scripts/adjudicate_u5_highres_winning_run.py
scripts/build_u5_source_visibility_ledger.py
scripts/audit_u5_selected_proxy_sensitivity.py
scripts/render_u5_heldout_shoe_reference.py
scripts/audit_u5_heldout_box_floor_error.py
scripts/audit_u5_selected_camera_registration.py
scripts/build_u5_dense_results_report.py
```

The phase and shoe-reference scripts include explicit single-reviewer decisions. Re-running them reproduces the saved decisions; it does not create independent human validation.
