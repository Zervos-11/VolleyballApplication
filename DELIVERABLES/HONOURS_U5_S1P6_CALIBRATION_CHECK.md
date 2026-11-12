# S1 P6 out-of-point court calibration check

The [frozen protocol](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_calibration_review/protocol.json) tests the previously fitted S3 P34 refined transform on unboxed S1 P6 frames 1759 and 1783. The transform hash and a 0.2 m maximum landmark residual rule were frozen before these new clicks. All twelve landmarks must be visible and marked, with no more than 2 px prior static camera-registration shift. The same reviewer has seen earlier tracking and calibration work.

**Frozen operational screen:** passed. 12/12 landmarks marked; median residual 0.0316 m, maximum residual 0.0506 m. The prior camera-registration maximum was 0.293 px.

The passed screen supports this transform as an operational court mapping across these checked source points. It does not validate a true player floor point, repair the final airborne S1 P6 sample, certify all intervening identities, or establish an outcome association. The [machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_calibration_review/score.json) retains the decision and input hashes.

Reproduce with `.\.venv\Scripts\python.exe scripts/score_u5_s1p6_calibration_check.py`.
