# External volleyball game-state model transfer trial

The [public volleyball-ml-models repository](https://github.com/masouduut94/volleyball-ml-models) provides a three-state VideoMAE model, with weights linked from the [project's dataset page](https://github.com/masouduut94/volleyball_analytics/wiki/Datasets-and-Weights). We downloaded only its game-state checkpoint and loaded its safetensors weights locally. The [machine-readable trial](../data/processed/honours_external_game_state_trial.json) records the source, model and reference-label hashes.

The parent project's [README data-source statement](https://github.com/masouduut94/volleyball_analytics#-data-sources) says its training and testing clips came from [Volleyball Watchdog](https://www.youtube.com/@VolleyballWatchdog/videos), featuring international matches. It does not identify the exact games or disclose a video-level train/test split for this checkpoint. Our primary recording is local gym footage, so differences in camera view, lighting, broadcast graphics and play level may affect transfer. The model therefore needs a local source-reviewed check before its predictions can be used even as phase suggestions.

Each prediction uses 16 source frames uniformly sampled over a one-second interval centred on one of the 13 previously [source-reviewed candidate instants](HONOURS_CANDIDATE_PHASE_QC.md). The uncertain end-of-play instant is listed but excluded from scoring. For the binary screen, model `play` is positive; `service` and `no-play` are non-play.

**Transfer check:** 11/12 agreement; live-play recall 7/8; non-play specificity 4/4. This is a small domain-transfer diagnostic, not an accuracy estimate for the full match or an independent test of the training dataset.

The disagreement is set-one point 23, frame 36366: source context shows the ball and players in continuing play, while the one-second model clip is classified `service`. The very sharp model probabilities below are not calibrated confidence estimates on this gym footage. Human source judgments take precedence in navigation and analysis.

| Set | Point | Centre frame | Source-review phase | Model class | P(play) |
| ---: | ---: | ---: | --- | --- | ---: |
| 1 | 2 | 8643 | live_play | play | 1.000 |
| 1 | 7 | 15252 | pre_serve | service | 0.000 |
| 1 | 7 | 15505 | live_play | play | 1.000 |
| 1 | 9 | 19345 | live_play | play | 1.000 |
| 1 | 9 | 19854 | uncertain_end_phase | no-play | 0.000 |
| 1 | 23 | 36366 | live_play | service | 0.000 |
| 1 | 39 | 65656 | pre_serve | no-play | 0.000 |
| 2 | 2 | 78050 | live_play | play | 1.000 |
| 2 | 2 | 78100 | live_play | play | 1.000 |
| 2 | 2 | 78400 | live_play | play | 1.000 |
| 2 | 12 | 90335 | between_points | no-play | 0.000 |
| 2 | 21 | 102259 | pre_serve | service | 0.000 |
| 3 | 27 | 187701 | live_play | play | 1.000 |

The model should only propose additional live-play windows if this local transfer check is convincing. It cannot create six-player shoe positions or resolve team identity. Its output must remain separate from the source-reviewed phase record and cannot be counted as validated rally metrics without those checks.
