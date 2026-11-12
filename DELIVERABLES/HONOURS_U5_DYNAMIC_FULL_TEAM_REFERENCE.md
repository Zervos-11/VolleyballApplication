# One non-anchor full-team shoe reference

Set 3 point 13 at source frame 29952, 12 frames after the fixed-box anchor, shows all six near-side players with visually readable shoes. The [unboxed source frame](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_sheets/full_f29952.jpg) and [manual marks](../data/matches/yt_u5HnY2aNW14/screening/dynamic_full_team_manual_qc.json) support this bounded check. Two marks reuse the earlier non-anchor check; four were added after inspecting enlarged source crops. This is one approximate single-reviewer team frame.

![Six manual shoe midpoints in red and fixed-box proxies in green](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_sheets/s3_p13_full_team_checked.jpg)

The six position discrepancies have median **0.468 m** and maximum **0.626 m**. The table compares each team metric from the same six manual points and six fixed-box proxies.

| Metric | Manual shoes | Fixed-box proxy | Proxy minus manual |
| --- | ---: | ---: | ---: |
| Pairwise spacing (m) | 4.554 | 4.985 | +0.431 |
| Hull area (m²) | 23.577 | 27.768 | +4.190 |
| Centroid dispersion (m) | 3.060 | 3.368 | +0.308 |

Individual positions and source hashes are in the [audit JSON](../data/matches/yt_u5HnY2aNW14/screening/dynamic_full_team_reference_audit.json). The manual shoe midpoints have about ±12 source-pixel reading uncertainty per axis. This is a selected clear frame, not a random sample; it does not validate the other four instants of the window, identity through unsampled frames, or any full rally. It also does not make the outcome comparison confirmatory.

The adjacent +6-frame source image (frame 29946) was screened as a possible second team reference. Some shoe-to-floor contacts were ambiguous in that moving frame, so it was not counted as another complete grounded team frame.

Reproduce with `python scripts/audit_u5_dynamic_full_team_reference.py`.
