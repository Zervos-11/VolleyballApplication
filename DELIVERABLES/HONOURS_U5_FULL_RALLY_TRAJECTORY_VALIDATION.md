# Full-rally six-player trajectory validation gate

This audit joins the [cut register](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_clip_register.json), [source phase review](../data/matches/yt_u5HnY2aNW14/screening/event_transition_source_qc.json), [run identity review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md), [30 fps box audit](HONOURS_U5_TWO_RUNS_30FPS_AUDIT.md), [reviewed end brackets](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/source_event_brackets.json), and [manual six-player reference](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md). The [machine-readable join](../data/matches/yt_u5HnY2aNW14/screening/full_rally_trajectory_gate_audit.json) records input hashes and exact intervals.

| Point | Conservative live frames | In original 103-frame run | Outside original run | Box frames in original run | Manual six-player frames |
| --- | ---: | ---: | ---: | ---: | ---: |
| S1 P5 | 61 | 18 (29.5%) | 43 | 103/103 | 0 |
| S3 P34 | 121 | 102 (84.3%) | 19 | 93/103 | 5 |

The conservative live intervals are **approximations** from source-image review, not exact serve-contact and dead-ball frames. Even against those approximate intervals, neither dense run covers the full period. S1 P5's run contains setup before the conservative live start; S3 P34 starts just before that start and ends before the conservative live end.

The new 30 fps pass extends from the tracker anchor through the first reviewed post-point frame. For the span from each conservative start through the last reviewed live frame:

| Point | Analysed frames | Six original IDs | Six after reviewed ID correction | Frames missing an original ID | Unassigned extra ID frames | Last live / first post-point |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| S1 P5 | 108 | 63 | 63 | 45 | 15 | 1518 / 1530 |
| S3 P34 | 138 | 96 | 104 | 42 | 0 | 36138 / 36150 |

The [jersey-keyed candidate paths](../data/matches/yt_u5HnY2aNW14/screening/full_rally_candidate_paths.json) retain observed box-bottom candidates and explicit nulls. S3 P34 source review maps late raw ID 78 back to UCLA #7 where original ID 9 is absent and excludes far-side raw ID 39. This corrects candidate identity at the reviewed late transition, but does not make airborne box bottoms observed floor positions.

The 5 Hz review checks the six visible jerseys at 18 displayed samples per original run. Five [six-player manual references](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md) distributed across S3 P34 yield a median box-bottom to shoe difference of 0.298 m. Three of the five frames are supplementary unblinded checks; none are a second-reviewer reference. The [new sampled source ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reviewed_sample_ledger.json) accepts 11/24 5 Hz S3 P34 frames for exploratory six-grounded-player proxy metrics, with explicit exclusions. [Source frame 36120](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/frame_36120.png) shows front players airborne, making their box bottoms unsuitable as observed floor positions.

The [S3 P34 source validation progress](HONOURS_U5_S3P34_SOURCE_VALIDATION_PROGRESS.md) records the serve/end brackets, sampled exclusions, late jersey correction and staged calibration. Exact event frames and independent full-rally floor references remain open.

**Result: 0 full-rally six-player court trajectories validated.** The two runs remain useful short-span tracking diagnostics. The remaining validation requires exact live boundaries, source review of identity through the full interval, explicit gap handling, and multiple independent six-player position references including movement and occlusion. Missing positions must remain missing or clearly marked as estimates; they cannot count as observed accuracy.

Reproduce with `.\.venv\Scripts\python.exe scripts/audit_u5_full_rally_trajectory_gate.py`.
