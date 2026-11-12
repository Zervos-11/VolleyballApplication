# Automatic score reading for ProVolley vs UTS

The [reader](../scripts/auto_fqe_score_reader.py) processes the fixed broadcast score graphic in the primary ProVolley vs UTS video. It reads two score patches from each sampled video frame, compares their digit pixels with a saved template bank, marks frames without a reliable graphic as unknown, and turns consecutive visible +1 score changes into point winners. It removes the temporary 19–11 to 19–10 broadcast correction. The opening 1–0 point is based on the first visible score, and the set-one 25–15 winner is inferred from the transition to the next set because that final score is not displayed.

The [automatic point register](../data/processed/fqe_auto_score_timeline.csv) and [JSON record](../data/processed/fqe_auto_score_timeline.json) contain **123 points across three sets**: 25–15, 25–16, and 25–17. They are generated from the saved [template bank](../data/processed/fqe_auto_score_templates.npz) and video pixels. After the one-time calibration, the normal command does **not** read the manually reviewed score states:

```powershell
.\.venv\Scripts\python.exe scripts/auto_fqe_score_reader.py
```

Calibration used one reviewed sample for each of 26 top-team and 18 bottom-team displayed score values. The fixed crop coordinates and templates are specific to this broadcast layout. The [audit record](../data/processed/fqe_auto_score_readings.json) reports **721/721** agreement with the existing reviewed sampled states, the same 123-point winner sequence, and **121/121** agreement on additional frames 25 frames after previously located score flips. The additional frames were not template examples, but their expected scores and flip locations came from the reviewed same-match timeline. These are **same-video agreement checks**, not independent accuracy on another broadcast. Run the audit with:

```powershell
.\.venv\Scripts\python.exe scripts/auto_fqe_score_reader.py --audit --check-flips
```

The reader makes score progression automatic for the primary match; it does not determine exact serve or rally-end frames. If the graphic is absent or a new layout differs from the calibrated template bank, the result needs a new calibration or a stated inference. The original manually reviewed timeline remains a reference and is not silently overwritten.
