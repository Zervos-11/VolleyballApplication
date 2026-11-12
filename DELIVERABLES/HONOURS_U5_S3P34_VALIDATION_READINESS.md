# S3 P34 strict validation readiness

The [machine-readable audit](../data/matches/yt_u5HnY2aNW14/screening/s3p34_validation_readiness.json) checks the current observation ledger, sampled and 30-fps single-reviewer ground review, staged calibration, event brackets and AI-assisted identity sequence review. It does not approve new court positions or a metric input.

| Gate | Current evidence | Decision |
| --- | --- | --- |
| Six near-side jerseys | Existing source roster review | Reviewed roster |
| Candidate continuity | 651 previously unsampled candidates visually checked in 47 paired sheets; no independent human adjudication | Sequence-level support only |
| Box availability | 104/138 frames contain all six candidates; 48 missing player slots | Incomplete |
| Ground points | The completed single-reviewer 30-fps candidate-interval review accepts 765/828 grounded box proxies and 93/138 all-six frames; the selected 37-frame segment remains complete | Whole candidate interval reviewed; exact full-rally floor path incomplete |
| Full-rally events | Serve contact unresolved; last live frame 36138 and first post-point frame 36150 | Exact interval unresolved |
| Court calibration | Four-corner transform with 0.079 m held-out attack-line residual; single-reviewer corners | Staged, not approved |
| Continuous six-grounded trajectory | #15 visibly airborne without a candidate at frame 36112 | Cannot pass current definition |

The longest consecutive six-candidate run is 36061–36106 (46 source frames). The longest run of complete *sampled grounded* frames is 36066–36102 at six-frame intervals: seven reviewed frames over a 37-source-frame span. All 37 frames have six candidate boxes; the single-reviewer 30-fps pass accepted all 180 intervening player slots, adding 30 complete diagnostic frames. This span was identified after checking candidate availability, so it is a diagnostic segment rather than a prespecified strict fixed window. The reviewer had previously seen tracker results, and these source-first annotations do not provide independent blinded adjudication.

**Result: zero validated full-rally trajectories and zero approved strict fixed-window results.** A six-player *observation* trajectory can retain airborne and missing states as null. To support a strict full-rally descriptive metric, exact event bounds and a court transform explicitly approved for metric use under a documented review protocol must be established, and each submitted metric frame needs six accepted grounded points. A continuous six-grounded-player trajectory across this rally is contradicted by the visible jump at frame 36112. The single-reviewer protocol supplies an internal selected-frame reference check; it does not convert the AI-assisted identity sequence verdict into an independently adjudicated human reference.

The [completed 138-frame review](HONOURS_U5_S3P34_FULL_30FPS_REVIEW_SCORE.md) joins 23 previously sampled frames, 30 dense frames and 85 newly exported frames. It records **780/828 original jersey-keyed candidate boxes**, **765/828 accepted grounded box proxies** and **93/138 frames with all six accepted proxies**. These proportions describe the source-bracketed candidate interval, not a serve-contact-to-dead-ball rally. The original scorer deliberately excludes newly diagnosed boundary-gate and higher-resolution boxes; [the separate #7 supplement](HONOURS_U5_S3P34_PLAYER7_BOX_CONFIRMATION.md) reports conditional box coverage only and does not add accepted floor points.

Reproduce with `.\.venv\Scripts\python.exe scripts/audit_u5_s3p34_validation_readiness.py`.
