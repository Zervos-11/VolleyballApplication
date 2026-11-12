# Week 6 - Dataset and Annotation Framework

Status: framework prepared; annotated pilot and initial main dataset are not yet verified. This document replaces the earlier unsupported claims of a completed pilot and a 500-match main dataset. The quantities below are project planning targets, not counts of completed work or a statistical power calculation.

Implementation update: five **unreviewed rally proposals** from `yt_FqE5pTJqx8g` and a local frame-by-frame boundary review page are now prepared. Follow [PILOT_REVIEW_GUIDE.md](PILOT_REVIEW_GUIDE.md). That first-source development pilot uses the explicitly documented temporal sampling amendment; it is not the exhaustive-register random sampling design below and is not a completed annotated dataset.

## 1. Scope and assessment evidence

The dataset will support detection, within-rally identity tracking and floor-position evaluation for players on one visible half of an indoor volleyball court. The target half must be declared for each camera segment. Required labels are rally boundaries, player identities, visible-body boxes, ground-contact positions, visibility and review provenance. Ball trajectories, action labels, pose keypoints and referee events are optional extensions, not prerequisites for Week 6.

| Deliverable | Prepared evidence | Remaining work |
|---|---|---|
| Final video selection criteria | Section 2 and source manifest template | Screen candidate sources and document permissions |
| Sampling strategy | Section 3; deterministic rally sampler | Register real rallies, assign source groups and freeze the selected sample |
| Annotation protocol | Section 4 | Apply to pilot, resolve ambiguities, record protocol revision |
| Structured dataset schema | DATASET_SCHEMA.md and six CSV templates | Populate and review records |
| Annotated pilot and initial main dataset | Existing files inventoried, not accepted as ground truth | Complete manual labels and independent review |
| Quality-control process | Section 5; stricter QC and generated audit | Measure annotator agreement and resolve findings |
| Ethics, privacy and data management | DATA_MANAGEMENT.md | Complete project-specific decisions and evidence |

## 2. Final video selection criteria for this scope

A main-dataset asset must satisfy all of these criteria:

- Native resolution at least 1280 pixels wide and 720 pixels high; measured frame rate at least 25 fps. Record actual decoder measurements, not download settings or assumed 1080p metadata.
- A documented constant frame rate, or a documented constant-rate derivative with an original-to-derived timestamp mapping. Nominal FPS alone does not verify timing.
- A stable court-wide view of the target half, with the four reference corners identifiable and the target team's six players observable during most of each rally. Boundary excursions and ordinary occlusions remain valid challenge cases.
- Complete rallies, from serve contact through the point-ending action, with enough context to verify the boundaries. Do not count a short clip as a complete rally without checking it.
- No camera cut, replay, major zoom or calibration-changing movement within a selected rally. A new camera segment needs a new calibration. Exclude an unsuitable segment with its reason, not an entire match automatically.
- A recorded source, parent match/source group, permitted-use evidence and completed privacy screening for the intended research and assessment use.

Prefer variation in venue, lighting, camera height and team appearance among accessible eligible matches. Record the coverage actually achieved; do not claim population representativeness or balance in gender/competition level without evidence. A low-resolution source may be retained as `development_only`, with the exception documented; it cannot be silently counted toward main-dataset eligibility. Audio is unnecessary.

## 3. Defined sampling strategy

### Planned size and separation

| Stage | Target | Purpose |
|---|---|---|
| Pilot | 2 independent source matches, 5 rallies each: 10 rallies | Test annotation definitions and workload; development only |
| Initial main dataset for Week 6 | First 10 reviewed rallies from a new eligible match | Demonstrate the frozen protocol beyond the pilot |
| Main dataset target | 3 new independent source matches, 10 rallies each: 30 rallies, including the initial main set | Two development matches and one held-out evaluation match for Week 9 |

These five source matches are a manageable starting target, not five existing folders. If fewer eligible matches are available, report the shortfall and narrow the scope before claiming completion. One held-out match only supports a limited case study, not a generalisation claim across volleyball.

Assign `source_group_id` before selecting clips. Every derivative from the same recording or physical match stays in one split. Freeze the held-out source group before tuning the tracker or changing annotation thresholds. Annotators may label it, but do not use its results to choose configurations. Pilot data never becomes held-out evaluation data.

### Selection procedure

1. Populate `data/dataset_manifest.csv` from its template. Screen candidates against Section 2 and record exclusions, source groups, stage and split.
2. Enumerate all complete rallies in each selected match, not just good tracker outputs. Record frame boundaries, set, rally index, visibility difficulty and eligibility in `data/rally_register.csv`.
3. Assign each eligible rally to a stratum defined before random selection. Default: set number crossed with early/middle/late chronological third within that set. Use at most the per-match sample count in strata; if necessary merge adjacent timeline thirds consistently and record the decision so every stratum has a chance of selection.
4. Run `scripts/sample_rallies.py` with seed `20261009`, selecting 5 per pilot match or 10 per main match. The sampler balances counts across sorted strata, redistributes unused quotas, then samples uniformly without replacement within each stratum. It preserves excluded and unselected rows and records within-stratum inclusion probability n/N. Different sampling fractions require stratum weighting for population estimates; also report unweighted benchmark results separately.
5. Keep routine and difficult selected rallies, and tag them for stratified reporting. Additional hand-picked failure cases belong in a separate challenge appendix and do not enter the randomly sampled headline result.
6. Freeze the candidate register, sampled register, manifest, seed and hashes. Review source-group/split consistency manually; the rally sampler enforces within-match consistency but does not read the manifest.

For every selected rally, label all target players at approximately 1 Hz: use sorted unique frames `start_frame + round(k * fps)` while below `end_frame_exclusive`. Also label the last rally frame. For identity evaluation, label every native frame in one two-second window per source match, beginning at the midpoint frame of its first selected rally; if that window exceeds the rally end, shift it back to end there. If the rally is shorter than two seconds, label it fully and record the exception. Retain the full original frame indices and do not interpolate missing ground truth.

Sparse labels support position checks. Only contiguous dense windows support local ID-switch measurements; they do not establish whole-match tracking reliability. Record annotated frames in `frame_review.csv`, including empty or unobservable frames, so missing labels are detectable during review.

## 4. Completed annotation protocol, version 2

1. **Prepare:** verify the manifest, video properties and exact source asset. Register rally boundaries and assign stable case-sensitive IDs such as `r1`. Annotate on the native video; convert display-scaled clicks back to native pixels.
2. **Mark rally boundaries:** start at the frame of serve contact; end at the first frame after the point-ending action. Use an end-exclusive frame interval. If the action is obscured, record uncertainty and seek adjudication; a whistle alone is not a confirmed point-end label. Reject a truncated rally from the primary sample with its reason. Copy verified times into existing API metadata as frame/FPS.
3. **Assign identity:** assign pseudonyms such as `home_p01`, scoped to the rally unless continuity across rallies is independently established. Use team plus pseudonym, not jersey number alone. Preserve identity through observable occlusions. At a cut, substitution or unresolved ambiguity, record an identity break rather than guessing. Automatic track IDs remain separate from manual player IDs.
4. **Draw player boxes:** tightly enclose the visible body and limbs, excluding shadows, using x1/y1 upper-left and x2/y2 lower-right. For partial occlusion, enclose the visible portion and mark `partial`. For full occlusion, leave the box blank; only retain an identity row when continuity is known. Do not infer hidden body extents.
5. **Mark ground-contact position:** if both feet visibly contact the floor, mark the midpoint of their contact locations; if one foot contacts the floor, use that contact point. Mark `visible` only when that point is directly observable. For hidden feet, airborne players, out-of-frame players or ambiguity, use the corresponding status and leave foot coordinates empty. A visible upper body does not imply a visible floor position. Do not use the torso centre for court mapping.
6. **Handle court coordinates:** annotate pixels first. Use the half-court convention in DATASET_SCHEMA.md and a reviewed calibration for derived metre coordinates. Preserve out-of-court positions. Mapping both prediction and annotation through the same homography evaluates agreement conditional on that calibration; independent court landmarks are needed to assess mapping accuracy.
7. **Record provenance:** use `manual` for fresh human labels or `assisted` for corrected proposals, with annotator code and `unreviewed` status initially. Retain original proposals separately. A model confidence of 0.95 is not evidence that a human checked the label. Leave manual confidence empty.
8. **Review:** a second person checks each selected frame for missing players, IDs, boxes, feet and visibility, using `frame_review.csv`. Record reviewer code and `reviewed` status only after that check. Use `adjudicated` after a recorded disagreement is resolved. Self-review can be useful, but must not be reported as independent review.
9. **Freeze:** run automated QC, resolve issues, measure independent agreement on the subset below, and save a versioned release with reviewer decisions. Never silently correct legacy labels without viewing the source frame.

The original `annotations_pilot.csv` files remain unverified source material. New verified labels should be stored in `annotations_reviewed.csv`. The protocol covers player tracking; optional ball rows do not count toward player annotation totals.

## 5. Quality-control process

### Automated validation

Run `scripts/qc_checks.py` against the actual source video and reviewed CSV. It checks required columns; native video/camera metadata agreement; case-sensitive match and rally references; finite values; frame bounds; timestamp agreement within half a frame; frames inside rally intervals; ordered boxes; coordinate bounds; confidence ranges; duplicate identities; visibility/footpoint consistency; and independent reviewer provenance. It also reports missing or degenerate calibration as a warning. Any error blocks structural acceptance; calibration warnings must be resolved before court-position evaluation.

A structural pass does not check whether a box encloses the correct person, whether players were omitted, whether a camera moved, or whether a claimed reviewer actually reviewed it. These are manual release checks. Full manifest, sidecar and cross-file release validation is also manual in this version.

### Independent annotation and visual review

For the pilot, independently double-annotate at least two rallies, one from each source. For main data, independently double-annotate at least 20% of selected rallies, rounded up, including every source and difficulty category present. The second annotator must work without seeing the first labels or machine proposals on this subset. Compare only after both versions are saved; preserve both originals and adjudicated labels.

The following are provisional project acceptance targets to review during the pilot and freeze before main annotation. They are not measured results:

| Check | Definition | Initial target |
|---|---|---|
| Rally boundary agreement | Absolute difference in frame indices | Within 2 frames for each boundary; resolve larger differences |
| Player box agreement | IoU of corresponding boxes for same manually identified player/frame | Median IoU >= 0.80; review every pair below 0.50; report denominator and unmatched boxes |
| Position agreement | Euclidean native-pixel distance between independently marked visible footpoints | Median <= 0.5% and 95th percentile <= 1% of image diagonal; also report pixels |
| Identity and visibility agreement | Exact agreement on eligible player/frame pairs | At least 95% before adjudication; resolve every known identity conflict |
| Court-reference validity | Independent held-out floor landmarks, not the four fitting corners | At least 4 checkpoints per camera segment; mean error <= 0.25 m and max <= 0.50 m, or exclude metric-distance claims |
| Completeness | Every target player and sampled frame accounted for in review log | 100% reviewed; retain and report unobservable positions |

Compute IoU as intersection area / union area; footpoint distance as sqrt((xa-xb)^2 + (ya-yb)^2). For each statistic report source, rally/frame/player counts, exclusions and pre-adjudication results. Exclude positions marked unobservable by either annotator from position error, but include those cases in visibility agreement and report their count. Unmatched players are a completeness error, not a reason to remove difficult frames. Store measured values and decisions in `qc_review.csv`; calculation of these agreement statistics is not yet automated by the QC script.

Use real decoded frames for review. The old `visualize_samples.py` has been adjusted to skip undecodable/missing source frames rather than generate blank substitutes. Review complete frames, not isolated random rows. Calibration checks must use additional landmarks; a perfect fit to the four clicked corners is not independent evidence of accuracy.

### Release gate

Release only when source selection/privacy records are complete, all selected frames have been reviewed, structural errors are resolved, agreement targets are met or justified by a documented protocol revision, and unresolved cases are excluded with reasons. Report the missing-position rate and the number of independent source matches. A set of CSV headers or automatic tracks is not an annotated pilot.

## 6. Current repository evidence

See CURRENT_DATASET_STATUS.md and the generated files in `data/processed/week6_audit/`. The source metadata and labels have been preserved. The old QC report's zero issues was insufficient evidence: it did not validate FPS, source dimensions, rally references or provenance.

## 7. Ethics and data management

Follow DATA_MANAGEMENT.md and populate the project-specific records. This framework records permission and privacy decisions rather than asserting that current downloaded footage is cleared. No fixed retention period is assumed without the institution's policy.

## 8. Commands and next working session

Run from the repository root using the existing environment:

```powershell
.\.venv\Scripts\python.exe scripts/audit_dataset.py
.\.venv\Scripts\python.exe scripts/sample_rallies.py --register data/pilot_rally_register.csv --out data/pilot_sampled_rallies.csv --per-match 5
.\.venv\Scripts\python.exe scripts/sample_rallies.py --register data/main_rally_register.csv --out data/main_sampled_rallies.csv --per-match 10
.\.venv\Scripts\python.exe scripts/qc_checks.py --match_dir data/matches/M1 --annotations data/matches/M1/annotations_reviewed.csv --out data/processed/qc_reports/M1_reviewed.json
```

The sampling and reviewed-QC commands require real populated inputs; those files have not been fabricated. QC returns exit code 1 when errors are found, even when it successfully writes the report.

Next: screen eligible videos and record rights/source groups; enumerate and sample pilot rallies; label and review the pilot; freeze protocol changes; annotate the first main match; assemble the release counts, QC results and real-frame figures for assessment. Week 9 then evaluates fixed tracking configurations against that held-out ground truth.
