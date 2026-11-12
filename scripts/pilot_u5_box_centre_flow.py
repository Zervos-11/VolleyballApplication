"""Pilot short optical-flow box translation from source-reviewed snapshots.

Tracks torso features in image pixels only. Detector agreement is a pipeline
diagnostic, not independent manual ground truth or court-coordinate accuracy.
"""

import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
BASE = MATCH / 'screening'
FILES = {
    'snapshot': BASE / 'image_plane_snapshot_screen.json',
    'original': BASE / 'selected_floor_qc/index.json',
    'highres': BASE / 'zero_run_high_res_detection/index.json',
    'highres_qc': BASE / 'zero_run_high_res_source_qc.json',
    'tracks': BASE / 'dense_live_track_screen.json',
}
VIDEO = MATCH / 'source_720p.mp4'
OUT = BASE / 'box_centre_flow_pilot.json'
SHEETS = BASE / 'box_centre_flow_pilot'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_BOX_CENTRE_FLOW_PILOT.md'
DELTAS = (-12, -6, 0, 6, 12)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_frames(cap, centre):
    cap.set(cv2.CAP_PROP_POS_FRAMES, centre - 12)
    result = {}
    for frame_no in range(centre - 12, centre + 13):
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f'Cannot decode source frame {frame_no}')
        result[frame_no] = frame
    return result


def initial_features(gray, bbox):
    x1, y1, x2, y2 = bbox
    width, height = x2-x1, y2-y1
    left = max(0, int(x1 + .2*width))
    right = min(gray.shape[1], int(x2 - .2*width))
    top = max(0, int(y1 + .18*height))
    bottom = min(gray.shape[0], int(y1 + .72*height))
    mask = np.zeros_like(gray)
    if right <= left or bottom <= top:
        return None
    mask[top:bottom, left:right] = 255
    return cv2.goodFeaturesToTrack(gray, maxCorners=70, qualityLevel=.01,
                                   minDistance=3, mask=mask, blockSize=3)


def track_direction(grays, centre, bbox, direction):
    seed = initial_features(grays[centre], bbox)
    if seed is None or len(seed) < 4:
        return {}, 0
    origin = seed.reshape(-1, 2)
    current = seed
    previous_gray = grays[centre]
    positions = {}
    for step in range(1, 13):
        frame_no = centre + direction*step
        next_points, status, error = cv2.calcOpticalFlowPyrLK(
            previous_gray, grays[frame_no], current, None,
            winSize=(21, 21), maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, .01))
        if next_points is None:
            break
        keep = (status.reshape(-1) == 1) & (error.reshape(-1) < 35)
        origin = origin[keep]
        current = next_points[keep].reshape(-1, 1, 2)
        if len(current) < 4:
            break
        offsets = current.reshape(-1, 2) - origin
        median = np.median(offsets, axis=0)
        distances = np.linalg.norm(offsets-median, axis=1)
        spread = float(np.median(distances))
        consensus = distances <= max(4.0, 3*spread)
        count = int(np.sum(consensus))
        if count < 4:
            break
        displacement = np.median(offsets[consensus], axis=0)
        positions[frame_no] = {'dx': round(float(displacement[0]), 2),
                               'dy': round(float(displacement[1]), 2),
                               'feature_count': count,
                               'feature_spread_px': round(spread, 2)}
        previous_gray = grays[frame_no]
    return positions, len(seed)


def review_image(frame, entries, frame_no, label):
    canvas = frame.copy()
    for i, row in enumerate(entries):
        candidate = row['frames'].get(str(frame_no))
        if candidate is None:
            continue
        dx, dy = candidate['translation_px']
        x1, y1, x2, y2 = [int(round(v)) for v in row['anchor_bbox_px']]
        box = (int(x1+dx), int(y1+dy), int(x2+dx), int(y2+dy))
        color = (0, 220, 0) if candidate['feature_count'] >= 6 else (0, 170, 255)
        cv2.rectangle(canvas, box[:2], box[2:], color, 2)
        cv2.putText(canvas, str(row['anchor_player_key']),
                    (box[0], max(18, box[1]-3)), cv2.FONT_HERSHEY_SIMPLEX,
                    .5, color, 1, cv2.LINE_AA)
    canvas = cv2.resize(canvas, (640, 360), interpolation=cv2.INTER_AREA)
    header = np.full((28, 640, 3), 255, np.uint8)
    cv2.putText(header, f'{label} f{frame_no}', (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack((header, canvas))


def main():
    data = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in FILES.items()}
    source = data['snapshot']['source_sha256']
    with VIDEO.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == source
    assert all(d['source_sha256'] == source for d in data.values())
    assert data['snapshot']['input_sha256']['local_boxes'] == sha(FILES['original'])
    assert data['snapshot']['input_sha256']['highres_boxes'] == sha(FILES['highres'])
    assert data['highres_qc']['detection_index_sha256'] == sha(FILES['highres'])
    original = {(r['set'], r['point_number']): r for r in data['original']['entries']}
    highres = {(r['set'], r['point_number']): r for r in data['highres']['entries']}
    high_qc = {(r['set'], r['point_number']): r for r in data['highres_qc']['rows']}
    dense = {(p['set'], p['point_number']): {r['source_frame']: r['proposals']
                                           for r in p['rows']} for p in data['tracks']['points']}
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    SHEETS.mkdir(parents=True, exist_ok=True)
    rows = []
    for snapshot in data['snapshot']['rows']:
        key = snapshot['set'], snapshot['point_number']
        centre = snapshot['source_frame']
        if snapshot['detector_pass'] == 'original':
            boxes = [(b['raw_track_id'], b['bbox_px']) for b in original[key]['boxes']]
        else:
            qc = high_qc[key]
            source_row = next(r for r in highres[key]['rows'] if r['source_frame'] == centre)
            proposals = source_row['broad_person_proposals']
            boxes = [(f'proposal_{i}', proposals[i]['bbox_px'])
                     for i in qc['accepted_near_team_proposal_indices']]
        assert len(boxes) == 6
        images = source_frames(cap, centre)
        grays = {f: cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) for f, image in images.items()}
        players = []
        agreements = []
        for player_key, bbox in boxes:
            paths = {}
            seeds = []
            for direction in (-1, 1):
                results, seed_count = track_direction(grays, centre, bbox, direction)
                paths.update(results)
                seeds.append(seed_count)
            anchor_center = [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2]
            frames = {str(centre): {'translation_px': [0, 0],
                                    'predicted_box_centre_px': [round(v, 2) for v in anchor_center],
                                    'feature_count': max(seeds), 'feature_spread_px': 0}}
            for delta in DELTAS:
                target = centre + delta
                if delta == 0 or target not in paths:
                    continue
                p = paths[target]
                frames[str(target)] = {'translation_px': [p['dx'], p['dy']],
                                       'predicted_box_centre_px': [round(anchor_center[0]+p['dx'], 2),
                                                                   round(anchor_center[1]+p['dy'], 2)],
                                       'feature_count': p['feature_count'],
                                       'feature_spread_px': p['feature_spread_px']}
                if snapshot['detector_pass'] == 'original':
                    matching = [proposal for proposal in dense[key].get(target, [])
                                if proposal['raw_track_id'] == player_key
                                and proposal['net_side_status'] == 'near_floor_side_candidate']
                    if len(matching) == 1:
                        x1, y1, x2, y2 = matching[0]['bbox_px']
                        detector_centre = [(x1+x2)/2, (y1+y2)/2]
                        error = math.dist(frames[str(target)]['predicted_box_centre_px'], detector_centre)
                        agreements.append(error)
                        frames[str(target)]['same_raw_id_detector_disagreement_px'] = round(error, 2)
            players.append({'anchor_player_key': player_key, 'anchor_bbox_px': bbox,
                            'seed_features': max(seeds), 'frames': frames})
        coverage = {str(centre+d): sum(str(centre+d) in p['frames'] for p in players)
                    for d in DELTAS}
        label = f"S{key[0]} P{key[1]} {'WIN' if snapshot['near_team_won'] else 'LOSS'}"
        sheet = np.hstack([review_image(images[centre+d], players, centre+d, label)
                           for d in (-12, 0, 12)])
        sheet_name = f's{key[0]}_p{key[1]:02d}.jpg'
        path = SHEETS / sheet_name
        assert cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': snapshot['near_team_won'], 'phase': snapshot['source_phase_status'],
                     'anchor_frame': centre, 'detector_pass': snapshot['detector_pass'],
                     'tracked_player_count_by_sample': coverage,
                     'all_six_tracked_at_all_five_samples': all(v == 6 for v in coverage.values()),
                     'same_raw_id_detector_comparisons': len(agreements),
                     'median_same_raw_id_detector_disagreement_px': (
                         round(statistics.median(agreements), 2) if agreements else None),
                     'players': players, 'review_sheet': sheet_name, 'review_sheet_sha256': sha(path)})
    cap.release()
    assert len(rows) == 17
    all_errors = [frame['same_raw_id_detector_disagreement_px']
                  for row in rows for player in row['players'] for frame in player['frames'].values()
                  if 'same_raw_id_detector_disagreement_px' in frame]
    summary = {'reviewed_anchor_snapshots': 17,
               'five_sample_windows_with_six_flow_candidates': sum(r['all_six_tracked_at_all_five_samples']
                                                                    for r in rows),
               'same_raw_id_detector_comparisons': len(all_errors),
               'median_same_raw_id_detector_disagreement_px': round(statistics.median(all_errors), 2)
               if all_errors else None,
               'validated_player_identities': 0, 'validated_court_trajectory_windows': 0}
    output = {'status': 'optical_flow_translation_pilot_not_manual_tracking_validation',
              'source_sha256': source, 'input_sha256': {**{k: sha(v) for k, v in FILES.items()},
                                                       'video': source},
              'settings': {'sample_offsets_frames': DELTAS, 'source_fps': 30,
                           'feature_region': 'middle 60 percent width, 18-72 percent height of reviewed box',
                           'flow': 'pyramidal Lucas-Kanade through each source frame; median feature translation'},
              'summary': summary, 'rows': rows,
              'interpretation': ('The reviewed source box initializes each player. Flow creates short '
                                 'image-plane candidates, including airborne people. Agreement with '
                                 'the same detector raw ID is not independent ground truth; no named '
                                 'identity, phase continuity or floor position is certified by this pilot.')}
    OUT.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
