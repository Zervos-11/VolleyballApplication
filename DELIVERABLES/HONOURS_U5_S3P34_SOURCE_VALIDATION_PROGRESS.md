# S3 P34 source validation progress

This point is the best current full-rally candidate. The [source review sheets](../data/matches/yt_u5HnY2aNW14/screening/s3p34_validation_review/) show the serve, every sixth frame through play, and every frame around the late point-ending transition. The [5 Hz ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reviewed_sample_ledger.json) preserves the exact sampled frame, source-image hash, six jersey slots, tracker box, accepted ground coordinate or null, and exclusion reason. It is an exploratory diagnostic, not final strict metric input.

## Event and identity review

- UCLA #12's jump serve is visible in frames 35986–36000. The ball-hand contact is not unambiguously visible at this resolution; frame 36000 is clearly after the serve. No exact start frame is certified.
- The ball is still travelling toward the left edge at frame 36138; players are disengaging by frame 36150. The point-ending contact, out crossing or whistle is not frame-certified. The bracket is 36138–36150, not a precise end frame.
- UCLA's near-side jerseys in the 5 Hz source sequence are #28, #12, #15, #7, #19 and #21. Raw IDs 9 and 78 intermittently overlap on UCLA #7 within frames 36117–36121; ID 78 fills frames where ID 9 is absent and becomes the sole late ID from 36122. Raw ID 39 is a far-side Concordia player incorrectly admitted by the geometric near-side gate. The corrected [candidate paths](../data/matches/yt_u5HnY2aNW14/screening/full_rally_candidate_paths.json) have all six candidate boxes in 104/138 screened frames, compared with 96/138 using only the original IDs. These remain unvalidated floor positions on unsampled frames.
- Across 771 adjacent-frame box pairs after this ID correction, the largest image-centre displacement is 19.65 px and none exceeds the 30 px diagnostic flag. This screens for abrupt tracker transfers; it does not replace visual jersey review at the unsampled frames.
- UCLA #21 and #15 are airborne around frames 36114–36120. Their box bottoms cannot be projected as observed floor positions. UCLA #7 has only one clear planted shoe at frame 36132, so a two-shoe midpoint reference there was excluded.

## Sampled position result

The source-reviewed diagnostic samples frames 36000–36138 every six frames (5 Hz). **126/144 individual player slots (87.5%)** have accepted grounded box-bottom proxies. **11/24 sampled team frames (45.8%)** have all six accepted; the other 13 receive no six-player metric because even one unavailable position fails the complete-team rule. The 13 exclusions comprise five serve/landing-contact frames for #12, three frames with a visible but unboxed player, three frames with airborne or occluded front players, one mixed missing-box/uncertain-landing frame, and one frame where #7 has a raised foot. The ledger identifies the same six jerseys throughout this sampled rally and records **no exclusion for a substitution or a player leaving the court**. The 45.8% figure is complete-team metric availability, not the proportion of players detected or the proportion of 30 fps source frames reviewed. Only every sixth source frame was sampled; dividing 11 by all 139 source frames would mix two denominators and should not be used as a detection rate.

Across the 11 eligible exploratory frames, the medians are mean pairwise spacing **4.858 m**, convex-hull area **26.137 m²**, and centroid dispersion **3.285 m**. These are diagnostic values under the staged transform, not final validated rally results. The [five manually marked six-player frames](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md) span early, middle and late play and contain 30 player comparisons: median proxy-to-mark difference **0.298 m**, maximum **0.595 m**. Three added frames were marked after the tracker boxes had been seen, so this is not an independent full-rally ground truth sample.

The held-out attack-line check in the [staged calibration](../data/matches/yt_u5HnY2aNW14/screening/near_court_candidate.json) has about **0.079 m** depth residual at both endpoints. The existing [camera registration](../data/matches/yt_u5HnY2aNW14/screening/selected_camera_registration.json) estimates **0.288 px** maximum static landmark shift at this point's frame 36072. These support a stable camera and plausible court geometry, but do not independently certify every player-floor projection. Calibration therefore remains staged for final metric use.

## Remaining validation boundary

This audit now documents source-reviewed **sampled** identity, a late tracker correction, explicit missing states, and distributed single-reviewer position checks. It does not establish exact full-rally boundaries or human-confirmed identity and ground contact at all 30 fps frames. The strict validated-rally metric count remains zero. A second independent court and position read, or an explicitly accepted single-reviewer tolerance in the thesis protocol, plus a source-reviewed fixed analysis window or exact event boundaries, is needed before promoting these results. A single rally cannot test an outcome association.

Reproduce with:

```powershell
.\.venv\Scripts\python.exe scripts/render_u5_s3p34_validation_review.py
.\.venv\Scripts\python.exe scripts/audit_u5_live_reference_frame.py
.\.venv\Scripts\python.exe scripts/build_u5_s3p34_reviewed_sample_ledger.py
.\.venv\Scripts\python.exe scripts/audit_u5_full_rally_trajectory_gate.py
```
