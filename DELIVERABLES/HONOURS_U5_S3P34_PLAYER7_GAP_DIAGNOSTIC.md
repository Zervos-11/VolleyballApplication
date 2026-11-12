# S3 P34 UCLA #7 candidate-gap diagnosis

The saved full-packet review currently records UCLA #7 / player 4 as having no selected box at nine packet frames, and the prior 5-Hz ledger misses two more. This diagnostic preserves those verdicts.

At **36015, 36026, 36030 and 36031**, the original 960-pixel detector produced raw ID 9 person boxes, but the near-side box-bottom gate labelled them `net_boundary_review` and omitted them from the jersey-keyed candidate packet. This is a gate omission, not a person-detector omission. The staged court depths were 9.002, 9.029, 9.016 and 9.003 m. These box bottoms cannot be accepted as floor positions merely by changing the gate.

For the later sideways sequence, a 1600-pixel YOLOv8n pass produced local person proposals on all **7/7** checked frames 36124 and 36126–36131. These have not been adjudicated as UCLA #7 or accepted floor positions. [Proposal sheet](../data/matches/yt_u5HnY2aNW14/screening/s3p34_player7_gap_diagnostic/sideways_7_proposals.jpg), [larger crops](../data/matches/yt_u5HnY2aNW14/screening/s3p34_player7_gap_diagnostic/sideways_7_crops.jpg) and [machine-readable boxes](../data/matches/yt_u5HnY2aNW14/screening/s3p34_player7_gap_diagnostic/candidate_recovery.json).

The original 138-frame candidate and source-review records remain unchanged. A reviewer must compare these suggestions with unboxed frames and adjacent identity context before any correction is scored.
