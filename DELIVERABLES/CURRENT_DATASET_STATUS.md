# Week 6 evidence audit - 9 October 2026

**Subsequent source import:** a new 1080p50 full-match candidate, `yt_FqE5pTJqx8g`, was downloaded after the six-folder audit below. See its [screening record](../data/matches/yt_FqE5pTJqx8g/SCREENING.md) and [contact sheet](../data/matches/yt_FqE5pTJqx8g/screening/contact_sheet.jpg). It is registered as a pending pilot/development source in `data/dataset_manifest.csv`; annotation has not started. There are now seven match folders and five downloaded video files. The historical counts below describe the six legacy folders at the time of their audit; rerunning the inventory will also include this new unannotated candidate.

The framework and tools are prepared. The existing files do **not** establish a completed, reliable annotated pilot or initial main dataset. Do not submit the old pilot-completion statement or the previous zero-issue QC result as evidence of accuracy.

## Measured inventory

Measurements come from decoding local MP4 metadata with OpenCV. These are video properties, not verified source permissions or independent match counts.

| Folder | Actual video | Existing label rows | Finding |
|---|---|---:|---|
| M1 | 640 x 360, 29.97 fps, 196,370 frames | 6 | Below main selection resolution; metadata declares 1920 x 1080 at 30 fps |
| provolley | No MP4 | 4 | No source video or metadata to validate labels |
| uts_demo | No MP4 | 4 | No source video or metadata to validate labels |
| yt_ref_1 | 1280 x 592, 60 fps, 662 frames | 4 | Below minimum height; missing metadata; likely same parent source as yt_ref_audio1 |
| yt_ref_audio1 | 1920 x 888, 60 fps, 662 frames | 4 | Metadata declares 1920 x 1080 at 30 fps; source-group check needed |
| yt_ref_clip1 | 1920 x 1080, 30 fps, 450 frames | 4 | Basic resolution/FPS pass; annotations use different match/rally IDs and inconsistent times |

Totals: **6 folders, 4 readable video files, 26 annotation rows, 0 rows with recorded independent-review provenance, and 0 folders passing the new structural QC.** The 26 rows include ball labels; they are not 26 rallies or 26 fully labelled frames. The two `rBgLLAwDU8M` filenames indicate a possible shared source, not proof of separate matches. Only two video files pass the new basic resolution/FPS rules; complete-rally, camera, privacy and source-use screening remain pending.

The audit does not prove nobody previously reviewed the data. It shows that the review evidence required for a research dataset is absent from these records.

## Specific M1 problems

- `metadata.json` contains only rally `r1`, from 0 to 10.5 seconds. Labels reference `R1` and `R2`; neither is the same case-sensitive ID.
- Frame 100 is approximately 3.337 seconds at measured 29.97 fps, not the label's 4.00 seconds. All six existing rows fail the half-frame timestamp tolerance.
- Camera width, height and FPS disagree with the actual asset. Do not rescale or rewrite labels blindly: verify the source frame and coordinate convention first.
- Labels have no human provenance, review status, team or footpoint fields. The file contains six rows across five frames, not the previously claimed 20 annotated rallies.
- The half-court calibration is structurally valid, but that does not verify its physical accuracy or corner identities.
- `processing_diagnostics.json` reports processing frames 0..599, around 20 seconds of a much longer video. Its `total_tracks: 7052` is a count of stored observations in this pipeline, not 7,052 distinct players or manually checked labels.

## Visual spot checks

Eight deterministic real-frame review images were generated across the four readable videos. No substitute images were generated for missing footage. Two images were inspected during this audit:

- [M1 frame 100](../data/processed/week6_audit/review_images/M1/M1_f100.png): the large `tk_1` box sits around the referee/stand area rather than a target on-court player.
- [yt_ref_clip1 frame 180](../data/processed/week6_audit/review_images/yt_ref_clip1/yt_ref_clip1_f180.png): the existing player and ball boxes sit on the upper wall, while the visible players and ball are elsewhere.

These examples demonstrate real label misalignment in the inspected rows. They are not a quantitative accuracy estimate for every file. The review images are marked as unverified copies and are diagnostic evidence, not corrected annotations. Previously generated images under `data/processed/visualizations/` are preserved and should not be treated as reviewed evidence.

## Generated evidence and reproducibility

- [Dataset inventory](../data/processed/week6_audit/dataset_inventory.csv)
- [Audit summary](../data/processed/week6_audit/dataset_audit.json)
- [M1 detailed QC](../data/processed/week6_audit/M1_qc_report.json), with a separate detailed report for every other folder in that directory
- [Schema and templates](DATASET_SCHEMA.md)
- [Protocol, sampling plan and acceptance criteria](WEEK6_DATASET_AND_ANNOTATION.md)
- [Ethics and data-management procedure](DATA_MANAGEMENT.md)

Reproduce from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/audit_dataset.py
.\.venv\Scripts\python.exe scripts/visualize_samples.py --matches M1 provolley uts_demo yt_ref_1 yt_ref_audio1 yt_ref_clip1 --n 2 --out data/processed/week6_audit/review_images
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Thirteen tests passed for the new validation/sampling behavior, covering valid structure, measured dimensions, timing and rally mismatches, frame limits, non-finite values, duplicate identity, reviewer independence, occlusion, empty/missing data, sampling reproducibility, exclusions and within-match split leakage. These software tests are not tests of tracking accuracy.

## Work required for Week 6 completion

1. Confirm source-use records and screen suitable complete matches. Obtain an eligible higher-resolution source for M1 if it is intended for the main dataset; retain this copy for development otherwise.
2. Populate the manifest and screened rally register, group derivatives by source, and run the reproducible pilot sampler.
3. Annotate the planned ten pilot rallies from two independent sources, including position visibility and contiguous identity-check windows. Record all sampled frames and independent reviewer decisions.
4. Measure agreement and adjudicate the pilot; revise and freeze the protocol before main annotation.
5. Annotate and review the first ten main rallies from a new eligible source, then rerun QC and assemble the versioned release with real counts and exclusions.

Source videos, original labels, metadata, calibration and tracking outputs were preserved by this work. No manually reviewed labels, source permissions or completed dataset counts were invented.
