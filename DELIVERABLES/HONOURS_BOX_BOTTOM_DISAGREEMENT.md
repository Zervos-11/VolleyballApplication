# Saved foot-point versus box-bottom proxy disagreement

For each saved visible player with both a box and a foot-point marker, this [source-bound audit](../data/processed/honours_box_bottom_disagreement.json) compares the marker with the centre of the box's bottom edge. Both positions are projected through the staged court transform only when both remain inside its nominal 9 m square. The source-reviewed live subset uses the [phase audit](HONOURS_CANDIDATE_PHASE_QC.md).

| Subset | Player pairs | Median / 90th percentile image disagreement | In-court projected pairs | Median / 90th percentile nominal court disagreement |
| --- | ---: | ---: | ---: | ---: |
| All saved visible | 307 | 10.6 / 19.8 px | 290 | 0.41 / 0.74 m |
| Source-reviewed live frames | 48 | 10.8 / 22.6 px | 48 | 0.38 / 0.76 m |

These are **disagreements between two proposals**, not measured position errors: the saved foot clicks themselves were not independently ground-truthed, and some visible labels may include airborne or unusual posture. The metre figures also inherit staged-calibration uncertainty. A body/box centre remains appropriate as an explicitly image-plane movement proxy; box-bottom court metres should be released only after a small independent grounded reference check defines acceptable error.

On 8 source-reviewed live frames where all six saved markers **and** box-bottom proxies project inside the nominal court, changing the anchor changes the three provisional team measures by a median absolute **0.11 m** in mean spacing, **0.66 m²** in hull area, and **0.09 m** in centroid dispersion. The frame-level comparisons are in the JSON. These differences quantify proxy sensitivity, not either method's accuracy.
