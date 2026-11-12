# Draft decision for completing the honours study

**Status, 2 November 2026:** This is a draft for the project supervisor, not an approved change to the signed learning contract. The signed work asks for court-coordinate player tracking, three consistently calculated spatial or transition metrics, and a comparison with point outcomes. The source-bound [contract audit](HONOURS_CONTRACT_ALIGNMENT.md) remains the controlling statement of those requirements.

**Primary-source update:** The [Concordia–UCLA feasibility result](HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md) now supersedes the ProVolley development counts below for the outcome study. Its 18 score-only frozen points are balanced by set and near-team result. Six teammates are visible in source stills for all 18; 15 had a locally correct six-box frame in the original pass and two more had one after a higher-resolution detector recovery. Seven have a run of at least five six-ID samples in the original pass, all in near-team losses. A higher-resolution pass adds one source-checked 13-sample run in a winning point, with its first five samples appearing active. A camera-image registration check passes on 24 source frames across all points. A 30-box clear-shoe reference finds up to 0.632 m box-bottom disagreement. A new 66-sampled-frame motion diagnostic calculates all three formulas on source-membership-checked box-bottom proxies across eight runs, but an airborne player, unequal outcome coverage and unvalidated grounded positions keep every frame outside the strict metric gate. A matched 0.8 s win/loss pilot also failed phase and court-floor position gates, including a revised exploratory phase candidate. A full frozen-sample image-plane screen now has locally checked box-centre snapshots for 17/18 points, but one win is missing and snapshots were selected by availability and mixed play phase. No full rally or fixed window has validated six-player grounded positions, so the strict outcome comparison remains unestimable. The [primary methods/results draft](HONOURS_U5_PRIMARY_MANUSCRIPT_DRAFT.md) is ready as an honest empirical account; it is not an approved substitute for the original comparison.

## What is already defensible

- The earlier ProVolley vs UTS development match has an [automatic 123-point winner register](HONOURS_RESULTS_HANDOFF.md) across three sets, with same-video score checks and documented exceptions.
- Its separate 18-point sample was [frozen by set and winner](HONOURS_RALLY_SAMPLE.md) before spatial review. All 61 scheduled frames have saved annotations, but those are sparse navigation frames, not dense rally trajectories.
- The bounded [court geometry screen](HONOURS_CALIBRATION_QC.md) passed on eight live candidate frames. It does not measure player anchor error.
- The three team formulas are implemented in the [strict calculator](HONOURS_METRIC_INPUT.md). An [image-box version](HONOURS_SET3_IMAGE_PROXY_DEMO.md) now calculates the same geometry on three selected set-three snapshots in pixel units without individual shoe clicks.
- The [external phase-model trial](HONOURS_EXTERNAL_GAME_STATE_TRIAL.md) agreed with 11/12 certain source-reviewed instants. Its other saved-frame outputs are navigation proposals.
- A [source-image screen](HONOURS_MISSING_OUTCOME_VISUAL_SCREEN.md) demonstrated that six detector boxes can include duplicate or far-side boxes. It identified two isolated six-near-box snapshots among the missing set-three UTS-won points, while a saved ProVolley-won candidate in point 27 included a far-side opponent.
- A [proxy sensitivity audit](HONOURS_BOX_BOTTOM_DISAGREEMENT.md) found median 0.38 m nominal disagreement between grounded box-bottom proposals and saved foot markers in the source-reviewed live subset, with smaller median changes in the three provisional team metrics. It does not establish either anchor's independent accuracy. The strict calculator now accepts a separately labelled, reviewed grounded box-bottom mode.
- A [source-video side adjudication](HONOURS_NEAR_SIDE_SOURCE_ADJUDICATION.md) supports UTS near in set two and ProVolley near in sets one and three, using readable `UTS` lettering and uniform continuity. It does not validate every player's box.
- A [short-window detector screen](HONOURS_DENSE_PROXY_WINDOW_SCREEN.md) and [visual review](HONOURS_DENSE_PROXY_WINDOW_VISUAL_REVIEW.md) sampled two opposite-outcome set-three points across 4.0 s. Only 4/21 and 6/21 sampled frames had six filtered person proposals; later UTS-win proposals include opponents and miss near-side players. The box-centre shortcut therefore produces isolated examples, not the continuous six-player data needed for a rally comparison.

## Why the original outcome claim remains open

The current **Concordia–UCLA** strict court-metric denominator is **zero validated six-player frames**. The frozen 18 points are balanced by outcome, but the [image-plane screen](HONOURS_U5_IMAGE_PLANE_SNAPSHOT_SCREEN.md) has only 17 locally correct single-frame boxes, selected by availability and at different phases of play. The [matched-window pilot](HONOURS_U5_MATCHED_WINDOW_PILOT.md) found box centres usable in pixel space even when a player was airborne, but its initial win/loss windows were phase-mismatched and its revised pair was exploratory. Neither establishes a court-coordinate comparison. Court-floor position accuracy, continuous identity and a comparable analysis phase remain open. The earlier ProVolley set-three three-snapshot example is development history and does not repair this primary-match gap. Consequently no defensible outcome effect size, significance test or full-match distance claim follows from the present data.

## Route A: keep the signed outcome question

1. Preserve the frozen 18 points. Source-review each interval and a fixed phase/window rule without consulting its eventual metric value.
2. Build dense near-side player tracks through those windows. Verify six distinct near-side identities at a documented frame rate, retaining explicit missing, airborne and off-screen states.
3. Choose one position rule *before* analysis: validated grounded box-bottom centre for court metres, or box centre for image-plane movement. Check inter-observer or reference error on a small, separate set of frames; keep pixel and metre outputs separate.
4. Calculate the three prespecified metrics, report frame and point attrition by set and winner, then compare within sets only if both outcomes retain enough comparable points. Report null associations and exclusions honestly.

This route is still substantial video review and measurement work. Automation can propose boxes and phases, but the current screens show it cannot certify team membership or remove all occlusion without checking the source.

## Route B: request a feasibility-focused scope refinement

Retain the score reader, tracking prototype, calibration screen, metric definitions and frozen-sample attrition as the empirical contribution. State the primary conclusion as a **measurement-feasibility result**: what proportion of the planned sample survives each gate, which failure modes dominate, and what accuracy is achievable on bounded reviewed windows. Use the [17-point image-plane snapshot screen](HONOURS_U5_IMAGE_PLANE_SNAPSHOT_SCREEN.md) and [66-frame motion diagnostic](HONOURS_U5_RUN_MOTION_DIAGNOSTIC.md) as explicitly labelled implementation and sensitivity evidence, with their original denominators and phase caveats. Treat outcome association as a prespecified question that could not be estimated on eligible court-coordinate windows, not as a negative association result. This route requires the supervisor's explicit agreement that the revised deliverable meets the learning contract.

**Proposed revised question:** How reliably can a fixed elevated volleyball view supply six-player team-geometry measurements, and at which source, identity, phase and ground-position gates does an outcome comparison cease to be estimable? The frozen 18-point sample, per-outcome attrition, 17-point pixel-space screen, measured shoe-proxy discrepancy and strict zero-frame court-metric result would answer that question without interpreting availability-selected pixel differences as performance effects.

## Proposed supervisor question

> Given the measured attrition in the frozen 18-point sample and the lack of validated six-player rally trajectories, may the final thesis centre on a reproducible video-analysis feasibility evaluation, with automatic point outcomes and three spatial metric demonstrations, while reporting the planned outcome association as not estimable? If the original outcome comparison remains required, what minimum reviewed rally count and acceptable position-proxy error should the project target?

No supervisor decision, source-use permission or privacy clearance is recorded here. This draft is ready to review; it is not evidence that the original project is complete.




