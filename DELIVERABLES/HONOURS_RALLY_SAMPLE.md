# Frozen honours rally review sample

This [machine-readable sample](../data/processed/honours_rally_sample.json) was selected using the automatic **score and point-winner records only**, before scoring team-position metrics. It contains three ProVolley-won and three UTS-won points from each set (**18 points**), using seed `20261101` and simple random sampling without replacement within each set/winner group. The first visible 1-0 point and inferred set-one 25-15 point were ineligible because their changes were not directly shown. The JSON records input hashes and each group's selection probability.

| Set | Point | Score after | Winner | Video seek frames | Boundary status |
| --- | ---: | ---: | --- | ---: | --- |
| 1 | 2 | 1-1 | UTS | 8400-9000 | needs_source_review |
| 1 | 7 | 4-3 | ProVolley | 15000-15900 | needs_source_review |
| 1 | 9 | 5-4 | ProVolley | 17700-20100 | needs_source_review |
| 1 | 23 | 14-9 | ProVolley | 35700-37200 | needs_source_review |
| 1 | 32 | 20-12 | UTS | 54000-55500 | needs_source_review |
| 1 | 39 | 24-15 | UTS | 64800-66300 | needs_source_review |
| 2 | 2 | 2-0 | ProVolley | 77700-78900 | pilot_annotator_checked |
| 2 | 8 | 5-3 | UTS | 84600-85800 | needs_source_review |
| 2 | 12 | 6-6 | UTS | 89400-90600 | needs_source_review |
| 2 | 14 | 8-6 | ProVolley | 91800-93000 | needs_source_review |
| 2 | 21 | 12-9 | UTS | 101700-102900 | needs_source_review |
| 2 | 33 | 21-12 | ProVolley | 123600-126600 | needs_source_review |
| 3 | 5 | 5-0 | ProVolley | 154500-156000 | needs_source_review |
| 3 | 11 | 8-3 | UTS | 162000-163200 | needs_source_review |
| 3 | 21 | 15-6 | ProVolley | 177000-178200 | needs_source_review |
| 3 | 27 | 18-9 | ProVolley | 186900-188400 | needs_source_review |
| 3 | 37 | 21-16 | UTS | 204000-204900 | needs_source_review |
| 3 | 38 | 21-17 | UTS | 204900-206100 | needs_source_review |

The seek frames are navigation aids; they are **not accepted rally boundaries**. The [source-frame screen](HONOURS_SAMPLE_SCREEN.md) provides three local stills per point and shows that the near-side uniforms change between sets. Every sampled point still needs source review for rally interval, near-side team and player identities, floor positions and calibration before it can contribute to a spatial metric. The sample is a target, not a claim that 18 analyzable rallies exist. Preserve exclusions and reasons; do not replace difficult rallies simply because tracking fails. Score winner alone does not establish near-side outcome, serving team, side-out, rotation or phase.

This is a balanced within-match development sample. It is not an unbiased estimate of the match's natural win/loss rate or of volleyball generally. Any eventual comparison must report the analyzed denominators and missingness by outcome and set.

Regenerate with `.\.venv\Scripts\python.exe scripts/freeze_honours_rally_sample.py` only if intentionally creating a new sample version. Once player review begins, keep this selection frozen.
