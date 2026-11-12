# S3 P34 refined court calibration candidate

The [frozen source-only review](HONOURS_U5_S3P34_CALIBRATION_REVIEW.md) marked 12/12 court-line intersections. Its predeclared operational screen **did not pass** for the original staged transform: one near-baseline/right-sideline mark missed the 0.200 m limit by 0.0037 m (maximum 0.2037 m). The two clicks on that landmark are only 0.58 px apart, while the second-frame residual is 0.1969 m. This tiny threshold crossing may reflect manual line-centre selection or the original manually chosen transform corners; the observations do not separate those causes. The original screen result is preserved.

A new candidate homography fits the four baseline and net-floor corners on source frame 36073. The other 8 marks were not used to fit this candidate. The largest held-out residual is **0.0364 m**, and the largest held-out attack-line residual is **0.0364 m**. The [machine-readable candidate](../data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/refined_candidate.json) stores the matrix, every residual and the source hashes.

At the 180 clicked shoe points in the completed 30-fps ground review, changing from the staged to this candidate mapping shifts a mapped coordinate by a median **0.0797 m** and a maximum **0.1424 m**. Those are changes between transforms, not position errors against true floor locations.

The net-floor line in these images is near source row 313, below the suspended net. A bright horizontal feature near row 200 is part of the net structure above the floor. The saved net-line clicks therefore follow the plausible floor feature. The four lines also retain similar geometry across the two reviewed frames.

**Status:** exploratory calibration refinement only. The reviewer had seen an earlier calibration, the two frames are close in one point, and this fit was made after the original screen result was known. Neither transform is approved for final strict metre-valued metrics by this analysis. The fixed-window and full-rally gates remain open.

Reproduce with `.\.venv\Scripts\python.exe scripts/analyze_u5_s3p34_refined_calibration_candidate.py`.
