# Honours contract alignment and next evidence gate

**Current status, 6 November 2026:** The [updated success-criteria audit](HONOURS_SUCCESS_CRITERIA_AUDIT.md)
finds criteria 1 through 6 met at research-prototype level and criterion 7's writing
content present in the [final thesis draft](HONOURS_U5_THESIS_FINAL_DRAFT.md).
The S1 P6 five-sample state record is complete with airborne floor coordinates
correctly null; four samples support six-player floor geometry. Its refined
mapping passed a frozen out-of-point court-line check. Author review,
institutional formatting, any required source-use clearance, supervisor review
and submission remain. The older work-order and evidence snapshots below
document the sequence of the project rather than the current completion state.

This audit uses the user-supplied **Honours Individual Learning Contract** (signed 11 August 2026) and the May 2026 draft titled *Player Tracking and Rotation/Coverage Analytics in Volleyball*. It supersedes the earlier suggestion that a complete broadcast-score result alone could satisfy the honours project. The project is a research prototype, and the contract requires player-position measurement and outcome analysis, not a commercial product.

The project scope explicitly anticipates video quality, camera angle, occlusion, identity and limited-dataset problems. The signed success criteria require court-coordinate data, manual-reference evaluation, calculated metrics and outcome comparisons, but do not require perfect automatic tracking or exact shoe positions in every frame. The current zero-window **strict gate** is a conservative high-confidence result, not a prohibition on an evaluated, uncertainty-aware proxy analysis. Any such analysis must keep image-space and court-space measures distinct and report missingness, error and sensitivity.

**Source update, 3 November 2026:** The user chose the elevated Concordia–UCLA video as the [primary analysis source](HONOURS_PRIMARY_SOURCE_SWITCH.md). Its score register and [18-point score-only frozen sample](HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md) are now built. The [primary methods/results draft](HONOURS_U5_PRIMARY_MANUSCRIPT_DRAFT.md) records the measured feasibility result and exploratory proxy comparisons. A selected non-anchor manual check is now available, but full dynamic position validation and a reliable outcome interpretation remain open. ProVolley-specific evidence below is retained as development history.

## Approved research questions

1. How can volleyball video be used to track players and create court-based movement data?
2. What metrics can describe team coverage, spacing, rotation, and transition movement?
3. How do coverage and rotation metrics relate to rally outcomes such as side-out success, rally length, and scoring patterns?
4. What limitations affect the reliability of player tracking in volleyball video?

These questions come from the supplied May draft. The learning contract permits scope refinement where findings or feasibility justify it, but no such change should be presented as already agreed.

## Evidence against the contract

The [seven-criterion audit](HONOURS_SUCCESS_CRITERIA_AUDIT.md) uses the student's stated success criteria directly. Criteria 1–6 have now been executed at research-prototype level: court-coordinate candidates and short paths are generated, selected positions are evaluated against manual shoe marks, three spatial metrics are calculated, an exploratory statistical outcome comparison is performed, and reliability is critiqued. This does not establish validated full-rally trajectories or a performance effect. Criterion 7 remains a working thesis draft pending author and academic review. The question is whether the measurement and selection limits permit a reliable interpretation, not whether the result is significant.

| Contract requirement | Evidence now | Status for final thesis |
| --- | --- | --- |
| Reproducible video and annotation method | Source records, score-balanced Concordia–UCLA sample, hashed feasibility ledger and review scripts | Met for the research prototype; thesis methods and source-use/privacy record need finalisation |
| Court-coordinate trajectories for selected rallies | Static image registration on 24 reviewed frames; local six-player boxes in 15 original-pass points and two higher-resolution recoveries; [full edited-clip export](HONOURS_U5_SELECTED_CLIP_COURT_COVERAGE.md) records raw court-coordinate candidates and missingness over all 18 selected clips; [fixed-box court proxy](HONOURS_U5_FIXED_BOX_COURT_PROXY.md) maps 240 candidate positions in eight source-screened short windows | Partly met as a prototype; only selected clear non-anchor positions have manual checks, and no full rally has six validated grounded trajectories |
| Tracking and mapping accuracy against manual reference | D79 development check; 30 clear-shoe single-reviewer primary-source comparisons, including 21 on held-out frames; [16 direct fixed-box anchor matches](HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md) with two complete team-frame comparisons; [11 non-anchor clear pairs](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) with five missing selected views; [one complete non-anchor team frame](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) with four additional marks | Bounded manual-reference evaluation met; broad dynamic accuracy, difficult contacts and independent inter-observer accuracy remain unmeasured |
| Three formally defined spatial or transition metrics, calculated consistently | [Strict calculator](HONOURS_METRIC_INPUT.md) implements three team metrics; [17-point image-plane screen](HONOURS_U5_IMAGE_PLANE_SNAPSHOT_SCREEN.md), [13-point phase-matched court-proxy screen](HONOURS_U5_PHASE_MATCHED_PROXY.md), and [eight five-sample fixed-box court-proxy windows](HONOURS_U5_FIXED_BOX_COURT_PROXY.md) exercise them | Met for the prototype's **at least three** spatial metrics; proxy validity, transition and rotation remain separate limitations |
| Statistical comparison of metrics with rally/point outcomes | Concordia–UCLA score-balanced 18-point sample, [eight-window within-set-and-phase proxy comparison](HONOURS_U5_FIXED_BOX_COURT_PROXY.md), exact conditional label reference, deletion and position-error scenarios, plus the 13-snapshot sensitivity comparison | Exploratory statistical comparison completed; availability selection, small matched cells and dynamic-position uncertainty prevent a reliable confirmatory association |
| Critical validity and reliability discussion | [Integrated working thesis draft](HONOURS_U5_THESIS_WORKING_DRAFT.md) covers detector failure, outcome-dependent run availability, image registration, measured shoe-proxy discrepancy, selection and generalisability | Prototype-level critical assessment completed; academic review remains |
| Complete thesis and research artefacts | [Integrated working thesis draft](HONOURS_U5_THESIS_WORKING_DRAFT.md), [primary methods/results record](HONOURS_U5_PRIMARY_MANUSCRIPT_DRAFT.md), [feasibility result](HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md), source-linked code | Draft assembled; author review, institution-specific presentation and source-use decision remain. Full selected-rally trajectories and reliable outcome inference remain unresolved |

## Minimum viable analysis design

Use **Concordia vs UCLA** as the primary outcome source. Its score register, set-side map and prespecified 18-point sample are built. Preserve those 18 selections and their missingness when reviewing exact starts/ends or narrower fixed analysis windows. Do not select rallies by whether a metric favours wins. The ProVolley-specific [score register](HONOURS_RESULTS_HANDOFF.md) and [side adjudication](HONOURS_NEAR_SIDE_SOURCE_ADJUDICATION.md) remain historical comparisons. Individual near-side membership through each interval, serving team, side-out, phase and rotation still require separate checks before those comparisons are attempted.

Use a single near-side team and a fixed six-player identity roster within each analysis interval. A metric frame requires all six players to have accepted court-floor positions; otherwise set that frame's team metric to null and report missingness. This strict denominator avoids silently treating an absent player as still or replacing a floor point with an upper-body box. If six-player coverage proves too sparse, report that failure and define a prespecified partial-coverage sensitivity analysis; do not mix partial and complete frames in one unlabelled result.

The [box-proxy availability screen](HONOURS_BOX_PROXY_AVAILABILITY.md) provides a separate, less precise measurement path. An image-plane box centre can track apparent player movement without an individually clicked shoe on every frame, provided it is reported in image units and checked for identity, clipping and posture changes. For court-coordinate metrics, a grounded box-bottom centre is a candidate floor-anchor proxy to validate against a small manual reference; a whole-body centre is above the floor and cannot be transformed by the floor homography as though it were a court point. The strict calculator now has an explicitly labelled `reviewed_grounded_box_bottom_proxy` mode for future source-reviewed inputs, separate from clicked floor contacts. The [sample disagreement audit](HONOURS_BOX_BOTTOM_DISAGREEMENT.md) measures proxy sensitivity but is not an independent error reference. The [targeted visual screen](HONOURS_MISSING_OUTCOME_VISUAL_SCREEN.md) finds two isolated set-three UTS-win six-box snapshots, not complete outcome-group trajectories.

The first three candidate team metrics are:

1. **Mean pairwise spacing (m):** for six accepted floor positions `p_i(t)`, average the 15 Euclidean distances `||p_i(t)-p_j(t)||` for `i<j` within frame `t`.
2. **Formation spread (m²):** area of the convex hull around those same six points within frame `t`. This describes geometric spread, not defensive quality or the area the team can actually reach.
3. **Centroid dispersion (m):** mean `||p_i(t)-c(t)||`, where `c(t)` is the mean of the six court positions. This describes compactness and can differ from pairwise spacing even when both use the same positions.

For each rally, summarise each metric using the median across eligible frames in a prespecified phase or window, and report the eligible-frame fraction. Compare winning and losing rallies with transparent group sizes and effect sizes; a permutation comparison should retain the set strata used in selection and should only be attempted with enough eligible rallies. With one match, these are within-match associations, not general volleyball effects or causal results. Rotation and transition are separate constructs: neither can be claimed from these three static metrics. A rotation analysis needs coded rotation states across multiple rallies; transition time needs reviewed phase boundaries and continuous positions.

## Work order

1. Build the new video's audited score register, then freeze a new sample from score evidence before spatial scoring. The earlier [18-point ProVolley review sample](HONOURS_RALLY_SAMPLE.md) remains frozen as historical work and must not be silently reused for Concordia–UCLA.
2. Review the chosen boundaries, near-side six-player identities and independent floor/court checkpoints. The first [R2 readiness audit](HONOURS_R2_READINESS.md) finds only 12 sparse, unreviewed frames, three with six candidate points projected inside the staged court, and no validated team-metric frame. Record every null state and mapping error in metres.
3. Use the [strict team-metric input](HONOURS_METRIC_INPUT.md) to calculate the three prespecified metrics only on eligible frames; report denominators, missingness and coordinate sensitivity (including at least the planned ±0.2 m perturbation).
4. Compare rally-level summaries with point winners only if both outcome groups have enough eligible rallies. Otherwise report feasibility and descriptive results without a significance claim.
5. Update the thesis using the approved research questions, sourced literature, a full methods account, results and critical discussion. Record the institution's source-use/privacy decision before distributing identifiable video or frames.

The latest [R2 source audit](HONOURS_R2_READINESS.md) resolves saved slot 42 as UTS #22 and supports the annotator's point end near frame 78522. It also finds a six-frame wrong-team assisted track, saved visibility contradictions, and only three sparse frames with six candidate in-court positions. The held-out net-line depth residual is 0.013 m at the left court edge and 0.157 m at the right; player-floor accuracy still has no independent reference. The later [completed-label audit](HONOURS_COMPLETED_SAMPLE_AUDIT.md) now includes all 18 selected points: 61/61 scheduled frames are saved and marked annotator-complete, 18 have six visible contacts, and 13 project six contacts inside the staged court. These are provisional sparse-frame observations, not final rally metrics.

The [sample-wide court calibration check](HONOURS_CALIBRATION_QC.md) registered all 61 saved frames. Its eight source-confirmed live snapshots pass a bounded geometry screen: fitted court-point image displacement is at most 0.497 px and the held-out net-line depth residual is at most 0.157 m. A late set-one point has an independently confirmed encoded-image alignment offset, although physical camera movement is unproven; its pre-serve candidate is excluded. This checks court geometry, not player floor-click accuracy, so it does not unlock final metric claims by itself.

The [R2 provisional metric demonstration](HONOURS_R2_PROVISIONAL_METRICS.md) executes all three formulas on the three six-point candidates and tests a hypothetical ±0.2 m floor-position perturbation. It covers 0.57% of that point interval and cannot establish a rally-level metric or a winner association. The strict final calculator remains gated.

The [sample-wide completion audit](HONOURS_COMPLETION_AUDIT.md) provides the current denominator for all 18 frozen points: 18 scored, 18 with linked scheduled player annotations, two with annotator-complete point boundaries, and none with a validated team-metric frame. This makes the contract's outcome-analysis gap explicit without disregarding the completed annotation work.

The existing [score draft](HONOURS_METHODS_RESULTS_DRAFT.md) is a results subsection, not a replacement for these contract outcomes.


