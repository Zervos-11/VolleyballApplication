# r1 end-to-end API pilot — 28 October 2026

The production `compute_tracking_metrics` path ran on the original `yt_FqE5pTJqx8g` video over the provisional r1 interval **[21050, 21464)** at its measured **50 fps**. The run used the existing YOLOv8n/ByteTrack settings (`conf=0.20`, `imgsz=960`) in an isolated output folder with a hard link to the verified source. It used no homography, jersey map, pose ankles, or added rally padding. The match's annotations, official boundary and staged calibration were not changed.

| Check | Result |
| --- | ---: |
| Frames processed | 414 / 414 |
| Frames with at least one person detection | 414 / 414 |
| Raw person observations | 8,511 |
| Raw tracker IDs across scene | 117 |
| API versus frozen r1 detector audit: frames with different IDs or counts | 0 |
| API versus frozen audit: largest paired bottom-centre difference | 0.0071 px |

The [isolated metrics](../data/processed/fqe_r1_end_to_end_pilot/metrics.json), [processing diagnostics](../data/processed/fqe_r1_end_to_end_pilot/processing_diagnostics.json), [track CSV](../data/processed/fqe_r1_end_to_end_pilot/tracks_centroids.csv), [repeatability audit](../data/processed/fqe_r1_end_to_end_pilot/AUDIT.json), and [six-frame source overlay](../data/processed/fqe_r1_end_to_end_pilot/source_overlay_sheet.jpg) document the run. The [runner](../scripts/run_r1_end_to_end_pilot.py) and [audit script](../scripts/audit_r1_end_to_end_pilot.py) reproduce it. The source SHA-256 matches the first-pilot source record.

The separate [six-slot candidate coverage audit](../data/processed/fqe_r1_end_to_end_pilot/NAMED_CANDIDATE_COVERAGE.json) links all **2,025 displayed candidate boxes** back to the API track CSV, with zero missing track IDs and at most 0.0071 px bottom-centre difference from rounding. It reports usable *box candidates* on **108/414 frames with all six named slots**, 183 frames with five, 93 with four, and 30 with three. Per-player candidate coverage is #9 **414/414**, #10 **380/414**, #11 **311/414**, #12 **368/414**, #13 **142/414**, and #20 **410/414**. The other four #20 frames have truncated boxes and remain invalid. The [coverage script](../scripts/audit_r1_named_candidate_coverage.py) preserves each missing or invalid run. Every named slot still has **zero verified court positions**; these counts are neither a visibility score nor identity accuracy.

**What this verifies:** the API seeks to the correct late-video interval, processes every selected frame, and reproduces the frozen raw tracking output. The six-frame overlay aligns the API bottom-centre points with the decoded source frames.

**What it does not verify:** the 8,511 detections include opponents, spectators, officials and other sideline people. A frame with any detection is not a frame with six verified teammates. The API's 500,175 px² convex-hull area, 3.61 entropy and 720 px mean pair spacing are scene-wide exploratory summaries, not volleyball team coverage or physical distances. The detector points are box bottoms, not verified shoe-floor contacts. `team_identity_verified` and `ground_positions_verified` are both false; transition latency and win probability remain null. No metre-scale or production player metric is released.

The next release gate is a **source-checked six-player output on one bounded point**: retain the now quantified candidate gaps, establish grounded positions where source evidence permits, and validate identity and position decisions against independent source labels. The end frame, dataset use/privacy record, and export review status also remain open. More raw inference on the same r1 frames would not address those evidence gaps.
