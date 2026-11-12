# S3 P34 opening three-frame player review

Open the [three-frame click review](http://127.0.0.1:8056/) while the local server is running. It covers source frames **35998–36000**, from the reviewer's reported serve contact through the frame before the existing 36001–36138 player-state record. The source image is hash checked. White numbered boxes are **provisional detector matches** to the reviewed 36001 boxes; use **Hide suggested boxes** to inspect the unboxed frame. Player slots are 1/#28, 2/#12, 3/#15, 4/#7, 5/#19 and 6/#21.

For each player, check identity, grounded or airborne state, whether the suggested box follows that player, and whether its bottom is a plausible floor proxy. Choose **Not applicable** for an airborne player's floor point or a missing/wrong box. A correct box can remain **Same player** while the player is airborne. Mark uncertainty instead of inferring shoe contact. Tick the all-six check, save each frame and export. This review does not require manual shoe clicks and cannot measure box-to-shoe position error.

The proposals are in [`s3p34_opening_frame_screen.json`](../s3p34_opening_frame_screen.json). Each frame has six suggested player matches, but those suggestions are **not** accepted identity or position observations until source reviewed. The three frames were chosen after the event review, so this is a post hoc completion check. The event ending remains a separate single-reviewer judgment with no certified exact point-ending frame.

To restart the page from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.s3p34_opening_frame_review:app --host 127.0.0.1 --port 8056
```
