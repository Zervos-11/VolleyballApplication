# First pilot: five rally proposals ready for boundary review

Open **http://127.0.0.1:8010/** while the local review server is running. The page uses the downloaded 1080p50 original. It does not upload footage or edits to another service.

## Your first session

1. Select **r1**, then choose **Watch from current frame**. Watch through the point end.
2. Choose **Inspect start**. Use the single-frame buttons to find serve contact. Click **Set start to shown frame**. Browser playback seeking is approximate; the decoded still images use source frame indices.
3. Choose **Inspect end**. Find the first frame after the action that ends the point, and click **Set end to shown frame**. The end is exclusive; do not use a delayed scoreboard update as the point-end time.
4. Enter your annotator code, such as `ann01`. Record uncertainty or any reason to exclude the rally. Choose **Save my boundary check**.
5. Repeat for r2–r5. A saved boundary check is your first annotation pass, not independent review or completed player labels.

The original proposals remain in `data/matches/yt_FqE5pTJqx8g/pilot/selection.json`. Your checks are written separately to `pilot/boundary_review.json`; previous decisions are retained under `pilot/review_history/`. Do not share an annotator code between people.

## Proposals, not final labels

| Rally | Set inferred from scoreboard | Approximate start | Approximate end | Reason to retain in the pilot |
|---|---:|---|---|---|
| r1 | 1 | 07:01.00 | 07:09.80 | Near-side serve and short exchange |
| r2 | 2 | 26:00.00 | 26:10.00 | Far-side serve and net overlap |
| r3 | 2 | 32:11.00 | 32:21.20 | Reception, movement and a defensive dive |
| r4 | 3 | 49:59.80 | 50:24.40 | Longer exchange and multiple transitions |
| r5 | 3 | 58:44.80 | 58:52.00 | Near-side serve and a difficult defensive finish |

These are model-assisted boundary estimates from real frames sampled every two seconds and more closely around candidate boundaries at 0.2-second intervals. They have not been checked frame by frame by a human. The displayed precision is an index convention, not a claim of annotation accuracy. Correct them before generating final label schedules or tracking metrics. Scores and set/rally ordinals are also provisional until reviewed.

## Pilot sampling amendment

This first-source pilot uses a documented temporal sampling method, instead of the framework's eventual uniform sampling within an exhaustive rally register. Its purpose is to establish annotation practice and workload, not to estimate whole-match performance without sampling bias.

- Exclude the first and last 120 seconds from the temporal sampling frame. This was an operational choice to avoid endpoint graphics; it is not a verified claim about when match play starts or ends.
- Divide the remaining frame interval into five equal temporal strata.
- Using seed `20261009`, draw one 60-second review window inside each stratum. The script quantises its start to a whole source second, within the stratum. The stored frame indices are authoritative.
- Propose the first complete rally whose serve and point end are inside that window. Ignore any rally already underway at the window start. Retain uncertainty for human review rather than claiming a verified boundary.
- The five windows are 06:21–07:21, 25:37–26:37, 32:08–33:08, 49:56–50:56, and 58:01–59:01. All contained a candidate in the sampled-frame review; no replacement windows were drawn.
- If human review finds a selected rally incomplete or unusable, mark it excluded and record why. Do not silently replace it with a visually easier rally. Record a replacement decision and its sampling rule separately.

The seed and windows are recorded in `pilot/review_windows.json`; all ten overview sheets are in `pilot/windows/`, and closer boundary sheets are in `pilot/boundaries/`. `pilot/rally_candidates.csv` is a proposal register, not a release-ready rally register. Full-match selection probabilities are unknown and left unset. Do not feed these five proposals to `sample_rallies.py` and call the resulting output a random sample of the full match.

This recording remains entirely in the **pilot/development** split. Five rallies from one match are not five independent matches. A second independently sourced match is still required for the planned two-match pilot, and separate matches are required for main/evaluation data.

## After checking the boundaries

Start player annotation with r1 to test the full process before doing all five rallies. Use the near-camera half court; verify which named team occupies that half in each set. Assign anonymous IDs and label all target players at the prescribed sparse frames, plus the dense identity window. Mark hidden feet and airborne players as unobservable rather than guessing floor positions. A separate [player annotation workspace and guide](PLAYER_ANNOTATION_GUIDE.md) is now available, with automatic proposals for 68 sparse frames across all five rallies. Dense identity annotation remains unfinished.

Check camera stability and define court calibration for each selected segment before using metre coordinates. Source-use and privacy records remain pending; do not mark the source or labels as released merely because technical screening passed.

## Running and checking the review tool

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.pilot_review:app --host 127.0.0.1 --port 8010
```

If the page already responds, a server is running and this command is unnecessary. The server started during setup writes logs to `data/processed/pilot_review_server.*.log` and its launch PID to `data/processed/pilot_review_server.pid`. Keep it bound to loopback for local use.

Validation: the suite now contains 29 passing tests, covering boundary review, player-label validation and export, stale schedules, proposal refresh, sampling and existing QC behavior. JavaScript syntax was checked with Node. These checks validate the tool, not the accuracy of the proposed rally boundaries or player labels.
