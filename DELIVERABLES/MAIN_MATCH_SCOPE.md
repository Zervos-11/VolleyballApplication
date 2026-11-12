# Main analysis match: ProVolley vs UTS

The primary match for scored volleyball analysis is **[SVL - Premier Women ProVolley vs UTS](../data/matches/yt_FqE5pTJqx8g/source_record.json)**, match ID `yt_FqE5pTJqx8g`. This is the 1080p50 full-match video. Its pilot contains five selected rallies spread across the recording, saved player annotations, boundary reviews, and staged court calibration. A [123-point broadcast-score timeline](PROVOLLEY_SCORE_TIMELINE.md) now covers the three sets, with one opening score and one set-one winning point distinguished from directly observed score changes.

The [automatic score reader](AUTOMATIC_SCORE_READER.md) now reproduces that 123-point sequence from the fixed broadcast overlay after one-time template calibration. The manually reviewed timeline remains its same-video reference; point-by-point manual score entry is not required for the main match analysis.

| Pilot rally | Set | Source score before → after (ProVolley–UTS) | Point to | Score evidence frames |
| --- | ---: | --- | --- | --- |
| r1 | 1 | 5–4 → 5–5 | UTS | 20950 → 21690 |
| r2 | 2 | 1–0 → 2–0 | ProVolley | 77900 → 78722 |
| r3 | 2 | 9–7 → 10–7 | ProVolley | 96450 → 97260 |
| r4 | 3 | 1–0 → 2–0 | ProVolley | 149890 → 151420 |
| r5 | 3 | 14–5 → 14–6 | UTS | 176140 → 176800 |

The [five before/after score crops](../data/processed/fqe_score_anchor_check.jpg) show these changes in the video's own score overlay. The [source-bound score review](../data/processed/fqe_score_anchor_review.json) records the frames and agrees with the earlier [pilot selection](../data/matches/yt_FqE5pTJqx8g/pilot/selection.json). The overlay updates a few seconds after play, so these are **point-score anchors**, not exact end-frame labels. The [five saved boundaries](../data/matches/yt_FqE5pTJqx8g/pilot/boundary_review.json) were checked by the annotator, with r1's precise candidate end still under source review. These five rows are the source-reviewed pilot anchors within the broader score timeline.

The D79, AoEP and em6z videos are separate sources for tracker or method validation. The D79 visibility audit and box coverage describe **SUV X WSV vs NOVA**, and none of those player IDs or distances should appear as ProVolley vs UTS results. The D79-to-R1 transfer study tests a method on the primary video's r1; its D79 input remains validation evidence.

The current honours score result and its limits are assembled in the [methods and results draft](HONOURS_METHODS_RESULTS_DRAFT.md). The [point-by-point source review queue](../data/processed/fqe_rally_review_queue.csv) and [local full-match review page](http://127.0.0.1:8077/match-score) remain available if exact rally durations are later needed. Extend player tracking and physical-distance estimates only where identity and floor-contact gates pass. The score timeline alone does not locate exact rallies. The [R1 case-study readout](R1_CASE_STUDY_READOUT.md) and [project status](PROJECT_STATUS.md) describe what is currently measured on the main match.

**Honours scope decision:** An exact serve-contact frame for every scored point is not required for the final score and point-winner analysis. In particular, set-one point three can remain a partial boundary review because its far-side serve contact is not visible well enough to label. Exclude that point from any exact rally-duration calculation, and state the denominator of any duration or movement subset. Do not invent a start frame from the whistle, score change, or player setup. This does not change the source-review requirements for any individual rally used to report duration or player movement.
