# Primary-match image-plane snapshot screen

The [source-bound result](../data/matches/yt_u5HnY2aNW14/screening/image_plane_snapshot_screen.json) uses one locally source-checked six-player box frame per available frozen point. All **18** score-selected points stay in the denominator. The original pass supplies 15 snapshots (6 wins, 9 losses); a higher-resolution pass supplies two more winning snapshots. Set-three point 23 remains missing because overlapping players are not six distinct boxes.

Each player is represented by the **centre of the image box**. This allows airborne frames to contribute screen-space positions. The formulas measure pixel spacing, pixel-squared convex-hull area, and pixel dispersion. They are not 9 m court positions, movement trajectories, rotation states or rally-level summaries.

| Set | Wins with boxes | Losses with boxes | Availability |
| ---: | ---: | ---: | --- |
| 1 | 3/3 | 3/3 | 6/6 |
| 2 | 3/3 | 3/3 | 6/6 |
| 3 | 2/3 | 3/3 | 5/6 |

## Descriptive stability check

For each metric, the diagnostic contrast is the mean winning snapshot minus mean losing snapshot within each set, averaged equally over the three sets. The table compares the original 15-frame subset with the augmented 17-frame subset, compares box-centre and box-bottom image anchors, and reports the range after removing each available point in turn. These are sensitivity checks, **not effect estimates**.

| Image metric | Original 15 box-centre contrast | All 17 box-centre contrast | All 17 box-bottom contrast | All 17 box-centre leave-one-out range | Missing-win observed-range scenario |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mean pairwise spacing (px) | +32.58 | +28.66 | +28.54 | +20.49 to +36.59 | +19.98 to +38.89 |
| Convex hull area (px²) | -4696.21 | -5664.41 | -5198.10 | -10448.67 to -1792.37 | -8691.51 to -395.78 |
| Centroid dispersion (px) | +22.80 | +19.88 | +19.66 | +14.83 to +24.73 | +14.96 to +26.96 |

The available-frame rule leaves out one winning point and the recovered frames use a different detector setting. An [exact-frame source phase audit](HONOURS_U5_SNAPSHOT_PHASE_BALANCE.md) finds eight defensive, seven offensive and two serve/reset snapshots; the snapshots do not align the same interval across points. The near-court image is stable, but perspective and body posture also affect pixel distances. The final column substitutes the missing winning snapshot with the minimum or maximum **observed** value for each metric; it is a scenario, not a statistical interval or measured value. Therefore no significance test, winner association or court-metre claim follows from this table.

## Reproduction

Run `python scripts/build_u5_image_plane_snapshot_screen.py`. The JSON lists every point, source frame, detector pass, both box-centre and box-bottom image metrics, input hashes and missingness.
