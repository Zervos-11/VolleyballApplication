# Local case-study results — 31 October 2026

Open the [local results page](http://127.0.0.1:8011/case-studies) for the two completed bounded examples. The [catalog](../data/processed/case_studies_catalog.json) binds each result to its source and case-study manifest by SHA-256.

| Source and scope | Approximate distances | Coverage and limits |
| --- | --- | --- |
| [R1 candidate point](R1_POINT_SUMMARY.md), 414 frames | Blue #9: 8.9 m after serve landing; blue #10: 9.72 m and blue #12: 13.95 m under the endpoint-chord rule; yellow #20: 8.5 m over candidate point | 2,025/2,484 usable named box slots; all six usable together on 108/414 frames. #11 and #13 have no estimate in the point summary. Point end is provisional. |
| [AoEP in-play slice](AOEP_CASE_STUDY_READOUT.md), 50 frames | Yellow #4: 1.0 m; navy #10: 5.4 m; yellow #5: 4.3 m; setter #18: 0.5 m after landing only | A selected slice of a highlights video, not a complete rally. #19 and Sam have no supported distance. |

The numbers are **development estimates** with their exact frame ranges in the catalog. R1 #10 uses a source-shoe chord across one detector gap; #12 uses source-anchored box-centre motion and straight endpoint chords across held gaps. Both omit unseen detours, and #12's first 20 candidate frames are excluded. R1 #20's full-point estimate changes from 6.4 to 12.0 m across the tested smoothing windows. AoEP's source and court calibration remain staged; its first dead-ball frame is unresolved. Neither study establishes full-match tracking accuracy, speed or independent ground-position accuracy.

An [optional R1 six-player proxy scenario](R1_D79_POLICY_TRANSFER.md) adds assumption-based box-bottom paths for #11/#13, chords over their missing spans, court-edge clipping and a stationary final hold for #13. Its six-player sum is **65.90 m**, with **62.01–82.85 m** obtained by changing only #11/#13's smoothing window. This spread shows why the figure is a model scenario, not a measured team distance; the main R1 player summary still leaves #11/#13 without source-supported estimates.

Both source records currently say `rights_status: pending` and `privacy_review_status: pending`. Keep this results page local. A public release or general full-match metric claim requires those project-owner decisions and evidence beyond these two bounded examples.
