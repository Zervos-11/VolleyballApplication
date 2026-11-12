# Supervisor scope decision brief

**Project:** Player Tracking and Rotation/Coverage Analytics in Volleyball  
**Primary analysis source:** fixed elevated Concordia–UCLA recording (`u5HnY2aNW14`)  
**Status:** contingency draft for supervisor review; no change to the signed 11 August 2026 learning contract has been approved. The original research-prototype scope remains the working plan.

## Current completion judgment (3 November 2026)

The **technical research prototype is implemented and reproducible** against success criteria 1–6 in the [criteria audit](HONOURS_SUCCESS_CRITERIA_AUDIT.md). The [integrated thesis](HONOURS_U5_THESIS_WORKING_DRAFT.md) remains a working draft, so criterion 7 and academic submission are not yet complete. The prototype reports eight short approximate court-position windows, three calculated team-geometry measures, an exploratory outcome comparison, manual position-error checks and explicit selected-clip missingness. These are the results to assess for the signed prototype scope.

The latest [full-clip tracklet audit](HONOURS_U5_FULL_CLIP_TRACKLET_AUDIT.md) screens all 1,005 selected five-Hz clip instants. An [every-sample visual review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) found six stable visible jerseys across 18 sampled frames in each of the two longest candidate spans. A separate [30-fps screen](HONOURS_U5_TWO_RUNS_30FPS_AUDIT.md) retained six near-side boxes in 103/103 source frames of one span and 93/103 in the other. The ten missing frames contain visible but unboxed teammates. Two [in-span manual shoe marks](HONOURS_U5_FULL_RUN_POSITION_REFERENCE.md) disagree with the corresponding box-bottom positions by 0.216 m and 0.523 m. These checks strengthen the reliability analysis but do not certify exact live-rally boundaries or complete six-player grounded trajectories.

**Recommended closeout:** retain the ten temporary detection misses as measured limitations and stop tuning that local case. Finish the thesis and obtain the supervisor's judgment on whether the evaluated short-path prototype meets the signed scope. If full-rally validated trajectories are required, the present result must be described as incomplete against that stronger requirement; no supervisor approval of a scope revision is recorded here.

## When a scope decision would be needed

The project does **not** require perfect tracking or a production-ready system. The supplied scope explicitly anticipates camera, occlusion, identity and dataset limitations, and the signed contract asks that these be evaluated. The current zero-window result comes from a conservative high-confidence analysis gate; it is not a rule that every player position must be an exact shoe click. The fixed-box proxy, mapped metrics, exploratory outcome comparison and selected non-anchor shoe-reference checks are now implemented. The next evidence task is to extend the reference to difficult contacts and more complete team frames, and state what the resulting uncertainty permits. The [seven success criteria](HONOURS_SUCCESS_CRITERIA_AUDIT.md) are audited separately; a statistically inconclusive comparison can still answer the research question.

If that evaluated proxy still cannot support a meaningful court-coordinate comparison, the supervisor decision would be: may the final thesis focus on **measurement feasibility and validity**, while reporting the planned outcome comparison as **not estimable on eligible data**? This remains a contingency, not the default scope.

## Alignment with the four original research questions

| Question | What the present work can answer | What remains open |
| --- | --- | --- |
| RQ1: court-based player movement from video | A fixed-court calibration and eight short fixed-box proxy paths now demonstrate approximate mapped movement; 11 selected non-anchor positions and one complete team frame have manual shoe checks. | Broader full-team dynamic floor accuracy and longer comparable trajectories are not yet evaluated. |
| RQ2: coverage, spacing, rotation and transition metrics | Spacing, formation spread, dispersion and short-window displacement proxies are calculated from the mapped positions. | Rotation and phase-confirmed transition measures remain unmeasured. |
| RQ3: relation of coverage and rotation to rally outcomes | Score-derived point outcomes, a balanced frozen sample and exploratory within-set-and-phase proxy comparisons are available. | Selected short windows cannot support a reliable coverage or rotation association with side-out, rally length or scoring patterns. |
| RQ4: tracking reliability limitations | The primary result documents detection, identity, phase, posture and floor-proxy limitations. | Broader manual reference and reliability checks would strengthen general claims. |

A hips-down or fixed-size player box can be a **defined lower-body movement proxy**. It would be relevant to RQ1 and the movement part of RQ2, but it is not itself a coverage or rotation measure for RQ3. Court-coordinate accuracy is a measurement question to evaluate against reference positions, not a demand for perfect shoe tracking on every frame.

## Completion path within the original prototype scope

1. Define a player position consistently, such as the floor anchor inferred from a fixed-size, hips-down box initialized on a clear grounded frame. Keep the image-space movement measure separate from the mapped court-position estimate. Flag jumps, exits, crossings and unobservable positions instead of inventing coordinates.
2. Evaluate the proxy on a manually marked reference subset, reporting positional error, missing positions and identity switches by phase and visibility. The existing clear-shoe checks provide a start; the evaluation must include difficult cases and should quantify uncertainty rather than require zero error.
3. Generate selected-rally court-coordinate trajectories with explicit missingness, then calculate coverage/spacing and at least one rotation or transition measure using prespecified live-play windows. Report the eligible fraction alongside every metric.
4. Compare the resulting rally-level metrics with point outcomes using the frozen sample, set and phase controls, effect sizes and sensitivity checks. An inconclusive or null association is a valid research result if the data and limitations are reported accurately.

## What the frozen sample establishes

The [primary feasibility result](HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md) retains **18 points selected from score evidence before spatial review**, balanced as three near-team wins and three losses per set. Six near-side teammates are source-visible at an instant in all 18 points. Across tested detector settings, 17 have one locally correct six-box frame. Eight have a source-membership-checked run of at least five 5 Hz samples: **one win and seven losses**. Camera-image registration is stable on 24 checked frames; a 30-box clear-shoe reference finds box-bottom to shoe-midpoint disagreement as large as **0.632 m** on the visible contacts reviewed.

The [image-plane screen](HONOURS_U5_IMAGE_PLANE_SNAPSHOT_SCREEN.md) calculates three box-centre geometry measures on **17 locally checked single frames**. It retains the missing winning point and shows how descriptive within-set contrasts change with detector recovery, image anchor and one-point removal. An [exact-frame phase audit](HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md) finds two serve/reset snapshots and only 13/18 frozen points in open-play set-by-phase cells containing both outcomes, with at most two snapshots per outcome per cell. The [matched-window pilot](HONOURS_U5_MATCHED_WINDOW_PILOT.md) confirms that airborne players can still have pixel-space box centres. Its initially fixed winning and losing windows, however, show different phases; a revised phase candidate was exploratory and has only one point per outcome.

The signed contract also asks for evaluated **court-coordinate player trajectories** and a statistical comparison with outcomes. No full rally or fixed window currently has six checked floor-position estimates through a comparable phase under the present conservative gate. The strict eligible set is **zero metric frames and zero windows**. The pixel-space contrasts alone cannot be presented as court-based performance effects. A defined, evaluated position proxy could support a more inclusive prototype analysis with its error and missingness stated explicitly.

The [phase-matched court-proxy diagnostic](HONOURS_U5_PHASE_MATCHED_PROXY.md) also calculates the three planned geometry formulas on 13 open-play single-frame proxies. Its small winning-minus-losing differences reverse sign when one higher-resolution recovery is removed, and an observed-error perturbation scenario spans zero for all three. This is a documented sensitivity result, not a reliable outcome association.

The [short optical-flow pilot](HONOURS_U5_BOX_CENTRE_FLOW_PILOT.md) extends the 17 reviewed six-box anchors across five image-plane samples. Four endpoint overlays remain uncertain at crossings or the net, and only eight candidate windows remain after phase and outcome balance checks. The method does not certify ground positions or resolve the signed trajectory requirement.

The [five-sample image-plane geometry diagnostic](HONOURS_U5_FLOW_WINDOW_GEOMETRY.md) uses those eight screened windows to calculate the three team formulas in pixels. A [five-instant source review](HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) found no obvious wrong-person transfer at the displayed instants in all eight. It is an exploratory temporal extension, with four wins and four losses, but still lacks validated court positions and a reliable winner-association design.

A [one-point deletion audit](HONOURS_U5_FLOW_WINDOW_SENSITIVITY.md) shows that the descriptive pixel differences depend strongly on the selected point and matched-cell coverage. Dropping S2 P28 removes the only winning point from its set-and-phase cell.

The [fixed-box court-position proxy pilot](HONOURS_U5_FIXED_BOX_COURT_PROXY.md) now implements the practical proxy proposed for the original scope: box dimensions remain fixed, their translated bottom points are mapped to approximate court coordinates, and the three geometry metrics are calculated on eight short windows. This is concrete progress beyond image pixels. A [non-anchor manual check](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) covers 11 selected clear shoe pairs and observes a maximum 0.729 m discrepancy. A [separate six-player frame check](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) reuses two marks and adds four; the fixed-box spacing exceeds manual shoe spacing by 0.431 m in that frame. The [updated sensitivity scenario](HONOURS_U5_DYNAMIC_ERROR_SENSITIVITY.md) uses the observed maximum. It remains exploratory because there is only one complete non-anchor team reference frame, five selected views are missing, and only three set-and-phase cells contain both outcomes.

A [direct anchor check](HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md) matches 16 pilot positions to existing manual clear-shoe marks, with complete six-player comparisons on two anchor frames. It quantifies a median 0.277 m positional discrepancy at those anchors. The non-anchor check covers selected clear positions and one complete team frame; the next accuracy gap is repeated complete six-player dynamic frames, especially difficult poses.

## Proposed revised contribution

**Research question:** How reliably can a fixed elevated volleyball recording supply six-player team-geometry measurements, and at which source, identity, phase and ground-position gates does a court-coordinate outcome comparison cease to be estimable?

The [primary methods/results draft](HONOURS_U5_PRIMARY_MANUSCRIPT_DRAFT.md), [attrition figure](figures/u5_primary_feasibility_attrition.pdf), source-linked review records and code would provide the empirical thesis foundation. The final manuscript would retain the score-balanced denominator, show all exclusion stages by set and point outcome, quantify position-proxy disagreement, distinguish pixels from court metres, and state explicitly that the planned winner association was not estimable. It would make no claim that spacing or coverage predicts winning.

## If the original analysis remains infeasible after proxy evaluation

The current matched pilot shows that raw-ID runs alone do not meet the original objectives. If the evaluated proxy still yields too few comparable winning and losing points, use the feasibility-focused question above as a proposed scope refinement. The supervisor would then review the evidence and decide whether to approve it.

**Decision record to complete after supervisor review:** approved scope, minimum evidence threshold if retaining the outcome analysis, date, and requested revisions. No supervisor response is recorded in this repository.
