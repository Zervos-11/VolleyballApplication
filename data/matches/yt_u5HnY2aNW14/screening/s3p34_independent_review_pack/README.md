# S3 P34 independent review packet

No second reviewer is available for the current thesis audit. The active [single-reviewer protocol](../../../../../DELIVERABLES/HONOURS_U5_S3P34_SINGLE_REVIEWER_PROTOCOL.md) uses the frozen existing marks and keeps this packet as an optional unboxed source-image aid. The blank forms below contain no observations. If the original reviewer uses them, label the resulting marks as same-reviewer and previously exposed to tracker results; do not score them as independent adjudication.

All 50 images are native 1280 x 720 source frames with no tracker boxes or earlier annotations. The blank templates must be filled by a reviewer who has not seen the existing proxy marks where possible. Keep the completed files separate from these blank templates.

1. Copy `event_review_blank.csv` to `event_review_completed.csv`. For the serve frames 35986–36000, use `before_contact`, `contact`, `after_contact`, or `uncertain` in `ball_contact_or_dead_status`. For point-ending frames 36138–36150, use `live`, `dead`, or `uncertain`. Record only directly visible evidence and use `uncertain` when the event cannot be resolved to a frame.
2. Copy `court_review_blank.csv` to `court_review_completed.csv`. On frame 36072, mark four court corners and both attack-line/sideline intersections independently. Pixel coordinates use the original 1280 x 720 image.
3. Copy `player_review_blank.csv` to `player_review_completed.csv`. For each of six UCLA jerseys at the 24 five-Hz source frames. Record identity as `confirmed`, `sequence_only`, or `uncertain`; ground status as `grounded`, `airborne`, `occluded`, or `uncertain`. Use `confirmed` only when the jersey digit is readable in the frame; use `sequence_only` for an assignment followed through neighbouring frames. If both shoes or their floor contact cannot be read, use `uncertain` for ground status. Enter an approximate shoe midpoint and a nonnegative `reading_uncertainty_px` only for readable grounded contact; leave other coordinates blank and explain in notes. Keep all 144 rows in their original order.

This packet can support independent adjudication of the sampled analysis. It cannot create a continuous six-grounded-player rally where a player is airborne, and it does not make a post hoc selected window prespecified. The source footage and extracted images remain local research materials.

Score the completed forms with `.\.venv\Scripts\python.exe scripts/score_u5_s3p34_independent_review.py`. The scorer checks image hashes and form completeness and reports observed discrepancies; it never automatically grants strict approval.

The manifest binds every unboxed image by SHA-256. Reproduce the pack with `.\.venv\Scripts\python.exe scripts/render_u5_s3p34_independent_review_pack.py`.
