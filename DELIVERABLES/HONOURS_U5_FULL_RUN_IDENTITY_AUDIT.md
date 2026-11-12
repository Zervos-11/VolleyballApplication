# Every-sample identity review of two selected raw runs

The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/full_run_identity_audit.json) reviews all 18 five-Hz source frames in each of the two longest same-six-ID candidate runs: **36 team frames and 216 person crops**. Six distinct UCLA jerseys remain associated with the same raw IDs at every displayed sample. White #28 is UCLA’s near-side libero. This is a single-reviewer visual continuity check, not a review of the five 30-fps frames between each pair of samples.

| Point | Source frames | Visible jersey numbers by raw ID | Obvious sampled switches |
| --- | --- | --- | ---: |
| S1 P5 | 1326–1428 (18 at 5 Hz) | 1→#12, 2→#28, 3→#7, 5→#8, 6→#21, 8→#19 | 0 |
| S3 P34 | 36000–36102 (18 at 5 Hz) | 1→#19, 2→#7, 8→#28, 11→#21, 20→#15, 25→#12 | 0 |

The six [S1 P5 crop pages](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s1_p05_all_samples_crops_1.png) and [S3 P34 crop pages](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_all_samples_crops_1.png) are indexed with hashes in the [atlas manifest](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/all_samples_crop_manifest.json). Each point has three six-frame pages. The audit records box-bottom court-proxy changes per ID as a motion diagnostic, not physical travel.

**Remaining accuracy limits:** exact serve-to-point-end intervals are not certified for these runs; the frames between 5 Hz samples could contain an unobserved swap or jump; and no manual shoe contact points were supplied for all 216 boxes. Prior [manual position checks](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) quantify selected proxy error elsewhere but do not validate these entire paths. The strict full-rally court-trajectory count remains **zero**.

Reproduce with `python scripts/render_u5_full_run_identity_atlas.py` and `python scripts/audit_u5_full_run_identity.py`.
