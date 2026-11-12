# S3 P34 paired coarse movement reference

This check compares the same four frame-to-frame straight-line court chords for each of six UCLA players, using the [five selected manual shoe-reference frames](HONOURS_U5_LIVE_SIX_PLAYER_REFERENCE.md). It is a selected **coarse displacement** check, not actual foot travel or a validated full-rally trajectory. The first compared frame is 36036 and the last is 36138; movement before, after and between these instants is not measured by the chords.

| UCLA jersey | Manual four-chord sum (m) | Proxy four-chord sum (m) | Proxy − manual (m) |
| --- | ---: | ---: | ---: |
| #28 | 3.742 | 3.719 | -0.023 |
| #12 | 2.494 | 2.482 | -0.013 |
| #15 | 1.364 | 1.370 | +0.006 |
| #7 | 2.161 | 1.947 | -0.214 |
| #19 | 3.154 | 3.335 | +0.181 |
| #21 | 1.736 | 1.684 | -0.051 |
| **Six-player total** | **14.652** | **14.538** | **-0.114** |

Totals are computed before individual-row rounding. Across the 24 player-interval chords, the median absolute paired discrepancy is **0.066 m**, the mean absolute discrepancy is **0.100 m** and the maximum is **0.377 m**. The small six-player signed difference reflects cancellation; it must not be used as a ± error bar for an entire rally.

| Source-frame interval | Manual six-player chord sum (m) | Proxy sum (m) | Proxy − manual (m) |
| --- | ---: | ---: | ---: |
| 36036–36066 | 5.154 | 5.545 | +0.391 |
| 36066–36078 | 1.032 | 1.315 | +0.283 |
| 36078–36096 | 2.247 | 1.745 | -0.503 |
| 36096–36138 | 6.219 | 5.933 | -0.286 |

The reference is approximate and visibility-selected. One reviewer marked all positions; only frames 36066 and 36078 were marked on unboxed images before box comparison, while the other three were unblinded supplements. The analysis cannot estimate an error distribution for all rally moments, especially jumps and missing boxes. For the thesis, use these direct paired discrepancies to describe the *selected coarse movement proxy*, alongside its coverage. Retain the separate [5 Hz sensitivity check](HONOURS_U5_S3P34_MOVEMENT_SENSITIVITY.md) to show why a frame-by-frame total and compact ± allowance are not supported.

[Machine-readable calculation](../data/matches/yt_u5HnY2aNW14/screening/s3p34_paired_movement_reference.json). Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_paired_movement_reference.py`.
