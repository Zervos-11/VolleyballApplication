# Frozen rally sample: first source-frame screen

The [18-point sample](HONOURS_RALLY_SAMPLE.md) now has three exact decoded source frames per point. The [manifest](../data/processed/honours_sample_sheets/manifest.json) binds the sheets to the source hash, sample and review queue. These are **navigation stills**, not a frame-by-frame rally review. The script is [build_honours_sample_sheets.py](../scripts/build_honours_sample_sheets.py).

| Set | Source-frame sheet | Preliminary observation |
| --- | --- | --- |
| 1 | [Six selected points](../data/processed/honours_sample_sheets/set_1_sample_navigation.jpg) | Same broad baseline view in the sampled stills. A near-side server is partly at the image edge in point 2; the chosen stills cannot establish complete six-player floor coverage. |
| 2 | [Six selected points](../data/processed/honours_sample_sheets/set_2_sample_navigation.jpg) | Same broad baseline view, with near-side uniforms different from sets 1 and 3. Point 2 uses a saved pilot boundary; other displayed times are estimates. |
| 3 | [Six selected points](../data/processed/honours_sample_sheets/set_3_sample_navigation.jpg) | Same broad baseline view. Some near-side servers or receivers are near the right image edge; selected stills do not establish continuous visibility. |

**Critical team-assignment gate:** you confirmed that UTS changes court sides. The near-side uniforms visibly change between sets, and the [provisional side map](../data/processed/honours_near_side_assignment.json) suggests ProVolley near in sets 1 and 3 and UTS near in set 2. That mapping is an analyst inference from sampled source stills and pilot serve observations; it has not been checked against a team roster or complete source intervals. The primary [source record](../data/matches/yt_FqE5pTJqx8g/source_record.json) still lists court-side assignment as `not_verified`. The score winner must not yet be used as a near-side win/loss label for a spatial test. Verify the near-side team on each selected interval before linking movement to outcomes.

**Boundary gate:** the 17 unsaved rows display heuristic start/middle/end estimates from the score review queue; the saved set-two point-two row uses its pilot contact/end frames. Even the saved pilot boundary has not independently established full-team floor-position quality. Score flips occur after play and cannot substitute for serve contacts or point ends.

The sampled stills show a usable court view for a closer source review, but **no point has been promoted to an analyzable team-metric rally** by this screen. The next review must record accepted intervals, near-side team, six named floor positions or explicit missing states, and camera/court-checkpoint validity. Preserve each selected point and record exclusions instead of replacing difficult points with easier ones.
