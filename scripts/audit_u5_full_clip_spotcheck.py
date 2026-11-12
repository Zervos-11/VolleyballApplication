"""Bind the bounded visual tracklet check to its source-frame sheets."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREENING = BASE / 'screening'
AUDIT = SCREENING / 'full_clip_tracklet_audit.json'
MANIFEST = SCREENING / 'full_clip_run_spotcheck/manifest.json'
QC = SCREENING / 'full_clip_run_spotcheck_qc.json'
OUT = SCREENING / 'full_clip_run_spotcheck_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FULL_CLIP_SPOTCHECK.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    assert manifest['source_sha256'] == audit['source_sha256']
    assert manifest['audit_sha256'] == sha(AUDIT)
    by_manifest = {(r['set'], r['point_number']): r for r in manifest['rows']}
    by_point = {(r['set'], r['point_number']): r for r in audit['points']}
    assert len(by_manifest) == len(qc['rows']) == 2
    checked = []
    for row in qc['rows']:
        key = row['set'], row['point_number']
        image = by_manifest[key]
        run = by_point[key]['longest_same_six_raw_id_run_full_clip']
        assert run['sampled_frames'] == 18
        assert image['frames'] == row['reviewed_source_frames']
        assert sha(BASE / image['image']) == image['image_sha256']
        assert not row['entire_run_identity_certified']
        assert not row['court_floor_path_certified']
        checked.append({**row, 'image': image['image'], 'image_sha256': image['image_sha256'],
                        'raw_run_first_frame': run['first_frame'],
                        'raw_run_last_frame': run['last_frame']})
    assert all(r['observed_identity_issue'].startswith('none_obvious') for r in checked)
    assert 'white_libero_28' in next(r for r in checked if (r['set'], r['point_number']) == (3, 34))['observed_team_membership']
    out = {'status': 'bounded_spotcheck_no_obvious_transfer_not_full_rally_validation',
           'source_sha256': audit['source_sha256'],
           'input_sha256': {'tracklet_audit': sha(AUDIT), 'image_manifest': sha(MANIFEST),
                            'manual_qc': sha(QC)},
           'summary': {'raw_runs_spotchecked': 2, 'displayed_source_frames': 6,
                       'raw_runs_with_no_obvious_transfer_at_displayed_frames': 2,
                       'wrong_team_raw_runs_rejected': 0,
                       'validated_full_rally_six_player_trajectories': 0},
           'rows': checked}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text('''# Full-clip raw-run source spot check

The two longest 18-sample same-six-ID runs were checked on the first, middle and last sampled source frames. These six displayed images are a bounded visual check, not a review of every intervening frame. The [source-linked audit](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck_audit.json) records the reviewed frames, sheet hashes and manual observations.

| Point | Displayed source frames | Observation | Decision |
| --- | --- | --- | --- |
| S1 P5 | 1326, 1380, 1428 | All six boxes appear on the near-side UCLA team at these three frames. | Retain as a raw candidate; exact live phase, intervening identity and court-floor positions remain unchecked. |
| S3 P34 | 36000, 36054, 36102 | Raw ID 8 labels white jersey #28 in all three frames. Close crops show the same player; #28 is the near-side libero. | Retain as a raw candidate; do not certify the uninspected frames or grounded positions. |

The [first sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s1_p05_first_middle_last.png) and [second sheet](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_first_middle_last.png) show the original source frames with the pass's raw-ID boxes. Close crops of ID 8 at [frame 36000](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3p34_id8_f36000.png), [frame 36054](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3p34_id8_f36054.png) and [frame 36102](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3p34_id8_f36102.png) show the same jersey #28. The initial visual classification of white #28 as an opponent was incorrect; #28 is the near-side libero. The [later every-sample review](HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md) checks all 18 five-Hz samples in each run. Neither review validates a full rally or grounded court-coordinate path.

Reproduce the sheets with `python scripts/render_u5_full_clip_run_spotcheck.py` and the audit with `python scripts/audit_u5_full_clip_spotcheck.py`.
''', encoding='utf-8')
    print(out['summary'])


if __name__ == '__main__':
    main()
