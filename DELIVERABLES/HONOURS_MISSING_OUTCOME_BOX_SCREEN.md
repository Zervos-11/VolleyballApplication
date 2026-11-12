# Nearby box proposals for missing outcome groups

The [source-bound detector screen](../data/processed/honours_missing_outcome_box_screen.json) searched short neighborhoods around model-proposed play frames for the six UTS-won points in sets two and three. It preserves the frozen sample and all saved annotations. The detector counts person boxes whose bottom centre projects into the nominal near-side court; these are proposals, not six verified teammates or final metric positions.

| Set | Point | Frames screened | Max near-court boxes | Frames with 6+ boxes | First candidate frames |
| ---: | ---: | ---: | ---: | ---: | --- |
| 2 | 8 | 5 | 7 | 1 | 85398 |
| 2 | 12 | 5 | 7 | 2 | 90065, 90095 |
| 2 | 21 | 10 | 6 | 3 | 102513, 102783, 102798 |
| 3 | 11 | 10 | 7 | 7 | 162695, 162710, 162725, 162965, 162980, 162995, 163010 |
| 3 | 37 | 5 | 7 | 2 | 204248, 204263 |
| 3 | 38 | 5 | 6 | 2 | 205378, 205423 |

The next source check is to inspect the listed six-box frames for actual live play, six distinct near-side players and usable grounded boxes. A detector count alone cannot resolve team identity, occlusion or a player partly outside the image. Only after that check should a box-centre image movement proxy or tested box-bottom court proxy be measured. Existing saved frames with fewer boxes remain valid evidence of missingness.

The [visual follow-up](HONOURS_MISSING_OUTCOME_VISUAL_SCREEN.md) inspected all 17 six-box proposal images. It found duplicates or opponent boxes in several apparent six-box counts. Set-three points 11 and 37 each have one visually screened six-distinct-near-box snapshot; point 11 includes an airborne player. The raw candidate counts must not be promoted to rally-level metric eligibility.

[Best-frame review sheet](../data/processed/honours_missing_outcome_box_screen.jpg).
