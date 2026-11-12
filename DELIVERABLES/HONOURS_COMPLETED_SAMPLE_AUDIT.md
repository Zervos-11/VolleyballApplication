# Completed sample annotation audit

The [combined CSV export](../data/processed/honours_sample_annotations_provisional.csv) contains all 366 saved player rows over 61 frames. Its [manifest](../data/processed/honours_sample_annotations_export.json) records input and output hashes. Court coordinates in that CSV are nominal projections through staged transforms, not validated physical measurements.

The [source-bound JSON](../data/processed/honours_completed_sample_audit.json) confirms that all **61** scheduled frames across the frozen 18-point sample are saved and marked annotator-complete. This includes the 12 existing R2 frames and 49 newly labelled navigation frames. The labels are preserved; this audit does not edit them.

Only **18** frames have six marked visible contacts. Of those, **13** project all six points inside the nominal 9 m square under the staged calibration, across **9** points. The JSON gives formula outputs for these bounded candidates. They are provisional: source-floor click accuracy, set-wide calibration and near-side team identity are not independently validated, and the frames are too sparse to stand for whole rallies.

The saved home/away fields disagree with the provisional set-level near-side map or remain unknown on **16** frames. Only **8** projected six-player candidates have all six team fields consistent with that provisional map. This is a data-quality flag, not proof that the other boxes are opponents; the map itself is unverified for final outcome assignment.

Across the 13 nominal projected frames, the provisional formula ranges are **3.737–5.322 m** for mean pairwise spacing, **12.636–31.746 m²** for formation hull area, and **2.326–3.570 m** for centroid dispersion. These ranges describe where the formulas produced nominal values; they are not accuracy bounds or outcome effects.

| Set | Point | Winner | Saved/scheduled | Six visible contacts | Six nominal in-court projections |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2 | UTS | 1/1 | 1 | 1 |
| 1 | 7 | ProVolley | 3/3 | 2 | 2 |
| 1 | 9 | ProVolley | 3/3 | 2 | 2 |
| 1 | 23 | ProVolley | 3/3 | 1 | 1 |
| 1 | 32 | UTS | 3/3 | 0 | 0 |
| 1 | 39 | UTS | 3/3 | 1 | 1 |
| 2 | 2 | ProVolley | 12/12 | 6 | 3 |
| 2 | 8 | UTS | 3/3 | 0 | 0 |
| 2 | 12 | UTS | 3/3 | 1 | 1 |
| 2 | 14 | ProVolley | 3/3 | 0 | 0 |
| 2 | 21 | UTS | 3/3 | 1 | 1 |
| 2 | 33 | ProVolley | 3/3 | 1 | 0 |
| 3 | 5 | ProVolley | 3/3 | 1 | 0 |
| 3 | 11 | UTS | 3/3 | 0 | 0 |
| 3 | 21 | ProVolley | 3/3 | 0 | 0 |
| 3 | 27 | ProVolley | 3/3 | 1 | 1 |
| 3 | 37 | UTS | 3/3 | 0 | 0 |
| 3 | 38 | UTS | 3/3 | 0 | 0 |

| Set | Point winner | Points with a nominal six-player projection | Nominal frames | Frames with consistent team fields |
| ---: | --- | ---: | ---: | ---: |
| 1 | ProVolley | 3/3 | 5 | 3 |
| 1 | UTS | 2/3 | 2 | 1 |
| 2 | ProVolley | 1/3 | 3 | 2 |
| 2 | UTS | 2/3 | 2 | 2 |
| 3 | ProVolley | 1/3 | 1 | 0 |
| 3 | UTS | 0/3 | 0 | 0 |

Set 3 has no nominal six-player projected frame for a UTS-won point. This outcome-dependent missingness alone blocks a balanced within-set spatial comparison, even before phase and calibration checks.

**Interpretation:** The user's annotation task is complete for this schedule. Further manual redrawing is not the next automatic requirement. The remaining work is evidence validation and a decision about whether sparse navigation frames support the planned rally-level comparison. Do not report these provisional medians as final outcome metrics.
