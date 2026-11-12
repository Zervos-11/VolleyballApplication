# S3 P34 sampled movement and uncertainty check

This calculation uses only the 24 source-reviewed 5 Hz frames in the [grounded-position ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_reviewed_sample_ledger.json). A point is used only when its jersey has an accepted grounded box-bottom proxy. It is an exploratory court-coordinate **proxy displacement**, not total physical player travel or a validated full-rally movement result.

| UCLA jersey | Accepted samples | Adjacent chords (m) | Bridges across missing samples (m) | First-to-last accepted chord (m) |
| --- | ---: | ---: | ---: | ---: |
| #28 | 24 | 7.080 | 0.000 | 3.117 |
| #12 | 19 | 3.406 | 0.000 | 1.872 |
| #15 | 20 | 1.790 | 0.564 | 0.549 |
| #7 | 21 | 4.751 | 0.497 | 1.262 |
| #19 | 24 | 4.771 | 0.000 | 4.265 |
| #21 | 18 | 4.403 | 1.811 | 0.579 |
| **Six-player sum** | **126** | **26.200** | **2.873** | **11.643** |

Team sums are calculated before rounding individual rows.

The adjacent and bridge columns sum to **29.073 m** across 120 accepted-position links. Six links bridge one or more unobserved 5 Hz samples. UCLA #12's first accepted position is frame 36030, after the initial serve/landing uncertainty; its earlier movement is absent from this calculation. Movement between any two samples can exceed their straight-line chord.

## What a ± allowance would mean

For two measured court points with assumed errors of at most \(\epsilon\) metres each, the error in their straight-line chord is at most \(2\epsilon\). Taking \(\epsilon=0.595\) m—the largest *observed* selected S3 P34 shoe-to-box discrepancy—as an illustrative per-point radius gives a conditional **0.000–171.873 m** range for the sum of the 120 discrete sampled chords. The largest measured single chord is only 0.936 m, smaller than the conditional 1.190 m error allowance for one chord. This bound is broad because errors can occur at every sampled point; 0.595 m is not a proven maximum error.

The six first-to-last accepted chords sum to **11.643 m**; under the same stipulated per-point radius, their conditional sum range is **5.756–18.783 m**. This describes net displacement between each player's first and last accepted sample, with different coverage for #12. It is not the distance travelled during the rally.

Neither range includes extra travel between samples, movement before or after accepted endpoints, an incorrect identity, or calibration error beyond the assumed point radius. Without a separately justified motion limit, the video does not provide a finite upper bound on actual travel through unseen intervals. A neat claim such as '29 m ± 1 m' would therefore overstate the evidence. The defensible presentation is the measured sampled proxy sum, the explicit missingness and conditional sensitivity, with actual total movement left unestimated.

[Machine-readable calculation](../data/matches/yt_u5HnY2aNW14/screening/s3p34_sampled_movement_sensitivity.json). Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_movement_sensitivity.py`.
