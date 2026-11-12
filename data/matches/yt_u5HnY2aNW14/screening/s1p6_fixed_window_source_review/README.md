# S1 P6 source-only fixed-window packet

The [all-point selection protocol](../source_only_fixed_window_protocol.json) froze this
25-frame window at source frames **1759–1783**, inclusive, before its tracking
availability was inspected for this review. Its five planned 5-Hz samples are
1759, 1765, 1771, 1777 and 1783. The [manifest](manifest.json) binds the five
unboxed 1280 × 720 source images to the source video and protocol hashes.

The [source-only review](completed.csv) is now frozen. The reviewer marked all
five frames live, 28 player slots grounded and two airborne at frame 1783. The
window remains frozen; the airborne frame is retained with unknown floor
positions.

Open the local [paired box review](http://127.0.0.1:8041/s1p6-paired-review).
The source image shows your frozen blue shoe-click numbers and yellow detector
boxes with raw IDs. For each of the five frames, correct the suggested box and
floor-proxy decisions where needed, tick the visual-check confirmation, and
save. Freeze the paired review after all five frames are saved. The source-only
page remains [read-only](http://127.0.0.1:8041/s1p6-fixed-window-review).

The [exact-frame diagnostic](../../../../../DELIVERABLES/HONOURS_U5_S1P6_FIXED_WINDOW_SOURCE_RESULT.md)
found one grounded player whose box was excluded by the simple near-side
cutoff at frame 1759. The same reviewer
has seen earlier tracker output, so this is a documented single-reviewer
diagnostic, not an independent blinded reference. Paired box judgments remain
separate from calibration approval and the strict metric gate.

The paired review is also frozen. Its original page hid two above-cutoff boxes
at the final airborne frame; the two saved “no box” choices there cannot be
read as evidence of detector omission. The page now displays those candidate
boxes for inspection, while retaining the frozen answers. Their floor points
remain null because the source reviewer marked both players airborne.

The existing source-only and tracker screens for all 18 points predate this
selection. The deterministic rule did not inspect tracker fields, but it is not
prospectively blind. No strict metric input has been approved.
