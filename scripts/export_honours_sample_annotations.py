"""Export the completed sparse sample labels without certifying their geometry."""
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
PILOT = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot'
CALIBRATIONS = {1: PILOT / 'calibration/camera_r1.json',
                2: PILOT / 'calibration/camera_r2_r5.json',
                3: PILOT / 'calibration/camera_r2_r5.json'}
OUTPUT = ROOT / 'data/processed/honours_sample_annotations_provisional.csv'
MANIFEST = ROOT / 'data/processed/honours_sample_annotations_export.json'
COLUMNS = ('match_id', 'set', 'point_number', 'winner', 'rally_id', 'frame_index',
           'player_id', 'team_id', 'position_status', 'occlusion', 'bbox_x1_px',
           'bbox_y1_px', 'bbox_x2_px', 'bbox_y2_px', 'foot_x_px', 'foot_y_px',
           'nominal_court_x_m', 'nominal_court_y_m', 'nominal_inside_9m_court',
           'all_players_accounted_for', 'saved_review_status', 'annotator_id',
           'label_sha256', 'calibration_sha256')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    matrices = {}
    for set_number, path in CALIBRATIONS.items():
        c = json.loads(path.read_text(encoding='utf-8'))
        matrices[set_number] = cv2.getPerspectiveTransform(
            np.asarray(c['points_px'], np.float32), np.asarray(c['points_court_m'], np.float32))
    records = []
    for point in audit['points']:
        label_path = ROOT / point['label_file']
        if sha(label_path) != point['label_sha256']:
            raise ValueError(f'Saved labels changed after the audit: {label_path}')
        labels = json.loads(label_path.read_text(encoding='utf-8'))
        for frame_key, frame in sorted(labels['frames'].items(), key=lambda pair: int(pair[0])):
            for player in frame['players']:
                box = player['bbox'] or ['', '', '', '']
                foot = player['footpoint'] or ['', '']
                court = ['', '']
                inside = ''
                if player['footpoint'] is not None:
                    xy = cv2.perspectiveTransform(np.asarray([[player['footpoint']]], np.float32),
                                                  matrices[point['set']])[0, 0]
                    court = [round(float(v), 4) for v in xy]
                    inside = bool(np.isfinite(xy).all() and ((xy >= 0) & (xy <= 9)).all())
                row = dict(zip(COLUMNS, [''] * len(COLUMNS)))
                row.update(match_id='yt_FqE5pTJqx8g', set=point['set'],
                           point_number=point['point_number'], winner=point['winner'],
                           rally_id=point['rally_id'], frame_index=frame_key,
                           player_id=player['player_id'], team_id=player['team_id'],
                           position_status=player['position_status'], occlusion=player['occlusion'],
                           bbox_x1_px=box[0], bbox_y1_px=box[1], bbox_x2_px=box[2], bbox_y2_px=box[3],
                           foot_x_px=foot[0], foot_y_px=foot[1],
                           nominal_court_x_m=court[0], nominal_court_y_m=court[1],
                           nominal_inside_9m_court=inside,
                           all_players_accounted_for=frame['all_players_accounted_for'],
                           saved_review_status=frame.get('review_status', 'unknown'),
                           annotator_id=frame['annotator_id'], label_sha256=point['label_sha256'],
                           calibration_sha256=audit['calibration_sha256'][str(point['set'])])
                records.append(row)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    meta = {'status': 'saved_sparse_annotations_with_provisional_staged_court_projection',
            'source_sha256': audit['source_sha256'], 'audit_sha256': sha(AUDIT),
            'csv_sha256': sha(OUTPUT), 'point_count': len(audit['points']),
            'saved_frame_count': audit['summary']['saved_frames'], 'player_rows': len(records),
            'calibration_sha256': audit['calibration_sha256'],
            'review_status_note': 'The saved_review_status field remains unreviewed because no separate source-validation attestation was recorded; all 61 frames are marked annotator-complete by the user.',
            'metric_use': 'not_validated_for_final_rally_outcome_comparison'}
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print(f'Exported {len(records)} player rows over {meta["saved_frame_count"]} frames')


if __name__ == '__main__':
    export()
