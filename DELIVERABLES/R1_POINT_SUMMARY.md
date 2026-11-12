# R1 point summary

The [local viewer](http://127.0.0.1:8011/r1-case-study) shows the final bounded case-study result for provisional source frames **21050–21463** (8.28 seconds at 50 fps). The [machine-readable summary](../data/processed/fqe_r1_boundary_recheck/r1_point_summary.json) records each player's usable box frames, gaps, and distance scope.

| Player | Usable candidate boxes | Unusable frames | Approximate distance |
| --- | ---: | ---: | --- |
| Blue #9 | 414/414 | 0 | **8.9 m**, frames 21070–21463, after serve landing |
| Blue #10 | 380/414 | 34 missing | **9.72 m**, frames 21050–21463, endpoint-chord estimate |
| Blue #11 | 311/414 | 103 missing | — |
| Blue #12 | 368/414 | 46 missing | **13.95 m**, frames 21070–21463, endpoint-chord estimate |
| Blue #13 | 142/414 | 272 missing | — |
| Yellow #20 | 410/414 | 4 truncated | **8.5 m**, full candidate point |

Across the six slots, **2,025/2,484** player-frame boxes are usable; **108/414** frames have all six usable boxes together. Box availability is a visual tracking measure, not checked floor-position coverage. Blank distance cells mean no defensible bounded path estimate for that player, not zero movement.

The [optional six-player proxy scenario](R1_D79_POLICY_TRANSFER.md) fills the blank #11/#13 cells only by assuming clipped box-bottom positions and straight endpoint chords. It totals **65.90 m**, but changing only those two players' smoothing window gives **62.01–82.85 m**. The table above keeps their source-supported distance cells blank because that scenario is too sensitive to be a measured physical team distance.

The #9 estimate uses a 15-frame median of the projected box-bottom centre. The [#10 estimate](R1_D79_POLICY_TRANSFER.md) adds an approximately 0.06 m source-shoe endpoint chord across one 34-frame gap to 9.66 m of visible smoothed box-bottom path; the ending shoe is partly obscured. The [#12 estimate](R1_D79_POLICY_TRANSFER.md) uses source-anchored box-centre translation in accepted segments and straight chords between endpoints of held gaps. It excludes the first 20 candidate frames. The 32-frame overlap contributes a 1.62 m chord. Both endpoint-chord estimates omit hidden detours under the agreed approximation rule. The #20 estimate uses the foot-level centre between two detected shoes where available and the box-bottom centre otherwise; four truncated-box frames are interpolated only for the diagnostic total. The [#20 path](../data/processed/fqe_r1_boundary_recheck/r1_p20_foot_level_center_path.png) and [per-frame record](../data/processed/fqe_r1_boundary_recheck/r1_p20_foot_level_center_distance_trial.json) expose that method. Five- to 31-frame smoothing changes the full-point #20 estimate from **12.0 m to 6.4 m**. The user accepted this accuracy level for an approximate case study.

These are source-specific development estimates under staged calibration and a provisional point end. They are not formal tracker accuracy, independently verified shoe-floor travel, or general match metrics. The [full readout](R1_CASE_STUDY_READOUT.md) explains the identity gaps and source checks; the [evidence manifest](../data/processed/fqe_r1_boundary_recheck/R1_CASE_STUDY_MANIFEST.json) binds the source and supporting files by SHA-256.
