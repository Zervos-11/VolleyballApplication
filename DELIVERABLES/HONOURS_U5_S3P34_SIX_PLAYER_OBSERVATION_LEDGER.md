# S3 P34 six-player full-span observation ledger

The [machine-readable ledger](../data/matches/yt_u5HnY2aNW14/screening/s3p34_six_player_observation_ledger.json) joins the six named UCLA players across every source frame from 36001 through 36138. Each slot preserves the tracker candidate, any existing 5 Hz source-reviewed grounded coordinate, and the targeted source visibility verdict for missing candidates. A candidate point does not become a validated floor point by appearing in this ledger. The [source-sequence verdict record](../data/matches/yt_u5HnY2aNW14/screening/s3p34_full_span_review/candidate_identity_source_review.json) lists the 47 inspected paired contact sheets and the limits of the visual identity assessment. This added pass was AI-assisted and has not received independent human adjudication.

| Evidence tier in this interval | Player slots | Meaning |
| --- | ---: | --- |
| Existing 5 Hz source review | 138 | Grounded positions accepted or rejected per player at 23 sampled instants. |
| Targeted gap sequence review | 39 | Visible player with no jersey-keyed candidate; no new floor coordinate. |
| Unsampled source sequence-reviewed candidate | 651 | Candidate-to-player continuity checked in paired 30 fps contact sheets; ground position unreviewed. |
| **Total** | **828** | **138 frames x six players.** |

Candidate boxes exist in 780/828 player slots and all six candidate boxes coexist in 104/138 frames. The 48 missing candidate slots occupy 34 frames; the targeted gap audit reports all of those players visible in the source sequence. Within the interval, the existing 5 Hz source review accepted 121 individual grounded proxies and eleven complete six-player frames. The sampled review also includes frame 36000 outside this interval, which explains its separate 126/144 denominator.

The 138 frames begin at a conservative live-looking start and end at the last reviewed live frame. They are not exact serve-contact to dead-ball boundaries. All 47 contact sheets were inspected in frame order. The 651 previously candidate-only slots have sequence-consistent visual assignments, but jersey digits are not independently readable at every frame and ground contacts outside the sampled review remain unassessed. Frame 36112 includes an airborne #15 without a usable floor point. Thus the ledger supports a six-player *observation and missingness account*, not a validated continuous six-grounded-position rally or full-rally distance.

Reproduce with `.\.venv\Scripts\python.exe scripts/build_u5_s3p34_six_player_observation_ledger.py`. The script checks the join against the saved candidate and source-review files.
