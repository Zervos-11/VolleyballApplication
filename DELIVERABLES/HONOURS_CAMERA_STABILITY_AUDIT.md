# Court image alignment check

The [source-bound registration record](../data/processed/honours_camera_stability_audit.json) compares the static gym wall in each of the 61 saved sample frames with a calibration reference frame. It excludes score graphics, players, net and floor from SIFT feature detection and uses a robust partial-affine fit. This measures **image-coordinate alignment**, not physical camera movement, court-line accuracy or shoe-position accuracy.

| Set | Registered frames | Maximum absolute x shift (px) | Maximum absolute y shift (px) |
| ---: | ---: | ---: | ---: |
| 1 | 16/16 | 13.424 | 3.079 |
| 2 | 27/27 | 0.328 | 0.183 |
| 3 | 18/18 | 0.475 | 0.231 |

Any frame with a weak or failed registration is identified in the JSON and cannot inherit a stability claim. Set 3 currently borrows the set 2 court transform. Court-line checks on exact frames, especially in set 3, are needed before approving any metre coordinate for final metrics.

Set-one point 39 has an approximately 12 px scene offset relative to the earlier set-one reference. An [independent phase-correlation and ECC check](../data/processed/honours_image_alignment_diagnostic/diagnostic.json) finds the same offset. The [direct interleaved source crop](../data/processed/honours_image_alignment_diagnostic/wall_checker_65656.jpg) shows the wall features at different pixel positions. This does not identify the physical cause; a fixed camera and an encoded-image offset are compatible.
