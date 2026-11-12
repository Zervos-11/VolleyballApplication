# Short box-centre optical-flow pilot

The [source-bound pilot](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_pilot.json) starts from each of the 17 locally reviewed six-player boxes. It tracks torso features through every source frame over 0.4 s before and after the anchor, then translates each player box to five 5 Hz sample times. The method works in image pixels and retains airborne players as screen-space candidates.

The [endpoint source review](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_source_qc.json) checks the unboxed source and translated boxes at the first, anchor and last sample for all 17 windows. All 17 have six *algorithmic* candidates at five sample times. Thirteen have no obvious wrong-person transfer at the displayed endpoints; four remain uncertain due to crossings or net overlap. After removing two serve/reset windows and set-and-phase groups without both outcomes, only **8/18** frozen points remain as short candidate comparison windows. These eight are not fully validated trajectories.

| Check | Result |
| --- | ---: |
| Frozen point denominator | 18 |
| Correct six-box anchors | 17 |
| Six flow candidates at all five samples | 17 |
| No obvious transfer at displayed endpoints | 13 |
| Uncertain overlap at displayed endpoints | 4 |
| Clear endpoint, open-play anchor | 11 |
| Clear endpoint, open-play and set-phase matched | 8 |
| Same-raw-ID detector comparisons | 334 |
| Median / 95th-percentile / maximum detector disagreement (px) | 5.10 / 16.40 / 40.35 |
| Validated court-trajectory windows | 0 |

The detector comparison uses the same video and raw IDs, so it is **not an independent manual accuracy reference**. A translated rigid box cannot adjust to pose or height changes. The two ±0.4 s endpoints were visually screened, but the intermediate samples were not adjudicated for named identity; none of the floor positions has passed the court-metric gate. The four uncertain windows stay unresolved. The 18th frozen point remains missing six correct anchor boxes. This pilot improves short image-plane coverage but does not unlock a statistical court-metric outcome analysis.

The [row-level audit](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_audit.json) and [review sheets](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_pilot/) retain every point and overlay. Reproduce with `python scripts/pilot_u5_box_centre_flow.py` followed by `python scripts/audit_u5_box_centre_flow.py`.
