# S1 P6 calibrated sampled-position diagnostic

The [frozen out-of-point calibration screen](HONOURS_U5_S1P6_CALIBRATION_CHECK.md) passed on all 12 court landmarks (maximum residual 0.0506 m). The same reviewer marked the source intersections and player shoes; this is an operational mapping check, not independent physical ground truth or formal strict metric approval.

All **five planned 5-Hz samples** have six source-reviewed player states. Four samples have six grounded shoe positions and paired same-player boxes, so their six-player floor geometry can be calculated. At the final sample, two blockers are observed airborne; their floor coordinates are structurally null and the six-player team metric is undefined there. This is a valid five-sample state record with four metric-eligible frames. The 20 intervening source frames have no per-frame ground-contact review, so this is not a certified 25-frame floor-position series.

| Frame | Grounded slots | Shoe spacing (m) | Shoe hull (m²) | Shoe dispersion (m) | Proxy − shoe spacing (m) | Proxy − shoe hull (m²) | Proxy − shoe dispersion (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1759 | 6 | 4.809 | 26.561 | 3.237 | +0.366 | +3.009 | +0.242 |
| 1765 | 6 | 5.133 | 30.308 | 3.455 | +0.150 | +1.258 | +0.106 |
| 1771 | 6 | 5.372 | 33.001 | 3.617 | +0.004 | -0.379 | +0.006 |
| 1777 | 6 | 5.654 | 36.883 | 3.810 | +0.034 | +0.570 | +0.021 |
| 1783 | 4 | — | — | — | — | — | — |

Across 28 paired grounded positions, the median shoe-to-box-bottom court distance is **0.423 m** and the largest observed distance is **0.902 m**. These are same-reviewer, sampled proxy discrepancies. They do not measure position accuracy at unreviewed frames or bound future errors.

At frame 1759, one reviewed grounded box-bottom proxy projects outside the 0–9 m court square; the shoe point does not. The diagnostic retains that proxy for a transparent discrepancy comparison. It would fail the current strict calculator’s in-court coordinate gate. An airborne state is an observed state, not a tracking failure or a position to fill by holding the previous floor point.

The [machine-readable diagnostic](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/calibrated_sample_diagnostic.json) contains all projected positions and input hashes. Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s1p6_calibrated_samples.py`.
