# Direct in-run position reference

The [source-bound result](../data/matches/yt_u5HnY2aNW14/screening/full_run_position_reference.json) joins two existing clear-grounded manual shoe midpoints at S3 P34 source frame 36084 to the new full-clip raw-ID boxes. The nearest box match is unique within 45 image pixels and its jersey is confirmed in the [every-sample identity review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md). These are reused single-reviewer marks, not new independent labels.

| Jersey | Raw ID | Current box to manual shoe | Earlier fixed-box proxy error |
| --- | ---: | ---: | ---: |
| #7 | 2 | 0.216 m | 0.094 m |
| #12 | 25 | 0.523 m | 0.729 m |

The two current box-bottom errors have median **0.369 m** and maximum **0.523 m**. The earlier fixed-box numbers come from a different proxy method; their change is not a controlled accuracy improvement. Four teammates at this frame and every other frame in these runs lack a joined manual shoe check. This does not validate a full-rally court trajectory.

Reproduce with `python scripts/audit_u5_full_run_position_reference.py`.
