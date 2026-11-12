# USC–BYU elevated-view transfer addendum

**Source:** [USC (5) v BYU (6), 7 March 2025](https://www.youtube.com/watch?v=b1bJ5WN05Qw). The local 04:55–05:55 excerpt is 1920 × 1080 pixels at 30 fps, with SHA-256 `873de902460784652506226a5adbc4725e0be0f178c07178e66c1a6c6932ab45`. The camera is elevated and appears fixed across the sampled minute. BYU occupies the near court in dark navy with a blue libero; USC is red on the far side. The view keeps the court and most players visible, making it suitable for a **source-reviewed transfer feasibility check**.

The [source-time selection addendum](../data/processed/source_view_screen/transfer_source_only_selection_2026-11-06_v2.json) retains the first new point after 05:00 before this case's detector screen. One-second unboxed [source frames](../data/processed/source_view_screen/usc_byu_source_screen_1s.jpg) bracket the next serve near 05:18–05:20 and the point ending near 05:24–05:25; exact event frames are not certified. The frozen local screening interval is frames 660–930 at six-frame steps, giving **46 planned 5-Hz instants**. The original two-case selection file remains unchanged and is hash-bound in the addendum. Local excerpt frame numbers have not been aligned to a full-video download.

The first raw YOLOv8n/ByteTrack pass produced **777 all-person proposals** over those 46 instants. The [five-frame provisional spot check](../data/processed/source_view_screen/usc_byu_provisional_spotcheck.jpg) shows that raw IDs can switch to far-side red players near the net. These proposals are **not** accepted near-side tracking or floor positions. The review page therefore displays every new-case candidate as **Uncertain** until checked against the source. The six stable slot labels begin from a source-visible near-side group at excerpt frame 720; earlier context frames remain unassigned by the suggestion generator rather than being fabricated. The raw source/box review is currently **0/46 saved**.

Review links:

- [BYU six-player source review](http://127.0.0.1:8043/?case=yt_b1bJ5WN05Qw)
- [BYU court landmark check](http://127.0.0.1:8043/calibration?case=yt_b1bJ5WN05Qw)
- [BYU selected shoe reference](http://127.0.0.1:8043/position-reference?case=yt_b1bJ5WN05Qw)

The [separate reference-plan addendum](../data/processed/source_view_screen/elevated_transfer_review/position_reference_plan_2026-11-06_v2.json) selects frames 762, 810 and 858 by source time. It was written after a raw detector spot check, so later shoe marks will be unblinded supplementary comparisons. The selected point remains in the denominator even if the boxes fail. Do not merge this point with the Concordia–UCLA outcome comparison or report it as validated until the source, court and shoe reviews have been saved and scored.
