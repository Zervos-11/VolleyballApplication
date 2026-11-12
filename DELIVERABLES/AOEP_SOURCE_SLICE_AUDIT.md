# AoEP 50-frame source-slice audit

**Scope:** frames 75180–75229 of `yt_AoEP-YiWRvc`, six visually named near-side players. The frozen YOLOv8n + ByteTrack output predates the side review. All 50 clean source frames were inspected in ten five-frame sheets. [Reproducible results](../data/processed/aoep_new_source/heldout_source_review/development_audit_75180_75229.json), [visibility record](../data/processed/aoep_new_source/heldout_source_review/visibility_reference_75180_75229.json), [audit script](../scripts/evaluate_aoep_source_slice.py).

**Evidence class:** single-reviewer development audit. The reviewer had already seen tracker diagnostics. The six approximate box-anchor frames were drawn after predictions had been seen. These observations are **not independent held-out labels** and do not establish detector recall, precision, IDF1, or court-position accuracy.

## Source-visible player coverage

| Near player | Source-visible frames | Frames with named raw-box candidate | Missing named candidate | Visibility note |
| --- | ---: | ---: | ---: | --- |
| Yellow #5 | 50 | 50 | 0 | Visible throughout |
| Yellow centre-left | 50 | 26 | 24 | Partly behind #4 from 75206–75229; remains in the image |
| Yellow #4 | 50 | 50 | 0 | Visible throughout |
| Yellow setter #18 | 50 | 50 | 0 | Airborne early; box presence is not a floor position |
| Navy #10 | 50 | 50 | 0 | Visible throughout |
| Yellow right entrant | 34 | 19 | 15 | Clipped by the right image edge; first possible fragment at 75193–75195 excluded |
| **Total** | **284** | **245** | **39** | Candidate associations are tracker-informed |

The right entrant is out of frame through 75192. Frames 75193–75195 are uncertain first-fragment frames and are excluded from the 284 source-visible denominator. The 34 included entrant frames start at 75196. The 39 missing named candidates are not proof that no person detection exists anywhere in the frame: a different, ambiguous, or background raw box may exist. They mean no distinct usable box is linked to that visual player in the development ledger.

## Box and identity checks on six sampled frames

The approximate source-drawn anchors cover 34 visible player slots at frames 75180, 75190, 75200, 75210, 75220 and 75229. A one-to-one raw-box match reaches IoU ≥ 0.5 for **29/34** slots; median IoU among those 29 matches is **0.835**. Five sampled slots miss that threshold: right entrant at 75200 and 75220, and centre-left yellow at 75210, 75220 and 75229. These are **agreement with unblinded development anchors**, not measured detector accuracy. No precision denominator exists because all people, including far-side and nonplayers, were not exhaustively labeled.

The named-candidate ledger links #5 to raw ID 8, #4 to 3, navy #10 to 1, and centre-left yellow to 131 while its box exists. Setter #18 uses IDs **346 and 492** across the six sampled frames, showing an identity split even though a box candidate is present on every frame. The right entrant uses ID 517 where a usable candidate is linked, with a gap at 75216–75226. Sampled ID agreement does not prove continuous identity between sampled frames.

## Court positions and movement

No new metre-scale position or distance was derived from this audit. The setter is airborne near the beginning; the centre-left player is partly occluded after frame 75205; and the right entrant is edge-clipped. Holding a player's last position or interpolating across these intervals can make a *display path* but is not an observed floor contact. The existing approximate AoEP case-study distances remain development estimates with their stated gaps, not accuracy-validated distances.

## What remains for a defensible honours result

This slice now has a complete source-visibility record and a reproducible frozen-prediction diagnostic. A formal performance claim still needs a separate source or truly independent frame labeling, exhaustive target and opponent boxes on a prespecified interval, reviewed foot contacts where ground positions are claimed, and confirmed calibration. With the current single-reviewer scope, the honest deliverable is a bounded case study with measured candidate coverage and disclosed uncertainty.

Source SHA-256: `2b762dfadcc1d725e9f08f3c376a22be276254499493a7af7674086b91910b44`. The result JSON records the exact frozen raw-output, anchor, and visibility-reference hashes.
