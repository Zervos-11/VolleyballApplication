# S1 P6 blocking-jump footprint sensitivity

At frame 1783, source slots 1 and 2 are airborne during a block. Both had grounded shoe clicks at frame 1777. Their earlier paired raw IDs remain present in the detector output at frame 1783, although the original paired-review page hid those boxes above its crude near-side cutoff. The table contrasts the earlier observed shoe points with the later airborne box bottoms.

| Source slot | Horizontal box-centre shift, 1777→1783 | Box-bottom rise | Mapped separation: last grounded shoe vs airborne box bottom |
| ---: | ---: | ---: | ---: |
| 1 | +12.65 px | 42.80 px | 0.869 m |
| 2 | -5.50 px | 32.40 px | 0.756 m |

The small horizontal centre shifts are consistent with a largely vertical blocking jump over these six frames. Projecting the raised box bottom as if it were a floor contact shifts the candidate court point substantially relative to the previous grounded shoe mark. That does not prove the foot location remained fixed: a blocker can drift or land elsewhere. Carrying the previous grounded point to frame 1783 would be an **imputed takeoff-location scenario**, not an observed 1783 position.

The metre differences use the exploratory refined transform, which has not passed the new out-of-point check. They are differences between proxy choices, not player travel, accuracy errors or uncertainty bounds. The strict frame remains null for the two airborne players. The [machine-readable result](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/block_takeoff_sensitivity.json) records source hashes and both proxy points.

Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s1p6_block_takeoff_sensitivity.py`.
