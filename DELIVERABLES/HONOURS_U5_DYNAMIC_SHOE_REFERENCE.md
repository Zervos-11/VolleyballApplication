# Non-anchor manual shoe check for fixed-box paths

The [source crop index](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_sheets/) selects the frontmost and rearmost anchor boxes in each of eight short windows, then displays the unboxed source image 12 frames after the anchor. The [manual marks](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_manual_qc.json) record an approximate midpoint only when both shoes and ground contact appear clear. The [audit JSON](../data/matches/yt_u5HnY2aNW14/screening/dynamic_shoe_reference_audit.json) binds the crops, proxy and court calibration by hash.

Of 16 selected non-anchor player views, **11** have a usable single-reviewer shoe midpoint and **5** are missing because contact or identity is uncertain. The readable marks cover all eight short windows; this two-player-per-window subset has no complete six-player reference frame. A separate [one-frame team check](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) reuses two of these marks and adds four. Median point discrepancy is **0.216 m** and the maximum is **0.729 m** among the 11 accepted points. Approximate manual reading uncertainty is ±12 source pixels per axis.

| Point | Player key | Proxy-to-shoe discrepancy (m) | Review |
| --- | --- | ---: | --- |
| S1 P5 | 2 | 0.324 | Both foreground shoes visible. |
| S1 P5 | 6 | missing | Front player lunges and one shoe is obscured by the foreground teammate. |
| S1 P6 | 15 | 0.216 | Two front-row shoes visible near the UCLA logo. |
| S1 P6 | 4 | missing | Rear player's right shoe may be lifted; grounded midpoint uncertain. |
| S1 P18 | proposal_3 | missing | Front player overlaps another near the net; second shoe assignment uncertain. |
| S1 P18 | proposal_6 | 0.375 | Both shoes visible beyond the right sideline. |
| S2 P6 | 76 | 0.075 | Both rear-player shoes visible. |
| S2 P6 | 8 | 0.087 | Both front-row shoes visible; nearby players make the reading approximate. |
| S2 P28 | 12 | missing | Front player is low and obscured near the net; two grounded shoes cannot be assigned. |
| S2 P28 | 5 | 0.149 | Both rear-player shoes visible. |
| S3 P13 | 14 | 0.580 | Both front-row shoes visible. |
| S3 P13 | 2 | 0.553 | Both rear-player shoes visible. |
| S3 P27 | 17 | 0.134 | Both front-row shoes visible. |
| S3 P27 | 21 | missing | Rear player has one clearly visible shoe; the other is occluded behind the leg. |
| S3 P34 | 10 | 0.094 | Both front-row shoes visible. |
| S3 P34 | 2 | 0.729 | Both rear-player shoes visible. |

The earlier [anchor reference](HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md) has a 0.277 m median over 16 *different selected players*. Comparing these medians is not a direct drift estimate. The new marks are approximate, single-reviewer and not blinded to the identity crop. The evaluation excludes difficult contacts and does not validate all six players or full rallies. It does, however, measure the proposed fixed-box proxy away from its initialization frame and records failures as missing.

Reproduce with `python scripts/render_u5_dynamic_shoe_reference_sheets.py` and `python scripts/audit_u5_dynamic_shoe_reference.py`.
