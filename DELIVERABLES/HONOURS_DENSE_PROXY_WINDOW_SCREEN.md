# Short-window six-box availability screen

The [source-bound record](../data/processed/honours_dense_proxy_window_screen.json) samples source frames every 10 frames across 201-frame windows (4.0 s between endpoints) around the visually screened set-three ProVolley-won point 5 and UTS-won point 37 snapshots. It applies the same person detector and staged near-court gate, then an additional IoU 0.45 overlap filter. This tests whether a short six-box run is even available before attempting six-player trajectories.

| Point | Winner | Frames sampled | Raw frames with 6+ near-court boxes | Frames with 6+ after overlap filter | Candidate frame indices |
| ---: | --- | ---: | ---: | ---: | --- |
| 5 | ProVolley | 21 | 4 | 4 | 155719, 155749, 155759, 155799 |
| 37 | UTS | 21 | 7 | 6 | 204213, 204253, 204263, 204313, 204323, 204333 |

The counts are **upper-bound detector proposals**: far-side players can still pass the court gate, while real teammates can be hidden or merged. A six-box count does not establish six near-side players. The [source-image review](HONOURS_DENSE_PROXY_WINDOW_VISUAL_REVIEW.md) shows far-side contamination and missed near-side players in the later UTS-win frames. No outcome comparison is made from these counts.
