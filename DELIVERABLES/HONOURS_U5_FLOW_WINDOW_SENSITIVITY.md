# Five-sample pixel comparison sensitivity

The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/flow_window_sensitivity.json) recomputes the exploratory equal-set-and-phase contrast after deleting each of the eight short windows in turn. It also singles out S1 P18, where a player is beyond the sideline, and S2 P28, where a player is low near the net. The [five-instant source review](HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md) found no obvious wrong-person transfer in either case, but it cannot validate court position or box-centre accuracy.

| Metric | All eight | Range after one-point deletion | Delete S1 P18 | Delete S2 P28 |
| --- | ---: | ---: | ---: | ---: |
| spacing_px | +36.503 | +12.306 to +59.268 | +30.608 (3 cells) | +37.935 (2 cells) |
| hull_area_px2 | -8166.551 | -14588.302 to -1744.800 | -14588.302 (3 cells) | -11349.737 (2 cells) |
| dispersion_px | +23.946 | +8.252 to +40.070 | +21.983 (3 cells) | +23.516 (2 cells) |

After a deletion, a set-and-phase cell contributes only if it still has both outcomes. Removing S2 P28 therefore removes the entire set-two offensive cell. The ranges reflect both point leverage and changing cell coverage; they are **not uncertainty intervals or significance tests**. These are pixel-space method diagnostics from selected windows. The validated court-trajectory count remains zero.

Reproduce with `python scripts/audit_u5_flow_window_sensitivity.py`.
