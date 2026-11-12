# S3 P34 single-reviewer validation protocol and result

The project has one available human reviewer. This protocol records what that review supports without treating the reviewer as independent of the tracker or changing the strict metric gate. The [reproducible audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_single_reviewer_protocol_audit.json) reads the frozen five-frame reference; it never rewrites manual QC marks.

## Review and reporting rules

1. Bind every source frame, manual mark and detector output to its existing file hash and source frame number. Keep the frozen 18-point score sample and all missing observations in their denominators. Do not replace a difficult frame with an easier one.
2. For any further shoe annotation, inspect the unboxed native-resolution source image first. Record a jersey as directly readable or sequence-inferred. Mark a floor point only when both shoe locations and apparent floor contact are readable; otherwise record `airborne`, `occluded`, or `uncertain` with a null coordinate. Record the reading uncertainty and the fact that the same reviewer has seen earlier tracker outputs. Preserve the original mark before displaying boxes.
3. Report the two existing frames marked before detector comparison separately from the three later unblinded frames. Do not relabel the earlier marks as independent observer measurements; they share the same reviewer and staged court transform. Do not pool the two groups as if they were independent rallies.
4. Compare each box-bottom court point with the manual shoe midpoint on the same frame, and report individual discrepancies and proxy-minus-manual team-metric differences. The 12–15 source-pixel per-axis reading uncertainty, selection by shoe visibility and shared calibration limit interpretation. Observed maxima are not upper error bounds. No post hoc threshold is used to declare the method accurate.
5. Keep 30-fps candidate boxes, sampled grounded proxies, manual shoe references, event brackets and court calibration as separate evidence fields. A source-sequence identity verdict does not establish floor contact. Missing or airborne positions stay null; interpolation cannot turn them into reviewed positions.
6. Grant a strict full-rally or fixed-window result only if its existing [input contract](HONOURS_METRIC_INPUT.md) is met and the source evidence supports each status assertion. A segment selected after seeing tracking availability remains diagnostic. Report failed gates explicitly; do not certify a rally by relaxing them after inspecting the result.

## Frozen reference audit

| Reference timing | Frames | Player pairs | Median discrepancy | Largest observed discrepancy |
| --- | --- | ---: | ---: | ---: |
| Unboxed marks before detector comparison | 36066, 36078 | 12 | 0.266 m | 0.418 m |
| Supplementary unblinded marks | 36036, 36096, 36138 | 18 | 0.3065 m | 0.595 m |
| All selected marks, descriptive only | Five frames in one point | 30 | 0.298 m | 0.595 m |

The pre-comparison frames have spacing discrepancies of +0.152 and +0.028 m; hull-area discrepancies of +1.303 and +0.050 m²; and dispersion discrepancies of +0.101 and +0.022 m. The supplementary frame values remain in the [five-frame source report](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md). These are selected *within-frame* proxy checks; they do not measure player error at every source frame or establish team-metric accuracy across rallies.

## Gate decision

The reviewer can support a **single-reviewer internal check of selected grounded positions and formation geometry**. The 30-fps pass subsequently marked all 180 intervening slots in the selected 36066–36102 segment grounded, with matching and plausible candidate boxes; the combined diagnostic segment has 37/37 complete source-reviewed team frames. The source event review still brackets the serve and point end; the four-corner calibration is staged; the larger candidate interval has 48 missing jersey-keyed box slots; and #15 is visibly airborne without a candidate at frame 36112. The segment was selected after tracking availability was known. Therefore the strict count remains **zero validated complete six-player rally trajectories and zero approved strict fixed-window results**. The single-reviewer choice does not supply inter-observer reliability or independent human adjudication of the AI-assisted identity sequence pass.

The unboxed [independent-review packet](../data/matches/yt_u5HnY2aNW14/screening/s3p34_independent_review_pack/README.md) remains blank. The dedicated [37-frame 30-fps packet](HONOURS_U5_S3P34_30FPS_GROUND_REVIEW_PROGRESS.md) now has a completed source-first 180-slot single-reviewer form and a [position comparison](HONOURS_U5_S3P34_30FPS_POSITION_COMPARISON.md). Reproduce this five-frame timing-stratified audit with `.\.venv\Scripts\python.exe scripts/audit_u5_s3p34_single_reviewer_protocol.py`.
