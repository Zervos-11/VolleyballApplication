# Five-sample source-image review

I inspected the [five-frame overlay sheets](../data/matches/yt_u5HnY2aNW14/screening/flow_window_five_sample_review/) for each of the eight screened 0.8 s candidate windows. The [review record](../data/matches/yt_u5HnY2aNW14/screening/flow_window_five_sample_source_qc.json) is bound to the sheet index and every image hash is checked by the [audit](../data/matches/yt_u5HnY2aNW14/screening/flow_window_five_sample_audit.json). At the five displayed instants, all eight have six boxes that appear to remain with the same near-side people. This is a coarse transfer screen, not a position-error measurement or certified player identity.

| Point | Screen result | Qualification |
| --- | --- | --- |
| S1 P5 | No obvious transfer at five instants | All six near-side boxes follow the same visible players across the five panels; right-side player approaches the net. |
| S1 P6 | No obvious transfer at five instants | The front-row blue players stay distinct through the five panels; boxes vary with posture. |
| S1 P18 | No obvious transfer at five instants | Six boxes follow the same players; the rightmost near-side player remains outside the sideline and is not a valid on-court coordinate. |
| S2 P6 | No obvious transfer at five instants | The three near-side front-row players stay distinguishable at the five instants despite the far-side dive. |
| S2 P28 | No obvious transfer at five instants | The central near-side player moves into a low posture near the net; the translated box remains associated visually, but its centre is posture sensitive. |
| S3 P13 | No obvious transfer at five instants | All six near-side boxes remain on their visually corresponding players at the sampled instants. |
| S3 P27 | No obvious transfer at five instants | Front-row boxes retain distinct near-side players at the sampled instants. |
| S3 P34 | No obvious transfer at five instants | All six boxes remain on corresponding near-side players; pose changes affect box-centre location. |

The source frames between displayed instants, box-centre error, floor contact and court positions are not manually labelled. S1 P18 includes a player beyond the sideline; S2 P28 includes a low posture near the net. The earlier [pixel-space geometry](HONOURS_U5_FLOW_WINDOW_GEOMETRY.md) remains a method diagnostic. This review leaves **zero validated court trajectory windows**, so the signed court-metric outcome comparison remains incomplete.

Reproduce the audit with `python scripts/audit_u5_flow_five_sample_source.py`.
