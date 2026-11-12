# Exploratory set-three image-box metric example

The [source-bound record](../data/processed/honours_set3_image_proxy_demo.json) applies the same three geometric formulas to box **centres** in source-image pixels for three visually screened live snapshots. The frame contexts show ball and continuing play: [ProVolley-won point 5](../data/processed/honours_missing_outcome_box_candidates/s3_p5_f155799_context.jpg), [UTS-won point 11](../data/processed/honours_missing_outcome_box_candidates/s3_p11_f162695_context.jpg), and [UTS-won point 37](../data/processed/honours_missing_outcome_box_candidates/s3_p37_f204263_context.jpg). Point 5 uses the [saved six boxes](../data/processed/honours_missing_outcome_box_candidates/s3_p5_f155799_saved.jpg); the [visual screen](HONOURS_MISSING_OUTCOME_VISUAL_SCREEN.md) records the detector choices for points 11 and 37. Point 11 has an airborne player. The same visual screen excludes a saved point-27 box on a far-side player.

| Set-three point | Winner | Frame | Mean spacing (px) | Hull area (px²) | Centroid dispersion (px) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 5 | ProVolley | 155799 | 359.3 | 42774 | 237.6 |
| 11 | UTS | 162695 | 262.9 | 19161 | 174.5 |
| 37 | UTS | 204263 | 381.4 | 49925 | 266.2 |

This proves the user's simpler box-centre position rule can be implemented without six manually clicked shoes at these snapshots. The units are **image pixels**, not metres; perspective and posture can change them. The frames were selected by box availability after outcomes were known, and there is only one frame per point with unequal 1-versus-2 groups. No rally-level movement, effect size, significance test or association with winning is inferred. The strict court-coordinate calculator and its zero validated-frame denominator are unchanged.
