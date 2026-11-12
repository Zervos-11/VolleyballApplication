# Set-three matched-window pilot

This pilot used one UCLA win (point 13) and one UCLA loss (point 34). The [source-bound review record](../data/matches/yt_u5HnY2aNW14/screening/matched_window_pilot_source_qc.json) retains both attempts and their frame notes. Each candidate window spans five 5 Hz samples over 0.8 s. Team membership at the sampled instants was checked against the source video by one reviewer.

**Measurement distinction:** Airborne players can still be tracked by the centre of their image boxes. That gives pixel-space motion and geometry; it does not require a visible shoe contact. This camera is elevated and oblique rather than exactly overhead, and a body-box centre changes with pose and height. Projecting that centre through the floor homography would not yield a verified court-floor position.

## Fixed first-run window

The rule was the **first five consecutive samples** of each point’s longest six-ID run, chosen before this frame-level ground review. The win frames are 29881–29905; the loss frames are 36054–36078. The [winning source pack](../data/matches/yt_u5HnY2aNW14/screening/matched_window_pilot/) shows raw ID 2 with both shoes above the floor at frame 29881. Its subsequent rapid footwork makes box-bottom support uncertain. The win shows a near-side attack followed by a far-side scramble; the loss shows the opponent preparing an attack. These are different phases. The fixed-window pilot therefore fails the **matched-phase outcome comparison**. Its box centres remain usable as image-plane candidates; its box bottoms do not pass the metre-valued court-position gate.

## Revised phase candidate

After that failure, a second exploratory candidate used win frames 29917–29941 and the same loss frames. The [revised source pack](../data/matches/yt_u5HnY2aNW14/screening/matched_window_pilot_phase/) shows both teams near an opponent attack setup. This was selected after inspecting phase images, so it is a method-development pilot rather than a prespecified outcome window. The winning player’s fast lateral footwork and overlap still prevent certification of six grounded box-bottom anchors on every sample for the floor-homography method. Exact ball contact and the full live window are not certified.

| Candidate | Point | Result | Frames | Median proxy spacing (m) | Median proxy hull (m²) | Median proxy dispersion (m) | Strict eligible frames |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| initial | 13 | Won | 29881–29905 | 3.805 | 15.477 | 2.489 | 0 |
| initial | 34 | Lost | 36054–36078 | 4.831 | 26.150 | 3.264 | 0 |
| revised_phase | 13 | Won | 29917–29941 | 4.427 | 21.575 | 2.980 | 0 |
| revised_phase | 34 | Lost | 36054–36078 | 4.831 | 26.150 | 3.264 | 0 |

The same 20 displayed frame instances also have six image-plane box-centre coordinates each. Their per-window median pixel-space geometry is recorded in the JSON; the repeated loss window means there are 15 distinct source frames. Airborne status alone does not exclude these screen-space candidates.

| Candidate | Point | Image spacing (px) | Image hull (px²) | Image dispersion (px) |
| --- | ---: | ---: | ---: | ---: |
| initial | 13 | 236.2 | 50344.3 | 151.6 |
| initial | 34 | 284.2 | 80796.6 | 183.7 |
| revised_phase | 13 | 260.1 | 64819.8 | 167.5 |
| revised_phase | 34 | 284.2 | 80796.6 | 183.7 |

The metre-valued numbers above are **box-bottom implementation diagnostics**. The loss window is repeated in the two attempts, and there is one point per outcome. No winner effect size or significance test is justified.

**Decision:** The initial windows are not phase matched. The revised windows are exploratory and have only one point per outcome. Pixel-space box-centre tracking is feasible in these frames, including airborne ones, but neither attempt supplies a validated six-player court-metric window or a defensible winner comparison. A final court-coordinate analysis still needs a common phase rule, checked floor-position proxy and enough eligible points in both outcome groups.

Reproduce with `python scripts/render_u5_matched_window_pilot.py`, `python scripts/render_u5_matched_window_pilot.py --phase-aligned`, then `python scripts/adjudicate_u5_matched_window_pilot.py`.
