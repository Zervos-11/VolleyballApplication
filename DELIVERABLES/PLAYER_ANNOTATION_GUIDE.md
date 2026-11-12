# Player annotation: first working session

Open **http://127.0.0.1:8010/players** to start with r1. To change rallies, return to the boundary review page, select a rally, and choose its player-annotation link. Automatic box proposals are prepared for all five proposed rallies: 68 sparse frames in total (r1: 10, r2: 11, r3: 12, r4: 26, r5: 9).

## Recommended order

1. Check and save each rally's boundaries on the boundary page first. If you change the boundaries, open the player page and choose **Refresh proposals for corrected rally boundaries** before labelling. Old automatic proposals are archived. Refresh is blocked if player labels have already been saved, so existing work cannot be silently overwritten.
2. Start with the first frame of r1. Grey boxes are all detected people, including spectators and officials. Click a target near-court player; only explicitly included players become labels.
3. Enter a stable anonymous ID, for example `near_p01`. Use that ID for the same person on every frame within the rally. The detector's proposal numbers are not player identities. Leave the team as unknown until the home/away assignment is verified.
4. Correct the visible-body box using **Draw / replace box** and drag. Add any missed player with **New player**, then draw their box. Choose partial or full occlusion as appropriate; full occlusion has no guessed box.
5. If the feet visibly contact the floor, choose **Mark floor-contact point** and click the contact location. If both feet contact the floor, use their midpoint. If the player is airborne, feet are hidden, or the location is uncertain, choose the corresponding status and leave the point empty. In the first r1 frame, the near-side server is airborne: do not put a floor point below them.
6. Choose **Include / update player**. Repeat for all target players. Use **Remove selected player** to correct an accidental inclusion. A referee or spectator must not be included simply because the detector found them.
7. Enter your annotator code and mark **All target players accounted for** only when that is true. Record missing/uncertain players in the frame notes. Click **Save this frame**, then move to the next frame.
8. Use **Download saved CSV** to export the saved labels. The CSV remains `unreviewed`; a second person's review is still required.

First complete one frame, reload the page to check the saved work, then finish r1 before scaling up to all five rallies. Unsaved edits prompt before navigation. Start with correct, consistent labels rather than accepting every automatic box.

## Files and provenance

All paths below are relative to `data/matches/yt_FqE5pTJqx8g/`:

- `pilot/player_drafts/r1.json` through `r5.json`: immutable-until-explicit-refresh automatic proposals and frame schedules. They record model file hash, source-video hash, detector settings and boundary snapshot. Archived proposal versions go under `pilot/player_drafts/history/`.
- `pilot/player_annotations/<rally>.json`: labels explicitly saved through the editor, including per-frame completeness and contributor codes. Created only when an annotator saves.
- `pilot/player_annotations/history/`: revision records for every saved frame.
- Downloaded CSV: rows follow the Week 6 player schema, use manual player IDs, and retain `review_status=unreviewed`. Assisted/manual provenance is based on whether a detector proposal was used. No independent reviewer is fabricated.

The source video is never changed. Boundary edits that invalidate the frame schedule block label saves and export until reconciled. If labels already exist, retain their JSON and history and reconcile them against corrected boundaries before regenerating frames; automatic refresh deliberately refuses to discard them.

## What is still unfinished

The 68 frames are an annotation workload, not 68 annotated frames. The generated person boxes are not ground truth. No human player labels or independent reviews were created during tool setup. Person detection can miss players and includes people outside the target half.

The required two-second dense identity window for this source is recorded in r1's draft JSON but has not been densely annotated. The editor currently presents the sparse frame schedule. Court calibration, source-use/privacy records, a second pilot match and main-dataset annotation also remain to be completed.

Technical checks: all 29 tests passed after adding the player editor. They cover saved revision history, CSV provenance, valid/invalid geometry, hidden feet, full occlusion, duplicate IDs, stale frame schedules and safe proposal refresh, in addition to the existing framework checks. Both pages were loaded in an isolated browser, and the frame/proposal display was visually checked. These checks establish tool behavior, not dataset accuracy.
