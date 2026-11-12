# Primary match switch: elevated Concordia–UCLA recording

**Current analysis status:** The [dense primary-match report](HONOURS_U5_DENSE_RESULTS_AND_READINESS.md) now covers all 18 frozen points at 5 Hz and includes provisional examples of all three team metrics. It records 0 validated six-player metric frames and 0 rally summaries. The earlier source screen and migration plan below describe how this match was selected; the dense report is the current readiness assessment.

**Decision (2 November 2026):** At the user's request, use [u5HnY2aNW14](https://www.youtube.com/watch?v=u5HnY2aNW14) as the *new primary analysis candidate*. The earlier ProVolley–UTS (`yt_FqE5pTJqx8g`) work remains a completed development and comparison record. Its 18-point frozen sample, labels, 123-point score register and results are not relabelled as observations of the new match.

## Source screen

The [full source manifest](../data/matches/yt_u5HnY2aNW14/primary_source_manifest.json) records the 21 min 40 s, 1280 × 720, 30 fps video (reported frame count 39,002 and SHA-256). Three independently downloaded six-second source sections were checked at requested times 0:00, 10:00 and 21:00. The [spot-check sheet](../data/matches/yt_u5HnY2aNW14/screening/whole_video_spotcheck.jpg) and [hash record](../data/matches/yt_u5HnY2aNW14/screening/whole_video_spotcheck.json) show the same elevated court view and scoreboard in all three sampled sections. The middle decoded frames show displayed scores 0–0 with set count 0–0, 12–10 with set count 1–0, and 23–15 with set count 2–0, respectively. This supports at least three set phases in the recording; it is not proof that no edits/cuts occur between spots.

The near-side uniform changes from blue at the first spot to white at the middle and back to blue at the final spot. Team names and the exact side-switch frames require source review before linking scores to near-side player metrics. The old ProVolley score-template bank cannot be applied to this different graphic without calibration and an independent score audit.

The [dense pilot](TOP_DOWN_BACKUP_VIDEO_SCREEN.md) gives 53 consecutive frames with six near-side gated boxes and stable raw IDs, while a net-jump interval loses two boxes before reconnecting. The staged court-line transform has no independently checked player-floor error. These are reasons to prioritise this source, not final outcome-analysis evidence.

## Score and prespecified sample now staged

The [minute strip](../data/matches/yt_u5HnY2aNW14/screening/score_minute_strip.jpg) shows a fixed score region through 22 minutes. A new [one-second pixel reader](../scripts/scan_u5_score_candidate.py) uses 22 manually read minute scores as digit templates. Its [candidate scan](../data/matches/yt_u5HnY2aNW14/screening/score_second_candidate.json) contains 1,300 source-second states. A separate [random twelve-frame sheet](../data/matches/yt_u5HnY2aNW14/screening/score_holdout_spotcheck.jpg), drawn without predicted values, was transcribed as [12/12 matching point scores](../data/matches/yt_u5HnY2aNW14/screening/score_holdout_review.json) by the same reviewer. This is a same-video spot check, not independent observer or cross-video accuracy.

The [candidate point register](../data/matches/yt_u5HnY2aNW14/screening/point_register_candidate.json) contains **122 displayed +1 score changes**: 37 in set one, 44 in set two and 41 in set three, plus two 0–0 set resets and no anomalous adjacent score transition. The last visible scores before those resets are 24–13 and 24–20; the recording ends with 24–17. Undisplayed possible final set points are **not inferred or sampled**. The score-change second is a navigation point after play, not a rally-end timestamp.

A [new score-only 18-point sample](../data/matches/yt_u5HnY2aNW14/screening/rally_sample_score_only.json) is frozen using seed `20261102`: three visible left-score winners and three visible right-score winners per set, sampled before spatial inspection of those selected points. If a selected point fails interval or position review, record the exclusion rather than replacing it by visibility.

The subsequent [selected-point source review](HONOURS_U5_SELECTED_POINT_SOURCE_REVIEW.md) confirms all 18 displayed +1 score transitions on adjacent source frames. The official UCLA result identifies the left score as UCLA and the right score as Concordia, and source context supports UCLA near in sets one and three and Concordia near in set two. A fixed three-frame-per-point detector screen has at least six permissively gated person proposals in 40/54 frames. A broader coarse live-core scan has 94/127 such seconds; visual anchor follow-up finds six distinct near-side boxes in 17/18 points. The one failure is a very short serve with the UCLA server still outside the near court. Exact rally boundaries, continuous roster identity and player-floor accuracy remain open.

## Migration rule

1. Source-check the new score register's selected point transitions, identify the school represented by each scoreboard side, and verify the set transitions and any correction.
2. Preserve the new score-only sample and the original 18-point ProVolley sample as separate frozen records; do not transfer selections or coordinates between matches.
3. Review exact source intervals, near-side six-player membership, side changes, phase and floor anchors. Use the existing three metric definitions and strict six-position eligibility rule. Report missingness by set and winner.
4. Rewrite the honours methods/results narrative using this match only after its outcome and movement data exist. Until then, existing numerical results are explicitly ProVolley-specific, and the new source is a promoted primary *candidate*, not a completed primary dataset.

This source switch changes the empirical match while retaining the agreed research questions and measurement definitions. It does not itself establish accuracy or a relationship between team movement and winning.
