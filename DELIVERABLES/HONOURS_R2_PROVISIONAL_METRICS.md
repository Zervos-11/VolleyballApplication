# R2 provisional team-metric demonstration

The [machine-readable demonstration](../data/processed/honours_r2_provisional_metric_demo.json) applies the three prespecified formulas to saved, **unreviewed** six-point candidates on frames 78050, 78100 and 78400. The [source screen](HONOURS_R2_CANDIDATE_SOURCE_REVIEW.md) makes the boxes plausible, but it does not independently verify every shoe-floor click or approve the court transform for final metrics. ProVolley won this point; UTS is near side. These values are **not** a losing-team outcome observation.

| Frame | Pairwise spacing (m) | Hull area (m²) | Centroid dispersion (m) | In-court sensitivity draws |
| ---: | ---: | ---: | ---: | ---: |
| 78050 | 4.540 | 20.062 | 3.105 | 2000/2000 |
| 78100 | 5.191 | 28.982 | 3.421 | 1526/2000 |
| 78400 | 5.154 | 30.774 | 3.426 | 2000/2000 |

Only **3/522 frames (0.57%)** of the saved point interval meet the nominal six-in-court geometry check. This fraction describes candidate availability, not validated tracking coverage. No rally median or win/loss comparison is published from it.

The JSON also gives 5th–95th percentile scenarios after independently perturbing each projected point within a **0.2 m radius** (2000 seeded draws per frame, excluding out-of-court draws). Those ranges are a hypothetical sensitivity check; they are not empirical error bars. The strict [final calculator](HONOURS_METRIC_INPUT.md) remains gated and has zero accepted R2 frames.

At frame 78100, 474 of 2000 perturbations put at least one player outside the strict court boundary. Its quoted quantiles are conditional on staying inside and should not be read as the full uncertainty range.
