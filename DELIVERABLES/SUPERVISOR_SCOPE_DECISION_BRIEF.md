# Supervisor scope decision brief

**Project:** Player Tracking and Rotation/Coverage Analytics in Volleyball  
**Primary match:** Concordia–UCLA (`u5HnY2aNW14`)  
**Status:** research prototype implemented; thesis draft and supervisor scope judgment pending. No scope change has been approved.

## Decision requested

Does the evaluated **short-path court-position prototype**, with its measured errors and explicit tracking gaps, satisfy the signed research-prototype scope? Or must the final thesis include validated six-player trajectories through complete rallies?

## Evidence available now

| Component | Current result |
| --- | --- |
| Video method | Source-linked clips, score-only frozen sample of 18 points, fixed-camera court mapping and reproducible scripts. |
| Movement data | Eight screened 0.8-second windows contain 240 approximate player court positions; a separate full-clip pass records raw position candidates and gaps over all 18 selected clips. |
| Identity check | The two longest candidate spans retain the same six visible jerseys at every reviewed 5 Hz sample: 216 player crops, with no obvious sampled switch. |
| Dense tracking | Across 206 source frames in those spans, one has six boxes in 103/103 frames; the other has six in 93/103. In the ten missing frames, the teammates are visible but unboxed. |
| Live-interval coverage | Against the existing conservative live intervals, the dense runs cover 18/61 frames in S1 P5 and 102/121 in S3 P34. These intervals are approximate, and neither run spans one completely. |
| Position reference | Five in-rally six-player manual shoe frames span early, middle and late S3 P34 play. Median box-bottom discrepancy is 0.298 m across 30 positions; maximum is 0.595 m. Three added frames are unblinded single-reviewer checks. |
| Extended candidate paths | From each conservative live start through the last reviewed live frame, all six original raw IDs have boxes in 63/108 frames at S1 P5 and 96/138 at S3 P34. Missing positions remain null. |
| S3 P34 source follow-up | Late raw ID 78 is UCLA #7; raw ID 39 is a far-side player. A 5 Hz diagnostic accepts 11/24 sampled frames with six grounded box-bottom proxies, excluding missing and airborne positions. Exact event frames remain uncertain. |
| Analytics | Three team-geometry metrics and an exploratory win/loss comparison are calculated. The comparison is too small and availability-selected to establish a performance effect. |

The [success-criteria audit](HONOURS_SUCCESS_CRITERIA_AUDIT.md) assesses criteria 1–6 as met **at prototype level**. A [working thesis draft](HONOURS_U5_THESIS_WORKING_DRAFT.md) covers the research questions, methods, findings and limitations. Criterion 7 still needs the student's final review and submission formatting.

## Limit of the claim

The project does **not** currently validate complete six-player court trajectories for entire rallies, exact live-play boundaries, rotation changes, or a reliable relationship between positioning and outcomes. The ten short detector gaps are recorded as missing positions. The thesis must describe the short-path metrics as approximate and the outcome comparison as exploratory.

The [full-rally validation gate](HONOURS_U5_FULL_RALLY_TRAJECTORY_VALIDATION.md) and [S3 P34 follow-up](HONOURS_U5_S3P34_SOURCE_VALIDATION_PROGRESS.md) document the extended coverage, explicit missing positions, corrected late identity and five six-player manual reference frames. They still find zero validated full-rally trajectories.

## Recommended closeout

Use the [primary feasibility result](HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md) and [full-rally validation audit](HONOURS_U5_FULL_RALLY_TRAJECTORY_VALIDATION.md) in the thesis, then seek the supervisor's decision on the question above. If complete validated rally trajectories are required, that requirement remains unfinished and should be stated plainly. A narrower feasibility-focused thesis is only a proposed contingency until the supervisor approves it.

The [detailed evidence brief](SUPERVISOR_SCOPE_DECISION_BRIEF_DETAIL.md) preserves the earlier analysis and source links.
