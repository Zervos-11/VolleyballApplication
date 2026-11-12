# ProVolley court calibration quality check

The staged [set-one transform](../data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r1.json) and [set-two/three transform](../data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json) map the near baseline to y=0 m, the attack line to y=6 m, and extrapolate to the net floor at y=9 m. The court is 9 m wide. The four fitted landmarks come from the baseline and attack-line intersections with the sidelines.

An independently marked net-floor line is the available held-out floor landmark. Its depth residual is **-0.061 to -0.049 m** across set one's court width and **+0.013 to +0.157 m** for the set-two/three transform. These are line residuals, not errors in player positions.

The [61-frame static-background check](HONOURS_CAMERA_STABILITY_AUDIT.md) registered all saved sample frames. For the [eight live-play court candidates](HONOURS_CANDIDATE_PHASE_QC.md), the largest fitted court-point movement relative to its reference was **0.497 px**. The representative [exact-frame overlays](../data/processed/honours_court_alignment_sheets/manifest.json) show the staged lines on source frames in all three sets.

| Set | Point | Live frame | Maximum fitted court-point displacement (px) | Static-wall inliers |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 2 | 8643 | 0.362 | 327 |
| 1 | 7 | 15505 | 0.167 | 356 |
| 1 | 9 | 19345 | 0.073 | 398 |
| 1 | 23 | 36366 | 0.132 | 340 |
| 2 | 2 | 78050 | 0.104 | 537 |
| 2 | 2 | 78100 | 0.124 | 540 |
| 2 | 2 | 78400 | 0.212 | 414 |
| 3 | 27 | 187701 | 0.497 | 178 |

**Bounded geometry decision:** Pass the operational screen of under 2 px camera displacement on each live frame and under 0.2 m held-out net-line depth residual over x=0..9 m. This supports using the existing transforms as *staged court geometry for these eight snapshots*. It does not approve an individual foot click or a final metre-valued team metric. Set 3 shares the set-two transform because its wall registration remains within the observed small movements; it has no separately marked held-out net line.

**Exception:** At set-one point 39, static wall features appear about 12 px left of their earlier pixel positions. This agrees across [SIFT registration](../data/processed/honours_camera_stability_audit.json), [phase correlation and ECC](../data/processed/honours_image_alignment_diagnostic/diagnostic.json), and the [direct source crop](../data/processed/honours_image_alignment_diagnostic/wall_checker_65656.jpg). **No physical camera movement is established.** Its only nominal six-player snapshot is [before the serve](HONOURS_CANDIDATE_PHASE_QC.md) and is excluded from live-play measurement. If a later frame from that point is analysed, it needs a source-frame-specific court transform or exclusion because its pixels differ from the calibration reference. The original calibration and player labels have not been altered.

**Remaining measurement gate:** Confirm the near-side team and six identities, check shoe-floor contacts against the source, and choose comparable live phases. The current strict metric calculator still has zero final eligible frames. No outcome association follows from this calibration screen.
