"""Make review-only flags from the experimental pose/tape diagnostic."""

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
ROOT = Path('data/processed/pilot_tracker_evaluation/net_cue_trial')
AUDIT = ROOT / 'pose_tape_audit.json'
OUT = ROOT / 'net_tape_review_flags.json'
SHEET = ROOT / 'net_tape_review_flags.jpg'
MIN_WHITE_FRACTION = .5
MIN_RUN_FRACTION = .3


def main():
    if OUT.exists() or SHEET.exists():
        raise FileExistsError('Review flags already exist')
    audit = json.loads(AUDIT.read_text())
    raw = json.loads((PILOT / 'heldout_tracker_predictions.json').read_text())
    video = cv2.VideoCapture(str(MATCH / 'heldout_source_cfr.mp4'))
    if not video.isOpened():
        raise FileNotFoundError('Source video')
    entries = []
    representatives = {}
    try:
        for window, detail in audit['windows'].items():
            labels = json.loads((PILOT / 'player_annotations' / f'{window}.json').read_text())
            for row in detail['rows']:
                if (row['status'] != 'measured'
                        or row['white_ridge_fraction'] < MIN_WHITE_FRACTION
                        or row['longest_white_run_fraction'] < MIN_RUN_FRACTION):
                    continue
                frame = row['frame']
                if row['source'] == 'labelled_near':
                    person = next(p for p in labels['frames'][str(frame)]['players']
                                  if p['player_id'] == row['player_id'])
                    box = person['bbox']
                    identity = row['player_id']
                else:
                    person = next(p for p in raw['windows'][window]['predictions'][str(frame)]
                                  if p['track_id'] == row['track_id'])
                    box = person['bbox']
                    identity = row['track_id']
                entry = {'window': window, 'frame': frame,
                         'source': row['source'], 'person': identity,
                         'bbox': box,
                         'net_tape_visibility_flag': 'review_candidate',
                         'team_inference': 'withheld',
                         'white_ridge_fraction': row['white_ridge_fraction'],
                         'longest_white_run_fraction': row['longest_white_run_fraction']}
                entries.append(entry)
                key = (window, row['source'], identity)
                if (key not in representatives or
                        entry['white_ridge_fraction'] > representatives[key]['white_ridge_fraction']):
                    representatives[key] = entry
        cells = []
        for entry in representatives.values():
            video.set(cv2.CAP_PROP_POS_FRAMES, entry['frame'])
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f"Cannot decode frame {entry['frame']}")
            x1, y1, x2, y2 = map(int, entry['bbox'])
            left, right = max(0, x1 - 60), min(image.shape[1], x2 + 60)
            top, bottom = max(0, y1 - 60), min(image.shape[0], y2 + 60)
            crop = image[top:bottom, left:right].copy()
            cv2.rectangle(crop, (x1-left, y1-top), (x2-left, y2-top), (0, 255, 255), 2)
            tape_y = 618 - top
            if 0 <= tape_y < crop.shape[0]:
                cv2.line(crop, (0, tape_y), (crop.shape[1]-1, tape_y), (0, 0, 255), 1)
            crop = cv2.resize(crop, (400, 400))
            label = f"{entry['window']} {entry['frame']} {entry['source']} {entry['person']}"
            cv2.putText(crop, label, (6, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (0, 0, 0), 4)
            cv2.putText(crop, label, (6, 28), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (255, 255, 255), 2)
            cells.append(crop)
    finally:
        video.release()
    if cells:
        blank = np.zeros_like(cells[0])
        sheet = np.vstack([np.hstack((cells[i:i+2] + [blank]*2)[:2])
                           for i in range(0, len(cells), 2)])
        cv2.imwrite(str(SHEET), sheet)
    result = {
        'source_sha256': audit['source_sha256'],
        'pose_audit_sha256': hashlib.sha256(AUDIT.read_bytes()).hexdigest(),
        'thresholds_selected_after_reviewing_near_labels': True,
        'flag_semantics': ('Review candidate only. A bright ridge is not a far-side '
                           'team label; known near-side boxes can satisfy this rule.'),
        'min_white_fraction': MIN_WHITE_FRACTION,
        'min_run_fraction': MIN_RUN_FRACTION,
        'flagged_boxes': len(entries),
        'known_near_flagged': sum(e['source'] == 'labelled_near' for e in entries),
        'far_geometry_proxy_flagged': sum(e['source'] == 'far_geometry_proxy' for e in entries),
        'review_sheet': str(SHEET), 'entries': entries,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['flagged_boxes'], result['known_near_flagged'],
          result['far_geometry_proxy_flagged'])


if __name__ == '__main__':
    main()
