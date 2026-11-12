# D79 full-point development candidate

The earlier D79 near-side assisted labels cover excerpt frames **240–289**, or **0.817 s** between endpoint frames. Source-frame review now brackets a longer point: white #98 serves around frames **78–82**, and the ball reaches the near-left floor around **337–339**. A conservative active-play candidate is **frames 80–336 inclusive** (257 frames, 4.283 s). The [boundary record](../data/processed/d79_new_source/point_boundary_candidate.json) and [serve](../data/processed/d79_new_source/serve_left_source_sheet.jpg) / [end](../data/processed/d79_new_source/rally_end_source_sheet.jpg) sheets retain the evidence. The older saved 180–480 visual bracket includes post-point regrouping and is not used as a full-rally movement interval. The completed 240–289 labels remain unchanged and lie inside the candidate.

The frozen [full-point raw tracker run](../data/processed/d79_new_source/raw_point_candidate_80_336.json) processed every candidate frame after 25 warm-up frames and produced 3,544 person boxes. Its [anchor audit](../data/processed/d79_new_source/point_candidate_track_audit.json) matches all **232 visible saved boxes** in the checked slice at IoU ≥ 0.5. The annotator confirms they checked the boxes and redrew incorrect ones, so this is a valid bounded agreement result against a human-verified near-side reference. The reference was made with this tracker's suggestions visible; the result is not a blind or general detector-accuracy estimate.

| Saved near-side key | Candidate raw ID | Frames with that raw ID | Interpretation |
|---|---:|---:|---|
| #8 | 1 | 257/257 | Continuous source-sampled identity candidate. |
| #98 | 5 | 257/257 | Continuous source-sampled identity candidate, including serve. |
| #23 | 152 | 125/257 | Appears from frame 212; earlier identity unresolved. |
| #4 (jersey candidate 14) | 162 | 79/257 | Appears from frame 234; gap at 311–316; ends at 318. |
| #9 | 30 | 186/257 | 20-frame gap at 269–288; after it, the raw ID returns on a far-side player. Do not stitch. |
| #15 | 202 | 50/257 | Late raw track from frame 287; the separate named-box policy now also source-links raw ID 134 on frames 184–232. Feet-level positions remain withheld there. |

The [source-sampled #8/#98 sheet](../data/processed/d79_new_source/point_candidate_8_98_source_sheet.jpg) checks their boxes at the serve, middle, reviewed slice, and near the end. It supports visual identity continuity at those samples. It does not verify planted shoe locations on every frame; box bottoms are affected by stance, airborne action, and occlusion.

The [full-point near-side box QC](D79_FULL_POINT_NEAR_QC.md) is newer than this original raw-track table. It adds source-sampled named boxes without changing the grounded proxy or distance method, and records the remaining null-box runs explicitly.

## Bounded feet-level proxy

The [focused source review](../data/processed/d79_new_source/point_proxy_source_review.json) inspects #8's largest box-bottom changes and #98's serve landing. #8's sampled jumps at frames 212–215 and 312–323 occur with planted shoes and a shifting defensive stance. #98 is airborne through the serve; frame 97 is a landing transition, so the proxy starts at **98**. The review sheets are [#8 jumps](../data/processed/d79_new_source/p8_jump_source_sheet.jpg), [#98 jumps](../data/processed/d79_new_source/p98_jump_source_sheet.jpg), and [#98 landing](../data/processed/d79_new_source/p98_landing_98.jpg). These checks are sampled, not dense ground-contact labels.

The [reproducible proxy calculation](../data/processed/d79_new_source/point_candidate_proxy_distance.json) uses the centre x and bottom y of each raw person box at feet level, projects it through the provisional 9 m court geometry, takes a 15-frame coordinate-wise median, then sums adjacent steps. The [court map](../data/processed/d79_new_source/point_candidate_proxy_court_paths.jpg) and [per-frame CSV](../data/processed/d79_new_source/point_candidate_proxy_positions.csv) expose the paths.

| Player | Source frames | 15-frame proxy | 5–31-frame smoothing | Joint smoothing and court-line scenarios |
|---|---:|---:|---:|---:|
| #8 | 80–336 | **3.21 m** | 2.91–4.13 m | 2.63–5.02 m |
| #98 | 98–336 | **6.77 m** | 6.30–8.01 m | 5.34–10.06 m |

These are **development case-study estimates**, not validated physical travel or confidence intervals. In the 50 user-checked anchor frames, the raw box-bottom proxy differs from the selected foot point by 9.46 px median for #8 and 15.47 px for #98; corresponding 15-frame path totals also differ (0.59 vs 0.80 m for #8; 0.78 vs 1.07 m for #98). The proxy follows a consistent centre convention, but that mismatch and uninspected floor contacts remain material limits. The later [endpoint-based readout](D79_SEEDED_HOLD_READOUT.md) adds #23 and partial-scope #4/#15 candidate estimates; no six-player or team total is released. Regenerate this original pair with [build_d79_point_proxy_estimate.py](../scripts/build_d79_point_proxy_estimate.py).

## Practical next work

The [pre-rally identity and hold review](D79_SEEDED_HOLD_READOUT.md) now source-samples those handoffs. It preserves six player identities through ambiguous spans with explicit stationary display holds, catches the early #9/#23 raw-ID exchange, and rejects the far-side raw #9 return. Long holds leave movement unknown; they do not create four additional physical-distance figures.

Following the user's endpoint-distance convention, the newer readout also adds a straight chord between accepted positions on either side of a gap. It reports model-based box-bottom proxy estimates for #23 and partial-scope #4/#15; those numbers are not observed hidden paths or validated physical travel. The older #8/#98 table above is unchanged.

1. Resolve #23, #4, #9 and #15 ground positions during held spans if full-point paths are required. The current stationary display assumption does not establish that they stood still.
2. Confirm the court centre and attack lines against source pixels and replace sampled shoe review with continuous grounded foot-centre labels if validated physical travel is required.
3. The [named near-team evaluation](D79_REVIEWED_NEAR_EVALUATION.md) now scores a separate box output against the six human-verified target slots: **232/232** visible boxes match the correct named player. The box-only #15 extension fixes three misses on frames 287–289 while leaving feet-level positions unknown. This is an in-sample regression check, not new held-out evidence; no far-side player annotation is required for the chosen scope.

Regenerate the raw candidate with [build_d79_point_candidate.py](../scripts/build_d79_point_candidate.py) only in a fresh output location; the existing frozen file is protected. Regenerate the anchor audit with [audit_d79_point_candidate.py](../scripts/audit_d79_point_candidate.py).
