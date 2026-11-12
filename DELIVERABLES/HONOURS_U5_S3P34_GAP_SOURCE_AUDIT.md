# S3 P34 targeted source review of missing candidates

The [source-linked verdict record](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/gap_source_verdicts.json) checks the nine missing-candidate runs identified by the [full-span review queue](HONOURS_U5_S3P34_FULL_SPAN_REVIEW_QUEUE.md). The paired contact sheets show the unboxed source frame beside the detector proposals. This is a targeted visual audit of candidate gaps, not a review of every player in every 30-fps frame.

| Jersey | Missing candidate slots | Source review of those runs |
| --- | ---: | --- |
| UCLA #7 | 11 | Player remains visible. Four missing slots occur early; seven occur during or after a front-court overlap. No independent floor marks were made. |
| UCLA #21 | 22 | Player remains visible. Six early slots show apparent ground contact without a jersey-keyed candidate; the later 16-slot net sequence includes jumping or uncertain ground contact. |
| UCLA #15 | 15 | Player remains visible in the late front-court jump and landing sequence. Ground contact is not settled frame by frame. |
| **Total** | **48** | These slots occupy 34 distinct frames because missing runs overlap. |

The 48/48 source-visible finding is limited to the *missing jersey-keyed candidate slots* in the 138-frame candidate interval. Some jersey digits cannot be read independently in each image; the association uses the neighbouring source sequence. It does not establish that every player's jersey and floor point have been verified at every frame. An alternate raw proposal may be visible in the detector view, but it is not a source-approved court position for the missing jersey. In particular, the jump and overlap frames cannot be repaired by carrying forward a box bottom or applying the court homography to an airborne body.

[Page 38](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/review_page_38.jpg) gives a decisive example at frame 36112: #15 is visibly airborne and has no jersey-keyed candidate. A grounded box-bottom court position cannot be accepted for that player at that instant under the project's strict rule. Recovering a detector box elsewhere would not make this interval a complete observed six-grounded-position rally.

The [full 828-slot review template](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/frame_player_review_template.csv) remains unfilled. The strict full-rally result is still zero: this targeted audit improves the missingness explanation but supplies no new accepted floor coordinates, exact play boundaries or independent calibration approval.
