# Two-recording transfer screen: current status

**6 November 2026.** The [frozen extension protocol](HONOURS_U5_RESEARCH_EXTENSION_PROTOCOL.md) specifies how to compare additional recordings. The source-selected [Lynx–ProVolley interval](../data/matches/yt_AoEP-YiWRvc/pilot/selection.json) and the previously proposed [ProVolley–UTS r3 interval](../data/matches/yt_FqE5pTJqx8g/pilot/selection.json) were processed with the same YOLOv8n person model, confidence 0.20, image size 960, ByteTrack and 0.2-second source-time grid.

| Recording | Source interval | Sampled frames | All-person proposals | Review status |
| --- | ---: | ---: | ---: | --- |
| Lynx–ProVolley | 74980–75389 at 59.94 fps | 35 | 498 | Source-only point selection; boundaries provisional |
| ProVolley–UTS, proposed r3 | 96550–97059 at 50 fps | 51 | 1,068 | Model-proposed time-quintile point; source verification pending |

The [AoEP candidate output](../data/matches/yt_AoEP-YiWRvc/pilot/transfer_5hz_candidate_screen.json) and [FqE candidate output](../data/matches/yt_FqE5pTJqx8g/pilot/transfer_5hz_candidate_screen.json) retain every sampled frame and proposal with source, selection and model hashes. Counts include far-side players, officials and other people; **498 and 1,068 are not near-side detections or tracking success counts**. No cross-recording accuracy or generalisation estimate follows from them yet.

Next, verify the source event brackets and near-side six on both points, review the frozen 5-Hz grids against source video, and mark candidate-to-player matches and missing boxes. Calibrate the stable camera segment in each recording, then click a prespecified small grounded-shoe reference sample for mapped position error. Report the per-recording denominators before comparing them. The FqE source was used during development and is not an independent held-out test. Reproduce the raw screen with `.\.venv\Scripts\python.exe scripts/screen_transfer_rally_candidates.py`.
