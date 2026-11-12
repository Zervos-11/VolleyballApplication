# Six-player box proxy availability

The user's proposed body/box movement proxy does not require a separately clicked shoe contact on every frame. This [source-bound screen](../data/processed/honours_box_proxy_availability.json) counts the saved boxes against the existing [phase navigation scan](HONOURS_SAVED_GAME_STATE_SCAN.md). It does not change the source labels or the strict floor-coordinate metric gate.

Of 61 saved positions, **24** have six usable boxes, versus 18 with six marked visible contacts. **16** of the six-box frames are source-confirmed live or model-proposed play; only **8** are source-confirmed live.

| Set | Winner | Six-box frames | Six-box navigation frames | Source-confirmed live six-box frames |
| ---: | --- | ---: | ---: | ---: |
| 1 | ProVolley | 5 | 3 | 3 |
| 1 | UTS | 2 | 1 | 1 |
| 2 | ProVolley | 13 | 10 | 3 |
| 2 | UTS | 2 | 0 | 0 |
| 3 | ProVolley | 2 | 2 | 1 |
| 3 | UTS | 0 | 0 | 0 |

This relaxes the need for individual shoe clicks for an **image-plane movement proxy**. A box centre can describe apparent movement on a fixed camera, with results in pixels or a clearly defined normalized image scale. It is elevated above the floor and cannot be sent directly through the court homography to claim metre-valued coverage or spacing. For court coordinates, the box bottom centre can be evaluated as a *ground-anchor estimate* when the player is grounded and fully visible; its error should be checked against a small set of manually reviewed floor contacts. Airborne, clipped and occluded cases remain unknown.

There are no six-box navigation frames for UTS-won points in sets two or three. Relaxing foot-click availability alone therefore does not create the missing outcome groups for the planned set-stratified comparison. More source-backed player positions or an explicitly narrower research question would still be needed.
