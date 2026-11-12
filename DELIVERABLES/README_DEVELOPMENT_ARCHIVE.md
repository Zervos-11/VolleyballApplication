# Earlier development notes

Volley Analytics — Local API

**Honours research package:** [Revised thesis draft](DELIVERABLES/HONOURS_U5_THESIS_FINAL_DRAFT.md), [primary-match evidence map](DELIVERABLES/HONOURS_PROJECT_EVIDENCE_PACKAGE.md) and [read-only evidence checker](scripts/check_honours_evidence_package.py). The Concordia–UCLA 18-point sample is the primary analysis; ProVolley–UTS and other clips are development or transfer evidence and are not pooled with its outcome comparison. The project reports short approximate court paths and an exploratory outcome comparison. Complete six-player rally trajectories remain unvalidated.

Latest full-clip work: [raw tracklet audit](DELIVERABLES/HONOURS_U5_FULL_CLIP_TRACKLET_AUDIT.md) and [source-frame spot check](DELIVERABLES/HONOURS_U5_FULL_CLIP_SPOTCHECK.md). All 1,005 selected 5 Hz clip instants have now been screened; the earlier selected-clip coverage link below describes a separate core-only pass. Candidate runs are not validated six-player rally trajectories.

The [every-sample identity audit](DELIVERABLES/HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) checks 216 person crops in the two longest runs; the [in-run shoe comparison](DELIVERABLES/HONOURS_U5_FULL_RUN_POSITION_REFERENCE.md) quantifies two existing manual marks at one frame. Identity continuity at sampled frames does not certify exact floor paths or the source frames between samples.

The [30 fps two-run audit](DELIVERABLES/HONOURS_U5_TWO_RUNS_30FPS_AUDIT.md) screens all 206 source frames in those spans and records ten temporary missing detections in one run. It is a raw-ID continuity check; inter-sample jersey identity remains unreviewed by a person.

Current honours-facing evidence: the [Concordia–UCLA primary-match feasibility result](DELIVERABLES/HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md), [integrated working thesis draft](DELIVERABLES/HONOURS_U5_THESIS_WORKING_DRAFT.md), [primary methods and results draft](DELIVERABLES/HONOURS_U5_PRIMARY_MANUSCRIPT_DRAFT.md), [full selected-clip candidate coverage](DELIVERABLES/HONOURS_U5_SELECTED_CLIP_COURT_COVERAGE.md), [fixed-box court-proxy pilot](DELIVERABLES/HONOURS_U5_FIXED_BOX_COURT_PROXY.md), [anchor reference](DELIVERABLES/HONOURS_U5_FIXED_BOX_ANCHOR_REFERENCE.md), [non-anchor manual shoe check](DELIVERABLES/HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md), [updated error sensitivity](DELIVERABLES/HONOURS_U5_DYNAMIC_ERROR_SENSITIVITY.md), [one-frame full-team reference](DELIVERABLES/HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md), [supervisor scope brief](DELIVERABLES/SUPERVISOR_SCOPE_DECISION_BRIEF.md), [contract alignment](DELIVERABLES/HONOURS_CONTRACT_ALIGNMENT.md), [seven success-criteria audit](DELIVERABLES/HONOURS_SUCCESS_CRITERIA_AUDIT.md), [submission readiness](DELIVERABLES/HONOURS_SUBMISSION_READINESS.md), and [project completion handoff](DELIVERABLES/PROJECT_COMPLETION_HANDOFF.md). Earlier image-plane diagnostics and source reviews are linked from those documents. The [ProVolley–UTS draft](DELIVERABLES/HONOURS_METHODS_RESULTS_DRAFT.md) and its 123-point register remain development history; they are not pooled with Concordia–UCLA. The primary 18-point frozen sample has zero validated six-player metric frames, so the signed outcome comparison remains incomplete. Broader product work is tracked in [project status](DELIVERABLES/PROJECT_STATUS.md). The Week 6 audit below is a historical snapshot; the five pilot rallies now have saved visual development labels and an export, but the export is still marked `unreviewed`.

The first pilot has a [bounded r1 case-study readout](DELIVERABLES/R1_CASE_STUDY_READOUT.md) and a [playable full-point development preview](data/processed/fqe_r1_boundary_recheck/r1_visual_candidate_preview.mp4). The preview marks candidate player boxes and gaps; it does not report validated court travel.

An [isolated r1 end-to-end API pilot](DELIVERABLES/R1_END_TO_END_PILOT.md) processed all 414 candidate frames and reproduced the frozen raw person tracks. Its detection coverage includes opponents and sideline people; it does not validate six-player coverage or physical movement.

The [r1 case-study viewer](web/r1_case_study.html) combines the candidate clip, exact source-frame stills and six-player box states. It also lets a reviewer save source-pixel shoe contacts or explicit unknown states in a separate revisioned draft. Click the still frame for a 2× shoe-point crop, then click the crop to refine a point before saving; an optional recorded net-floor line can be overlaid for visual inspection. A crossing toggle can show a dashed **last-seen** marker for up to eight frames when another named box plausibly overlaps the missing player; it does not represent the player's current position or movement. Select #20 and use **Show #20 shoe cues** to see read-only colour-region suggestions on frames 21300–21463; inspect the source sole before saving any floor contact. The guided next-frame button skips saved states for the selected player. With the updated pilot review server running on port 8011, open `http://127.0.0.1:8011/r1-case-study`. If starting it yourself, run `.\.venv\Scripts\python.exe -m uvicorn services.api.pilot_review:app --host 127.0.0.1 --port 8011`. These draft clicks do not change saved pilot labels or enable physical-distance metrics.

The processing API now seeks to each rally in the source video instead of stopping after the first 600 frames. Each rally gets fresh tracker state. Coverage outputs remain exploratory; transition latency and win probability are `null` until validated estimators are available.

Each per-rally metric includes a `quality` object with its processed frame interval, count of frames with and without track observations, raw and retained track-observation counts, and an explicit `insufficient_observations` status when coverage cannot be computed. These counts describe tracker output, not ground-truth player visibility or team identity.

`coverage.mpd` is the average spacing between retained detector points **in the same frame**. It is `null` if no frame contains at least two retained detections. `quality.simultaneous_pair_frames` and `quality.simultaneous_pairs` show its sample size. Court calibration changes the units from pixels to metres, but `quality.ground_positions_verified` and `quality.team_identity_verified` remain `false`: this spacing, the area and entropy are exploratory detector summaries, not verified six-player physical metrics. The web page displays those limits above the raw API response.

Older saved `metrics.json` files have no `quality.metric_revision` and may contain a spacing value mixed across time. The web page flags those results; reprocess a match to compute the corrected `same_frame_mpd_v2` value.

Week 6 dataset work

- The [player annotation workspace](DELIVERABLES/PLAYER_ANNOTATION_GUIDE.md) opens at `http://127.0.0.1:8010/players` using the same local review server. Five rallies now have saved labels across 69 sampled frames; their export remains marked `unreviewed`.

- Use the [pilot boundary review](DELIVERABLES/PILOT_REVIEW_GUIDE.md) page to inspect the saved rallies. Run `.\.venv\Scripts\python.exe -m uvicorn services.api.pilot_review:app --host 127.0.0.1 --port 8010` and open `http://127.0.0.1:8010/`.

- Start with [the dataset and annotation framework](DELIVERABLES/WEEK6_DATASET_AND_ANNOTATION.md).
- Read [the historical evidence audit](DELIVERABLES/CURRENT_DATASET_STATUS.md) for legacy-data QC issues, and [project status](DELIVERABLES/PROJECT_STATUS.md) for the current pilot.
- [Dataset schema](DELIVERABLES/DATASET_SCHEMA.md) and [data-management procedure](DELIVERABLES/DATA_MANAGEMENT.md) describe the required records. Blank CSV templates are in `annotations/`.
- Run `.\.venv\Scripts\python.exe scripts/audit_dataset.py` to regenerate the inventory and detailed QC reports under `data/processed/week6_audit/`.

Quickstart

- Create a virtualenv and install deps:
  - `python -m venv .venv`
  - `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (macOS/Linux)
  - `pip install -r requirements.txt`

- Run the API:
  - `uvicorn services.api.main:app --reload`
  - Open `http://127.0.0.1:8000/web/`

- Workflow:
  - Click “1) Init Match” with a `match_id` (e.g. `uts_demo`).
  - “2) Upload Video” the MP4.
  - “3) Send Metadata” (use the template button if needed).
  - “4) Process” to run tracking and metrics.
  - “5) Get Metrics” to view the output.

Homography Calibration

- Open `web/homography.html` in a browser.
- Load a frame image and click corners in order: Left-Back -> Right-Back -> Right-Front -> Left-Front.
- Save the JSON as `data/matches/<match_id>/homography.json`.
- If you clicked on a scaled screenshot, the pipeline rescales points to the video’s native resolution.

Notes
- Player tracking uses Ultralytics YOLOv8 + ByteTrack (`ultralytics` package). CPU works but is slow; a GPU is recommended.
- Raw track centroids are saved to `data/matches/<match_id>/tracks_centroids.csv` for debugging.
- Diagnostics are written to `data/matches/<match_id>/processing_diagnostics.json`.

YouTube Helper (download video into a match)

- Instead of uploading an MP4 manually, you can ask the API to download a YouTube video straight into `data/matches/<match_id>`.
- Requirements:
  - `yt-dlp` available (installed via `pip install yt-dlp` or as a CLI on your PATH).
  - `ffmpeg` on your PATH is recommended for best quality and optional audio extraction.
- Example (PowerShell on Windows):
  - Start the API in one terminal: `uvicorn services.api.main:app --reload`
  - In another terminal run:
    - `Invoke-RestMethod -Method POST "http://127.0.0.1:8000/v1/matches/M1/youtube" -ContentType "application/json" -Body '{"url":"https://www.youtube.com/watch?v=WDMo-a0us6c"}'`
- On macOS/Linux (bash):
  - `curl -X POST "http://127.0.0.1:8000/v1/matches/M1/youtube" -H "Content-Type: application/json" -d '{"url":"https://www.youtube.com/watch?v=WDMo-a0us6c"}'`
- Then, in the web UI, set `Match ID` to `M1`, send metadata, click **Process**, then **Get Metrics** as usual.





