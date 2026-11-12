# Model-assisted phase navigation in the saved sample

After the [small source-reviewed transfer trial](HONOURS_EXTERNAL_GAME_STATE_TRIAL.md), the same model classified a centred one-second clip at each of the 61 saved frame positions. The [source-bound scan](../data/processed/honours_saved_game_state_scan.json) retains the predictions, probabilities, hashes and existing position-availability flags. It does not change the user's annotations.

The model marked **30/61** saved positions as play, spanning **16/18** sampled points. Combining these *proposals* with the existing source-reviewed phase judgments yields at least one navigation candidate in **16/18** points. The 13 source-reviewed candidate instants retain their human judgments regardless of model output; in particular, the model calls live frame 36366 `service`.

| Set | Point | Winner | Model play / saved frames | Model play with six visible feet | Model play with six nominal in-court feet |
| ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 2 | UTS | 1/1 | 1 | 1 |
| 1 | 7 | ProVolley | 1/3 | 1 | 1 |
| 1 | 9 | ProVolley | 2/3 | 1 | 1 |
| 1 | 23 | ProVolley | 1/3 | 0 | 0 |
| 1 | 32 | UTS | 1/3 | 0 | 0 |
| 1 | 39 | UTS | 1/3 | 0 | 0 |
| 2 | 2 | ProVolley | 10/12 | 6 | 3 |
| 2 | 8 | UTS | 1/3 | 0 | 0 |
| 2 | 12 | UTS | 1/3 | 0 | 0 |
| 2 | 14 | ProVolley | 0/3 | 0 | 0 |
| 2 | 21 | UTS | 2/3 | 0 | 0 |
| 2 | 33 | ProVolley | 2/3 | 0 | 0 |
| 3 | 5 | ProVolley | 1/3 | 1 | 0 |
| 3 | 11 | UTS | 2/3 | 0 | 0 |
| 3 | 21 | ProVolley | 0/3 | 0 | 0 |
| 3 | 27 | ProVolley | 2/3 | 1 | 1 |
| 3 | 37 | UTS | 1/3 | 0 | 0 |
| 3 | 38 | UTS | 1/3 | 0 | 0 |

For each missing outcome group, the table separates a *phase problem* from a *position-availability problem*. A model play prediction alone does not create the six checked shoe-floor points needed for court metrics. Before adding frames to the analysis, source-check the phase and identities and inspect the feet; preserve all 18 frozen points and report exclusions.
