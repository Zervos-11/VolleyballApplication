# Five in-rally six-player position references

At S3 P34 source frames 36036, 36066, 36078, 36096 and 36138, six UCLA player shoe positions were marked by one reviewer. The original 36066 and 36078 marks were made on unboxed source images before the detector comparison. The three added marks are supplementary unblinded checks made after seeing tracker boxes. Estimated shoe reading uncertainty is 12-15 source pixels per axis. These five frames span early, middle and late play.

| Frame | Median player difference (m) | Maximum (m) | Spacing difference (m) | Hull difference (m^2) | Dispersion difference (m) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 36036 | 0.183 | 0.338 | +0.050 | +0.316 | +0.043 |
| 36066 | 0.266 | 0.412 | +0.152 | +1.303 | +0.101 |
| 36078 | 0.260 | 0.418 | +0.028 | +0.050 | +0.022 |
| 36096 | 0.363 | 0.445 | +0.005 | -0.101 | +0.005 |
| 36138 | 0.298 | 0.595 | +0.073 | +0.663 | +0.066 |

Across the 30 selected player positions, median difference is **0.298 m** and maximum is **0.595 m**.

### Frame 36036

[Manual marks](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36036_manual_qc.json) and [source image](../data/matches/yt_u5HnY2aNW14/screening/s3p34_validation_review/source_36036.png).

![Red manual shoe midpoint, green box bottom](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36036_reference_overlay.png)

| Jersey | Box-to-shoe difference (m) |
| --- | ---: |
| #28 | 0.308 |
| #21 | 0.145 |
| #15 | 0.065 |
| #7 | 0.139 |
| #19 | 0.338 |
| #12 | 0.222 |

### Frame 36066

[Manual marks](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36066_manual_qc.json) and [source image](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/frame_36066.png).

![Red manual shoe midpoint, green box bottom](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36066_reference_overlay.png)

| Jersey | Box-to-shoe difference (m) |
| --- | ---: |
| #28 | 0.254 |
| #21 | 0.278 |
| #15 | 0.205 |
| #7 | 0.251 |
| #19 | 0.373 |
| #12 | 0.412 |

### Frame 36078

[Manual marks](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36078_manual_qc.json) and [source image](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/frame_36078.png).

![Red manual shoe midpoint, green box bottom](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36078_reference_overlay.png)

| Jersey | Box-to-shoe difference (m) |
| --- | ---: |
| #28 | 0.306 |
| #21 | 0.310 |
| #15 | 0.192 |
| #7 | 0.162 |
| #19 | 0.418 |
| #12 | 0.214 |

### Frame 36096

[Manual marks](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36096_manual_qc.json) and [source image](../data/matches/yt_u5HnY2aNW14/screening/s3p34_validation_review/source_36096.png).

![Red manual shoe midpoint, green box bottom](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36096_reference_overlay.png)

| Jersey | Box-to-shoe difference (m) |
| --- | ---: |
| #28 | 0.387 |
| #21 | 0.445 |
| #15 | 0.278 |
| #7 | 0.337 |
| #19 | 0.436 |
| #12 | 0.339 |

### Frame 36138

[Manual marks](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36138_manual_qc.json) and [source image](../data/matches/yt_u5HnY2aNW14/screening/s3p34_validation_review/source_36138.png).

![Red manual shoe midpoint, green box bottom](../data/matches/yt_u5HnY2aNW14/screening/full_rally_validation_frames/s3_p34_f36138_reference_overlay.png)

| Jersey | Box-to-shoe difference (m) |
| --- | ---: |
| #28 | 0.264 |
| #21 | 0.291 |
| #15 | 0.353 |
| #7 | 0.064 |
| #19 | 0.595 |
| #12 | 0.305 |

The [audit JSON](../data/matches/yt_u5HnY2aNW14/screening/full_rally_live_reference_audit.json) contains all image and court coordinates and source hashes. These are five selected single-reviewer source-frame comparisons; three are unblinded. They do not validate the full rally, every-frame jersey assignment, airborne positions, or outcome effects.

Reproduce with `.\.venv\Scripts\python.exe scripts/audit_u5_live_reference_frame.py`.
