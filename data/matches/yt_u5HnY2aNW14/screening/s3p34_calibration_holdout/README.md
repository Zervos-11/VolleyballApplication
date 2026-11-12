# Out-of-point court-line holdout

The [click review](http://127.0.0.1:8055/) shows two unboxed source frames from other selected points: set one point five at frame 1422 and set three point thirteen at frame 29952. These frames were frozen before any new marks and were not used to fit the refined S3 P34 transform. Click six painted court intersections in each frame; use **Uncertain** or **Occluded** with a null point when the intersection cannot be read. Save both frames and export.

The [protocol](protocol.json) fixes the landmarks, source hashes and operational screen before marking: all twelve marks present, maximum mapped court-line error at most 0.2 m, and existing static camera shift at most 2 px. The [scorer](../../../../../scripts/score_u5_s3p34_calibration_holdout.py) compares the frozen marks to the previously refined transform. A pass would support this fixed-camera court mapping for descriptive metric use under a single-reviewer operational rule. It would not prove shoe or box-bottom positions or independent observer accuracy.

**One-frame diagnostic, 8 November 2026:** the student saved all six marks for frame 1422 and chose to stop there because the camera appears fixed. The [partial score](../../../../../DELIVERABLES/HONOURS_U5_S3P34_ONE_FRAME_CALIBRATION_DIAGNOSTIC.md) has a 0.0261 m median and 0.0397 m maximum mapped line residual. Frame 29952 is unmarked, so the frozen two-frame operational rule remains incomplete. This partial check can be reported with that qualification; do not export a fabricated second frame.

To restart the local page from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.s3p34_calibration_holdout:app --host 127.0.0.1 --port 8055
```
