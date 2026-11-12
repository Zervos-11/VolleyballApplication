# Dataset schema v2: annotation sidecars

This schema extends the existing API's `metadata.json` v1 with separate CSV files. It does not change the API or make existing pilot CSVs reviewed ground truth. Templates in `annotations/` contain headers only; they are not completed datasets.

## Layout and ownership

```text
annotations/                         blank templates
data/dataset_manifest.csv            screened video/source register (to populate)
data/rally_register.csv              all screened candidate rallies (to populate)
data/sampled_rallies.csv              reproducible selection output
data/matches/<match_id>/
  <original filename>.mp4            preserve original source
  metadata.json                      existing API metadata, v1
  homography.json                    existing calibration
  annotations_pilot.csv              legacy, unverified; preserve as received
  annotations_reviewed.csv           new manual/assisted labels (to populate)
  frame_review.csv                   frame completeness record
  calibration_review.csv             independent reference landmarks
  tracks_centroids.csv               machine predictions, never ground truth
data/processed/week6_audit/           generated inventory and QC findings
data/releases/week6_v1/              approved manifest, labels and QC evidence
```

Source videos and identifiable material stay in restricted project storage; the layout alone does not enforce access controls. Do not copy videos into release folders by default.

## Existing API metadata

The actual fields are `schema_version`, `match_id`, `set_number`, `camera: {fps,width,height,mount}`, `rallies`, `teams`, and optional `homography`. A rally has `rally_id`, `t_start`, `t_end`, `context`, and optional `outcome`. Times use seconds from the start of the local video. IDs are case-sensitive (`r1` differs from `R1`). Do not substitute the earlier document's top-level `fps` or `resolution` fields.

Correct camera metadata only after measuring the selected source video and recording the change. If frames are remuxed, cropped, scaled or resampled, create a new asset record and preserve the relationship to the original. A constant-rate file uses `time_s = frame_index / fps`; variable-rate material needs a per-frame timestamp map or a documented constant-rate derivative before this framework's QC can be used.

## Dataset manifest

One row per video asset / `match_id`. The unique physical match or parent recording is `source_group_id`; all clips from that group must share a split. Distinct files are not necessarily distinct matches.

| Fields | Definition / allowed values |
|---|---|
| `match_id, source_group_id` | Nonempty pseudonymous identifiers; match_id equals folder name |
| `source_url, video_file, sha256` | Provenance, relative asset path, full-file SHA-256 |
| `competition_level, venue_code, camera_view` | Verified descriptive fields; use `unknown` if unavailable |
| `rights_status` | `pending`, `documented`, `excluded`; documented requires an evidence reference |
| `permission_evidence` | Restricted record reference for permission/licence and permitted uses |
| `privacy_review_status` | `pending`, `complete`, `excluded` |
| `selection_status, exclusion_reason` | `pending`, `eligible`, `excluded`, `development_only`; reason required for last two |
| `dataset_stage, split` | `pilot` or `main`; `development` or `evaluation`; pilot is development only |
| `width,height,fps,frame_count` | Positive measured values; all except fps are integers |
| `frame_rate_verified` | `true`/`false`; nominal decoder FPS alone is not verification |
| `screened_by, screened_at` | Annotator code and ISO 8601 timestamp |

The generated inventory is an audit, not a populated permission/selection manifest. A source hint inferred from a filename is not verified provenance.

## Rally register

Unique key `(match_id,rally_id)`. `set_number` and `rally_index` are positive integers verified from the source. `start_frame` is inclusive; `end_frame_exclusive` is exclusive, and `0 <= start_frame < end_frame_exclusive <= frame_count`. Synchronise API times to these bounds divided by verified FPS. Keep any inference padding separate from label boundaries.

`eligible` and `selected` are `true`/`false`; `difficulty` is `routine`, `occlusion`, `boundary`, or `other` with details in notes. `stratum` is the sampling bucket (for example `set1_early`). `selection_probability` is n/N within that bucket, not an annotation confidence. The sampler fills `selected`, `sample_seed`, and `selection_probability`; retain unselected and excluded records for an audit trail. `dataset_stage` and `split` must agree with the source-group assignment in the manifest. Review fields record boundary verification.

## Player annotations

One row per object per labelled frame. Required columns are in [the template](../annotations/player_annotations_template.csv). CSV missing values are empty cells, never zero, `NaN`, a guessed position or a copied prediction.

| Fields | Definition / allowed values |
|---|---|
| `match_id,rally_id,frame_index,time_s` | Exact registered IDs, zero-based integer frame index, seconds from local video start |
| `object_type` | `player`; `ball` is optional and excluded from required player QC statistics |
| `id_type,id` | Use `player_id` and a stable pseudonym for manual player ground truth; `track_id` denotes a machine track |
| `x1,y1,x2,y2` | Visible-body box in native pixels, upper-left to lower-right; empty only for full occlusion |
| `confidence` | Optional detector confidence in [0,1]; leave empty for fully manual labels; not review quality |
| `occlusion` | `none`, `partial`, `full` |
| `team_id` | `home`, `away`, `unknown`; use one consistent target team/half per camera segment |
| `foot_x_px,foot_y_px` | Ground-contact reference point in native pixels; empty when unobservable |
| `position_status` | `visible`, `occluded`, `airborne`, `out_of_frame`, `uncertain` |
| `annotation_source` | `manual`, `assisted`, `automatic`, `example`; only the first two can become ground truth |
| `annotator_id,reviewer_id` | Distinct pseudonymous contributor codes for independent review |
| `review_status` | `unreviewed`, `reviewed`, `adjudicated`, `rejected` |
| `notes` | Reason for ambiguity, corrections and identity breaks |

Physical frame uniqueness is `(match_id,frame_index,object_type,id_type,id)`; a player cannot duplicate across overlapping rally labels. The footpoint lies in `[0,width) x [0,height)`; box right/bottom edges may equal width/height. All coordinates must be finite. Ground-truth identities are scoped to a match/rally; do not assume identity across a cut or substitution without evidence.

## Court reference and review records

`homography.json` stores four ordered `points_px`, four corresponding `points_court_m`, and `image_size: [width,height]` for the clicked reference image. The existing pipeline rescales reference pixels to native video size. Four points define a projective 3x3 mapping; they do not establish its accuracy.

For this Week 6 scope use the target half court: x=0..9 m across its width, y=0..9 m from its baseline toward the net. Label corner correspondences by physical location. Record which team occupies the half and each camera segment. Existing full-court code also has a different 18-by-9 convention; do not mix that output into this dataset without a documented coordinate conversion. Keep legitimate positions beyond the boundary; never clip them to make errors smaller.

`calibration_review.csv` records reference landmarks with known court coordinates. `used_for_fit=false` identifies held-out landmarks for validation, with Euclidean error in metres. `frame_review.csv` records counts and `all_players_labelled=true/false`, including reviewed empty frames. These records are essential: row validation cannot find a player that was never labelled. `qc_review.csv` records each agreement check, value, unit, threshold, result and adjudication. These sidecars require human review; the current QC script does not validate their entire contents.

## Release invariants

Before release, check manifest/rally/annotation foreign keys, no shared source group across splits, all selected frames accounted for, distinct reviewer identity, no unresolved issues, permission/privacy records complete, and calibration reviewed. Record file hashes and dataset version. Do not call a structural QC pass a dataset release approval.
