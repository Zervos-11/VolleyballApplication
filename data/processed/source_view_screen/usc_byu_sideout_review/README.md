# USC–BYU side-out event review

Open the [local frame review page](http://127.0.0.1:8044/usc-byu-sideout-review). It shows the unboxed 12-second clip at 30 fps. Use the slider or arrow keys to inspect the sequence. For each of USC's serve, BYU's reception, set and first attack, and the point-ending event, click **Exact** on a clear contact frame or mark **First possible** and **Last possible** to bracket it. Leave an event unmarked if the contact is not visible. Record whether USC served, whether BYU won, and the score before and after. Save the review.

The [source selection note](../../../../DELIVERABLES/HONOURS_USC_BYU_SIDEOUT_CANDIDATE_2026-11-07.md) records why this case was chosen. It was selected after watching the point and its outcome, so it is an exploratory exemplar outside the frozen Concordia–UCLA outcome sample. The [blank event protocol](event_protocol.json) contains coarse AI-assisted previews; those are not reviewer verdicts.

The [5-Hz detector proposals](raw_5hz_candidates.json) cover 60 sampled frames and 918 person boxes. They include both teams and nonplayers. Raw tracker IDs already drop for several BYU players; no candidate is accepted as a six-player trajectory or court position. The event review page deliberately does not show those boxes.

After the source review is saved, run `.\.venv\Scripts\python.exe scripts/analyze_usc_byu_sideout_event.py`. It calculates a reception-to-first-attack interval only if the saved event sequence, winner and score support the agreed side-out definition. No manual pixel positions are needed for this event measure. Full player tracking or court geometry would need a separate box, identity, ground-contact and positional review.
