# Honours research evidence package

**Primary case:** Concordia–UCLA, YouTube ID `u5HnY2aNW14`.  
**Local source:** [source_720p.mp4](../data/matches/yt_u5HnY2aNW14/source_720p.mp4), SHA-256 `da50eba82e7e9366eb7a93db169b42065dea790c3f335bf26397d9241a2f437b`.  
**Scope:** a single-camera research prototype for court-position and team-geometry measurement. This is an evidence map, not a claim that complete rallies or outcome effects were validated.

## What is in the primary analysis

| Level | Denominator and result | What it supports |
| --- | --- | --- |
| Frozen point sample | [18 score-selected points](../data/matches/yt_u5HnY2aNW14/screening/rally_sample_score_only.json): three near-team wins and three losses in each of three sets | A fixed denominator for feasibility and attrition. UCLA is near side in sets 1 and 3; Concordia is near side in set 2. |
| Source and detection | Six near-side players visible at a reviewed instant in 18/18 points; locally correct six-box instant in 15/18 initial points and 17/18 across tested detector settings | Local detector availability, not continuous identity. See [primary feasibility result](HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md). |
| Short court paths | [Eight selected 0.8 s windows](../data/matches/yt_u5HnY2aNW14/screening/fixed_box_court_proxy_pilot.json), 40 team frames and 240 approximate court positions | Implemented fixed-box motion proxy and three geometry formulas. Windows were selected partly by tracking availability; [pilot report](HONOURS_U5_FIXED_BOX_COURT_PROXY.md). |
| Outcome comparison | Four wins and four losses in three matched set-and-phase cells; exploratory win-minus-loss contrasts: spacing −0.089 m, hull area −4.212 m², dispersion −0.104 m | A sensitivity-tested descriptive comparison, not a reliable winner effect or confirmatory significance result. |
| Manual position reference | [Eleven selected non-anchor shoe pairs](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md), [one selected full-team non-anchor frame](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md), and [five selected in-rally six-player frames](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md) | Bounded proxy disagreement. The five S3 P34 frames contain 30 single-reviewer positions (median 0.298 m, max 0.595 m); three frames are unblinded. Neither maximum is a general error bound. |
| Longer candidate paths | [Two source-bracketed spans](HONOURS_U5_FULL_RALLY_TRAJECTORY_VALIDATION.md): six original IDs in 63/108 and 96/138 frames; corrected S3 P34 candidate IDs in 104/138 | Detector and identity diagnostics with explicit gaps. They are not six validated floor trajectories. |
| S3 P34 full-span review queue | [Thirty-fps paired source/box sheets](HONOURS_U5_S3P34_FULL_SPAN_REVIEW_QUEUE.md) for all 138 candidate frames, plus a frame/player review template | Localises 34 frames with one or more missing boxes and prepares source review. The new 30-fps review fields are still blank. |
| S3 P34 targeted gap source audit | [Nine missing-candidate runs](HONOURS_U5_S3P34_GAP_SOURCE_AUDIT.md), 48 missing jersey slots across 34 frames | All missing players remain source-visible in the paired views. Late front-court gaps include jumps or uncertain ground contact; no missing court coordinates were filled. |
| S3 P34 six-player observation ledger | [All 828 frame-player slots](HONOURS_U5_S3P34_SIX_PLAYER_OBSERVATION_LEDGER.md) over 138 frames | Joins candidate coordinates, 5 Hz grounded verdicts and targeted gap visibility. Unsampled tracker candidates remain provisional, and missing floor points remain null. |
| S3 P34 sampled ground status | [126/144 individual slots](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reviewed_sample_ledger.json) accepted (87.5%); 11/24 sampled frames have all six (45.8%) | Exploratory complete-team geometry at 5 Hz. One missing, airborne or uncertain player excludes a whole team frame. The 45.8% is not a per-player detection rate. |
| S3 P34 paired coarse movement | [Five-frame manual comparison](HONOURS_U5_S3P34_PAIRED_MOVEMENT_REFERENCE.md): 24 player-interval chords, 14.652 m manual and 14.538 m proxy sums; 0.066 m median absolute chord discrepancy | Direct selected-frame comparison. The signed total difference of −0.114 m contains cancellation and is not a full-rally error bar. |
| S3 P34 sampled movement sensitivity | [29.073 m of summed 5-Hz proxy chords](HONOURS_U5_S3P34_MOVEMENT_SENSITIVITY.md), including 2.873 m of gap bridges | A descriptive coordinate-path sum, not true foot travel. A stipulated 0.595 m per-position error radius gives a broad 0–171.873 m conditional discrete-chord range, not a confidence interval. |
| Strict full-rally result | [0 validated full-rally six-player trajectories](../data/matches/yt_u5HnY2aNW14/screening/full_rally_trajectory_gate_audit.json) | Exact play endpoints, continuous 30 fps identity, grounded positions and final court calibration are not jointly certified. |

The three metrics are mean pairwise spacing (metres), formation convex-hull area (square metres), and centroid dispersion (metres). Chord and sampled polyline lengths describe movement of estimated box-floor points; they are not counted steps or true foot travel. Rotation, verified side-out effects and phase-confirmed transitions were not measured.

## Data provenance and earlier work

| Material | Role in this thesis | Pool with primary outcome comparison? |
| --- | --- | --- |
| Concordia–UCLA `u5HnY2aNW14` | Primary score-frozen 18-point sample and all numbers above | Yes, subject to each analysis's stated eligibility. |
| ProVolley–UTS `yt_FqE5pTJqx8g` | Earlier annotation, interface and tracking development; [69 saved pilot frame records](HONOURS_PREVIOUS_WORK_REUSE.md) | No. It is a different match and sampling frame. |
| D79, AoEP and other transfer clips | Detector, identity and policy-transfer checks | No. They do not supply outcomes for the Concordia–UCLA sample. |

Raw source footage, annotation JSON, candidate tracks and reviewed position references have different evidential status. A tracker box is a candidate image observation; a source-reviewed grounded box bottom is an approximate court proxy; a manual shoe mark is a selected reference; a missing or airborne position stays null for grounded metrics. [Strict metric input rules](HONOURS_METRIC_INPUT.md) document the separate validated-rally gate.

## Reproduce and audit the package

Use Python 3.11 and the repository environment. [Research dependencies](../requirements-research.txt) add the computer-vision and plotting packages missing from the API-only requirements file. PyTorch CPU/GPU installation is platform-specific; the recorded local environment had `torch 2.9.1+cpu` and `torchvision 0.24.1+cpu`. No new model training is needed to inspect the saved results.

```powershell
.\.venv\Scripts\python.exe scripts/check_honours_evidence_package.py
.\.venv\Scripts\python.exe scripts/check_honours_evidence_package.py --hash-video
```

The first command is a read-only check of headline counts, the shared source identifier, key report links and video presence. The optional second command also hashes the full video file. It checks internal consistency; it does **not** independently reannotate video or establish scientific validity.

To regenerate the compact primary reports from saved source-linked data:

```powershell
.\.venv\Scripts\python.exe scripts/build_u5_primary_feasibility_result.py
.\.venv\Scripts\python.exe scripts/analyze_u5_fixed_box_court_proxy.py
.\.venv\Scripts\python.exe scripts/audit_u5_live_reference_frame.py
.\.venv\Scripts\python.exe scripts/build_u5_s3p34_reviewed_sample_ledger.py
.\.venv\Scripts\python.exe scripts/audit_u5_full_rally_trajectory_gate.py
.\.venv\Scripts\python.exe scripts/prepare_u5_s3p34_full_span_review.py
.\.venv\Scripts\python.exe scripts/build_u5_s3p34_six_player_observation_ledger.py
.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_paired_movement_reference.py
.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_movement_sensitivity.py
```

These scripts write regenerated reports or JSON and depend on existing screening outputs and manual QC records. Preserve the original manual annotations. The [revised thesis draft](HONOURS_U5_THESIS_FINAL_DRAFT.md) and [success-criteria audit](HONOURS_SUCCESS_CRITERIA_AUDIT.md) give the interpretation and limitations.
