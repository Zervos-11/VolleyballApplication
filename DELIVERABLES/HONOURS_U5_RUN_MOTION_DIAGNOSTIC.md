# Six-player run motion diagnostic

The [source-bound data](../data/matches/yt_u5HnY2aNW14/screening/long_run_proxy_motion_diagnostic.json) calculate the three implemented geometry formulas on all **66 sampled instants** in the eight source-membership-checked long runs. These are box-bottom proxies from two detector settings, **not validated floor positions or final rally metrics**.

| Set | Point | Near team result | Samples | Span (s) | Largest 0.2 s proxy step (m) | Median spacing (m) | Median hull (m²) | Median dispersion (m) |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 6 | Lost | 5 | 0.8 | 0.641 | 5.099 | 29.371 | 3.438 |
| 1 | 34 | Lost | 7 | 1.2 | 0.396 | 5.035 | 26.892 | 3.462 |
| 1 | 37 | Lost | 10 | 1.8 | 0.709 | 3.710 | 15.545 | 2.492 |
| 2 | 2 | Lost | 8 | 1.4 | 0.161 | 4.654 | 25.063 | 3.129 |
| 2 | 6 | Lost | 7 | 1.2 | 0.598 | 4.680 | 25.662 | 3.161 |
| 2 | 26 | Lost | 7 | 1.2 | 0.406 | 5.046 | 29.711 | 3.403 |
| 3 | 34 | Lost | 9 | 1.6 | 0.779 | 4.911 | 26.595 | 3.318 |
| 3 | 13 | Won | 13 | 2.4 | 0.805 | 4.108 | 19.056 | 2.756 |

## Interpretation

The one winning run is set-three point 13. Its [reviewed source sheets](../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_review/) show a blue right-side player airborne in the early part of the run. A box bottom at that instant is not that player’s floor location. The seven losing runs came from the original detector pass; the winning run came from a higher-resolution pass. Their durations and phases also differ. The table is therefore an implementation and motion-continuity diagnostic, not a winner comparison. No outcome effect size or significance test is calculated.

Every row retains **zero validated metric frames**. A final comparison still requires a fixed live phase, grounded source-reviewed positions for all six players at every included sample, a validated court transform, and enough eligible points in both outcome groups within sets.

Reproduce with `python scripts/audit_u5_long_run_proxy_motion.py`.
