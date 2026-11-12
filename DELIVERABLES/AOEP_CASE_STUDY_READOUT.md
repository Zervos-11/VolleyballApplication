# AoEP 50-frame court-trace case study

## Scope and source

This development readout covers source frames **75180–75229** of `yt_AoEP-YiWRvc`, a 1280×720, nominal 59.94 fps highlights recording. The source SHA-256 is `2b762dfadcc1d725e9f08f3c376a22be276254499493a7af7674086b91910b44`. The fixed slice is visibly inside play. The exact serve/dead-ball boundaries for the surrounding point remain unresolved, as recorded in the [boundary recheck](../data/processed/aoep_new_source/boundary_recheck.json). This is a slice study, not a complete-rally result.

The [local case-study manifest](../data/processed/aoep_new_source/CASE_STUDY_MANIFEST.json) freezes hashes and sizes for the source and supporting files. It records **five partially saved near-side frames and zero complete frames** in this slice. The visual trace review below was performed on source sheets and frozen tracker candidates; it is not a completed independent annotation set. A separate [50-frame source-visibility audit](AOEP_SOURCE_SLICE_AUDIT.md) reports named-candidate gaps and agreement with six unblinded development anchors.

## Court-trace result

The [court map](../data/processed/aoep_new_source/candidate_court_paths_75180_75229_7e8d7ea5cd.jpg) projects the **bottom centre of a person box** through the staged [court calibration](../data/matches/yt_AoEP-YiWRvc/homography.json). The [underlying 50-frame record](../data/processed/aoep_new_source/candidate_court_paths_75180_75229_7e8d7ea5cd.json) binds the raw prediction, navigation, visibility, annotation and calibration hashes. Frozen YOLO/ByteTrack boxes and development visual-player links supply most of these points; only five frames have partial user-saved boxes.

| Near player | Provisional position samples | Trace status |
| --- | ---: | --- |
| Yellow #4 | 50/50 | One continuous candidate segment. |
| Navy libero #10 | 50/50 | Twelve motion discontinuities break the drawn trace. |
| Yellow setter #18 | 19/50 | Known airborne/landing interval withheld; two raw-ID segments afterward. |
| Yellow #5 | 3/50 strict; 50/50 within a 0.5 m boundary band | Same visible player along the left sideline; five box-bottom motion breaks. |
| Yellow #19 | 0/50 | Same visible player in 26 candidate boxes near the net; foot proxy unreliable and later 24-frame overlap gap. |
| Sam | 0/50 | Entry, missing boxes and right-edge cuts remain unresolved. |

The [six-frame source check](../data/processed/aoep_new_source/court_trace_source_checks_6frames.jpg) shows #4 and #10 boxes on the intended players at sampled frames. The [libero source pairs](../data/processed/aoep_new_source/libero_all_motion_breaks_source.jpg) show the same navy player across all 12 flagged steps. The [motion audit](../data/processed/aoep_new_source/libero_motion_break_audit.json) measures a largest one-frame projected jump of 0.85 m; five-frame median smoothing leaves four jumps above the broad 0.30 m review threshold. Box-bottom positions require smoothing for a provisional distance estimate and do not support a precise speed measurement.

## Source-reviewed coarse zones

All 50 frames were checked in the #4 source sheets ([first half](../data/processed/aoep_new_source/player4_source_qc_75180_75204.jpg), [second half](../data/processed/aoep_new_source/player4_source_qc_75205_75229.jpg)) and #10 source sheets ([first half](../data/processed/aoep_new_source/libero_source_qc_75180_75204.jpg), [second half](../data/processed/aoep_new_source/libero_source_qc_75205_75229.jpg)). The boxes stay on the intended visible players and their foot regions remain in frame. This is one development review of tracker-assisted boxes, not independent ground truth or exact shoe-contact annotation. The [zone record](../data/processed/aoep_new_source/two_player_zone_readout.json) binds the reviewed frames to the candidate path and calibration hashes.

The [3×3 court-zone view](../data/processed/aoep_new_source/two_player_zone_readout.jpg) gives a cautious spatial description. #4 falls in the central 3 m × 3 m zone on all **50** frames, each more than 0.30 m from a zone line in the projected coordinates. #10 falls in the right-middle zone on **28** frames and the right-front zone on **22**; **35/50** points lie more than 0.30 m from all zone lines. The other 15 are sensitive to modest projection or box-fit shifts, so the exact 28/22 split is diagnostic.

## Sideline and near-net review

The [#5 source sheets](../data/processed/aoep_new_source/player5_source_qc_75180_75204.jpg) ([second half](../data/processed/aoep_new_source/player5_source_qc_75205_75229.jpg)) show the same yellow player in all 50 raw boxes while he runs along the left sideline. The [sideline-band map](../data/processed/aoep_new_source/player5_sideline_band.jpg) and [record](../data/processed/aoep_new_source/player5_sideline_band.json) retain all 50 projected box bottoms within a **0.5 m boundary band**; only three lie inside the strict 9 m square. Five abrupt box-bottom steps remain flagged. A teammate stepping beside a line must not be relabelled as an opponent or deleted solely by a strict polygon check.

The #19 source sheets ([first half](../data/processed/aoep_new_source/player19_source_qc_75180_75192.jpg), [second half](../data/processed/aoep_new_source/player19_source_qc_75193_75205.jpg)) show the same near-net yellow player through frame 75205. His box bottoms project beyond the net line, and #4 increasingly hides his feet; after 75205 there is no distinct raw box through 75229. The identity slot remains represented, but no court path is inferred for him.

The [setter landing recheck](../data/processed/aoep_new_source/setter_landing_recheck.json) examines original source frames 75196–75215 and enlarged shoe crops. The first floor-contact frame remains indistinct, so frames 75202–75210 stay unknown and no extra court points were added.

## Provisional distance estimate

The [distance record](../data/processed/aoep_new_source/reviewed_distance_estimate_75180_75229.json) uses only intervals with a source-reviewed continuous visual player and a usable box-bottom position. It projects those positions through the staged homography, applies a centred five-frame median to reduce box-fit jitter, and sums the projected steps. The 3–7 frame range below shows how much the result changes with smoothing; it is **not a statistical confidence interval**.

| Player | Frames included | Approximate distance | 3–7 frame method range |
| --- | ---: | ---: | ---: |
| Yellow #4 | 75180–75229 | ~1.0 m | 0.9–1.1 m |
| Navy #10 | 75180–75229 | ~5.4 m | 5.1–6.5 m |
| Yellow #5 | 75180–75229 | ~4.3 m | 4.1–4.4 m |
| Setter #18 | 75211–75229 only | ~0.5 m | 0.4–0.7 m |

The [setter post-landing source sheet](../data/processed/aoep_new_source/setter_grounded_qc_75211_75229.jpg) confirms the same visible player across the raw-ID change at 75225. His airborne and uncertain landing frames are excluded, so 0.52 m is **not a full-slice total**. #19 has no reliable returning endpoint after his overlap gap; Sam's entry and approach lack reliable grounded court positions. Neither receives a metre distance. These estimates describe only this fixed 50-frame case-study slice and must not be extended to the surrounding rally.

The [saved-contact comparison](../data/processed/aoep_new_source/saved_floor_proxy_discrepancy.json) provides a scale check at frame 75180. Saved floor clicks and box bottoms differ by **0.14 m for #4**, **0.15 m for #10**, and **0.36 m for #5** after projection. These are differences between provisional markings, not measured position errors: the clicks have not been independently verified, and the setter's saved click conflicts with his airborne posture. A single frame cannot calibrate accumulated path error. The table therefore shows approximate tenths of a metre rather than precise hundredths.

A second [source crop check](../data/processed/aoep_new_source/floor_proxy_source_75205_75229.jpg), with [frame-level findings](../data/processed/aoep_new_source/floor_proxy_visual_qc_75205_75229.json), shows the box-bottom marker falling between #4's separated shoes at both 75205 and 75229. It is also offset from #5's planted shoe during a stride and from #10's shoe at 75205. Thus the table estimates **smoothed box-bottom path length**, which can differ from actual player travel as stance and box extent change. Its method ranges do not measure this bias. The values are useful for comparing this reviewed slice at coarse scale, but they are not validated distances or suitable for speed.

The available pose model was tested on the same [six player crops](../data/processed/aoep_new_source/pose_ankle_floor_proxy_75205_75229.jpg). Its [diagnostic record](../data/processed/aoep_new_source/pose_ankle_floor_proxy_75205_75229.json) shows ankle joints 17–25 pixels above the box bottom; direct ankle projection shifts the mapped location by 1.4–2.5 m in these samples. An ankle joint is not a floor-contact point. The optional `use_pose_ankles` processing setting now returns an explicit error until a shoe-floor method is validated; the default box-bottom path remains unchanged.

A small [pose-guided contact trial](../data/processed/aoep_new_source/pose_guided_contact_trial_75205_75229.jpg) uses the lower ankle's horizontal coordinate with the box-bottom height. The [trial record](../data/processed/aoep_new_source/pose_guided_contact_trial_75205_75229.json) shows 0.06–0.37 m shifts from the box-centre point. It often moves the marker closer to a visible shoe, especially for #4's wide stance, but it can still land below the sole and cannot identify a planted foot. A path that alternates between left and right shoes would also add stride motion to the distance. This trial is a contact-review cue only and does not alter the reported path estimates.

## Interpretation and release gate

The map and distance estimates are **provisional geometry**, not tracker accuracy or validated movement. #4, #10 and #5 have a single-reviewer source check across this slice; the setter has one across the reported post-landing segment. Other identity links remain development candidates. The court calibration has `use_for_metrics: false`, and box bottoms are unreliable for airborne, hidden or image-edge players. No speed, complete-rally distance or player-coverage metric is published here.

A defensible case-study metric would require a verified ground-contact/identity sequence over the chosen interval, review of the court-line assignment for metric use, and an explicit sample count and missing-position rate. A full-rally release also requires the first dead-ball frame. The [project status](PROJECT_STATUS.md) tracks the broader application gates.

The [focused endpoint and ground recheck](../data/processed/aoep_new_source/boundary_ground_recheck.json) inspected every source frame from 75294–75329 around the right side of the net. The ball-floor/dead-ball event is hidden by the player cluster; a later orange ball-like object cannot be tied confidently to the live exchange. The exact endpoint remains unset. Static upper-wall samples through frame 75340 shift by at most 0.53 pixel, supporting camera stability over this interval, but the reviewed shoe markers still lack independent floor-contact labels. The official rally selection and staged calibration remain unchanged.
