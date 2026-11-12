# Exact-frame phase audit of the primary-match snapshot screen

The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/snapshot_phase_balance_audit.json) reviews the **exact** 17 six-box source frames, each with unboxed video at −12, 0 and +12 frames (±0.4 s). The [context sheets](../data/matches/yt_u5HnY2aNW14/screening/snapshot_phase_context/index.json) and [adjudications](../data/matches/yt_u5HnY2aNW14/screening/snapshot_phase_source_qc.json) retain the evidence and single-reviewer phase calls. The 18th frozen point, a win, has no correct six-player snapshot.

The 17 snapshots comprise 8 near-side defensive, 7 near-side offensive and 2 serve/reset frames. The broad labels describe visible team posture and ball-control direction; they do not establish an exact touch, live-rally boundary or court-floor position.

| Set | Near-side phase | Wins | Losses | Mean win − loss spacing (px) |
| ---: | --- | ---: | ---: | ---: |
| 1 | near defense | 2 | 1 | +82.30 |
| 1 | near offense | 1 | 1 | +128.18 |
| 1 | serve or reset | 0 | 1 | — |
| 2 | near defense | 0 | 2 | — |
| 2 | near offense | 2 | 1 | +53.64 |
| 2 | serve or reset | 1 | 0 | — |
| 3 | near defense | 1 | 2 | -9.03 |
| 3 | near offense | 1 | 1 | -61.16 |

Only **13/18** frozen points fall in the 5 open-play set-by-phase cells containing both outcomes. Each outcome has at most two snapshots per cell. The table is a selection and phase diagnostic; its differences are not winner effects. The JSON also records hull-area and dispersion differences where both outcomes exist. The original all-snapshot contrasts pool incompatible phases, including serve/reset frames. Neither screen supports a significance test or court-metre association.

## Reproduction

Run `python scripts/render_u5_snapshot_phase_context.py`, inspect the source sheets, then `python scripts/audit_u5_snapshot_phase_balance.py`. Review labels are a separate manually adjudicated input; rerunning the rendering script does not invent them.
