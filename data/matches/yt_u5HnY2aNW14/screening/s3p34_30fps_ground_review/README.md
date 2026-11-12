# S3 P34 diagnostic 30-fps ground review

**Review completed 4 November 2026.** The 180-row completed CSV is frozen.
The [score](single_reviewer_score.json) accepts all 180 intervening slots under
the single-reviewer diagnostic rule; the
[position comparison](../../../../../DELIVERABLES/HONOURS_U5_S3P34_30FPS_POSITION_COMPARISON.md)
reports the shoe-to-box-bottom differences. The local website is now read-only
for this completed export.

## Review in the local website

From the repository root, start the existing local review server with
`.\.venv\Scripts\python.exe -m uvicorn services.api.pilot_review:app --host 127.0.0.1 --port 8039`,
then open [S3 P34 ground review](http://127.0.0.1:8039/s3p34-ground-review).
The page shows each unboxed source image, the six player slots, and the review
progress. New rows start with `confirmed` and `grounded` selected for convenience;
review the frame and change any value the image does not support before saving.
Saving records the review. Enter a reviewer code, choose a
player's **Mark shoe point** button,
select **Grounded**, and click the floor contact in the source image. A 2× crop
opens below the frame; click it to refine the point. The page fills source-pixel
x and y automatically and initially selects a 15-pixel reading uncertainty,
which you can change using the menu. Use **Clear point** to remove a mark. Shoe
points are optional; leave them blank when the floor contact cannot be read.
Save all six source-image judgments before the tracker boxes appear
for that frame. The numbered box view draws six white outlined boxes with
large yellow labels on that frame. Labels 1–6 correspond to the six comparison
cards in order: 1 → stored key 28, 2 → 12, 3 → 15, 4 → 7, 5 → 19, 6 → 21.
The original raw-ID contact sheet remains available through the link above
the numbered view. These numbers are stable review labels, not verified jersey
digits. The paired tracker stage starts with `same_player` and
`plausible` selected. Correct any mismatches, then save the six candidate and
box-bottom comparisons. Saved choices remain populated when revisiting a frame.
Choose uncertain when a judgment cannot be made from the source. The website
saves a revisioned draft in `single_reviewer_web_draft.json` and
`single_reviewer_web_history/`. Once both stages are complete on all 30 frames,
use **Export completed CSV**. It creates `single_reviewer_unsampled_completed.csv`
once and does not overwrite an existing export. Run the scorer command below.

The source-image-first order is enforced in the page. The reviewer has seen
earlier tracker results, so this is a single-reviewer unblinded diagnostic,
regardless of whether the paired sheet is opened after the source stage.
The stored slot keys in the page come from the earlier mapping. If a visible
jersey digit differs from a stored slot key, record
that in Notes and use `sequence_only` or `uncertain` rather than `confirmed`.
Consistent slot IDs are sufficient for a within-frame team geometry calculation,
but a jersey-level identity claim needs a verified slot-to-jersey mapping.

## CSV alternative

This packet contains all 37 unboxed source frames from 36066 through 36102 and ten source contact sheets. The [manifest](manifest.json) hashes each image. The [audit](audit.json) joins them to the existing observation ledger: seven previously reviewed five-Hz frames have six accepted grounded proxies; the other 30 frames contain **180 player slots with no human 30-fps ground verdict**. Every frame has six candidate boxes in the separate tracker ledger, but this interval was selected after box availability was known. It is a diagnostic segment, not a prespecified fixed window.

For the one available human reviewer, copy `single_reviewer_unsampled_blank.csv` to `single_reviewer_unsampled_completed.csv`. Preserve the 180 rows and the source frame, jersey, image, hash and paired-sheet fields. Complete the remaining fields in two passes:

1. Open the `unboxed_*.png` source frame first. Enter `identity_status` as `confirmed`, `sequence_only`, or `uncertain`; enter `ground_status` as `grounded`, `airborne`, `occluded`, or `uncertain`. Use `confirmed` only when the jersey digit is readable in that frame. If you can read a shoe midpoint, record its original 1280 × 720 pixel coordinates and a nonnegative `reading_uncertainty_px`; these shoe coordinates are optional for a grounded box-bottom proxy verdict. Keep them blank when contact is uncertain. Record the reason in `notes`.
2. Only after saving the source-only decisions, open `paired_sheet_after_unboxed_review`. Enter `candidate_alignment` as `same_player`, `wrong_player`, or `uncertain`, and `proxy_floor_alignment` as `plausible`, `implausible`, or `uncertain`. The reviewer has previously seen tracker results; label this as a same-reviewer unblinded check, not independent adjudication.

Run `.\.venv\Scripts\python.exe scripts/score_u5_s3p34_single_reviewer_30fps.py` from the repository root. The scorer checks form order and source-image hashes and counts complete grounded-proxy verdicts. It leaves strict approval false. The source sheets were visually screened by the AI assistant for obvious player absence; this screen accepted **zero** new ground positions and is not a human verdict. The four-corner calibration and event/window gates are documented separately. Images remain local research materials.
