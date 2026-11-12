"""Build a provisional image-space Sam path with visibly marked short gaps."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
RAW = DIR / 'raw_74880_75540.json'
SAVED = MATCH / 'pilot/player_annotations/point_21m.json'
VIDEO = MATCH / 'source_AoEP-YiWRvc.mp4'
FIRST, LAST = 75198, 75229
RAW_ID, PLAYER_ID = 517, 'Sam'
MAX_INTERPOLATED_FRAMES = 8


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def centre(box):
    return [round((box[0] + box[2]) / 2, 3), round((box[1] + box[3]) / 2, 3)]


def build_path(predictions, saved_frames, first, last, raw_id, player_id,
               maximum_interpolated_frames=8):
    rows = {}
    blocked = set()
    for frame in range(first, last + 1):
        key = str(frame)
        saved = [p for p in saved_frames.get(key, {}).get('players', [])
                 if p['player_id'] == player_id]
        if len(saved) > 1:
            raise ValueError(f'Duplicate saved player at {frame}')
        if saved and saved[0]['bbox'] is None:
            blocked.add(frame)
            rows[key] = {'status': 'saved_no_box', 'image_point_px': None,
                         'court_position_m': None}
            continue
        if saved:
            rows[key] = {'status': 'saved_assisted_box_centre',
                         'image_point_px': centre(saved[0]['bbox']),
                         'court_position_m': None}
            continue
        raw = [p for p in predictions[key] if p['track_id'] == raw_id]
        if len(raw) > 1:
            raise ValueError(f'Duplicate raw ID at {frame}')
        rows[key] = {'status': 'raw_box_centre_unverified' if raw else 'unresolved_gap',
                     'image_point_px': centre(raw[0]['bbox']) if raw else None,
                     'court_position_m': None}
    anchors = [frame for frame in range(first, last + 1)
               if rows[str(frame)]['image_point_px'] is not None]
    for left, right in zip(anchors, anchors[1:]):
        missing = right - left - 1
        if not 1 <= missing <= maximum_interpolated_frames:
            continue
        if any(frame in blocked for frame in range(left + 1, right)):
            continue
        start, end = rows[str(left)]['image_point_px'], rows[str(right)]['image_point_px']
        for frame in range(left + 1, right):
            weight = (frame - left) / (right - left)
            rows[str(frame)] = {
                'status': 'interpolated_image_centre_not_observed',
                'image_point_px': [round((1 - weight) * start[i] + weight * end[i], 3)
                                   for i in range(2)],
                'court_position_m': None,
                'between_observed_frames': [left, right],
            }
    return rows


def render(video_path, rows, out):
    cap = cv2.VideoCapture(str(video_path))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 75222)
        ok, image = cap.read()
        if not ok:
            raise RuntimeError('Cannot decode source frame 75222')
    finally:
        cap.release()
    colors = {'raw_box_centre_unverified': (90, 205, 90),
              'saved_assisted_box_centre': (255, 200, 50),
              'interpolated_image_centre_not_observed': (30, 150, 255)}
    previous = None
    for frame, row in rows.items():
        point = row['image_point_px']
        if point is None:
            previous = None
            continue
        p = tuple(round(v) for v in point)
        if previous is not None:
            cv2.line(image, previous, p, (230, 230, 230), 2)
        cv2.circle(image, p, 5, colors[row['status']], -1)
        if int(frame) in (75198, 75218, 75227, 75229):
            cv2.putText(image, frame, (p[0] - 12, p[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, .42, (0, 0, 0), 3)
            cv2.putText(image, frame, (p[0] - 12, p[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, .42, (255, 255, 255), 1)
        previous = p
    cv2.rectangle(image, (5, 5), (690, 78), (12, 18, 30), -1)
    cv2.putText(image, 'Sam provisional image path (bbox centres, no floor metres)',
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, .58, (255, 255, 255), 2)
    cv2.putText(image, 'green=raw   blue=saved assisted   orange=interpolated',
                (15, 59), cv2.FONT_HERSHEY_SIMPLEX, .53, (255, 255, 255), 1)
    if not cv2.imwrite(str(out), image):
        raise RuntimeError(f'Could not write {out}')


def main():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    saved = json.loads(SAVED.read_text(encoding='utf-8'))
    source_hash = sha256(VIDEO)
    if raw['source_sha256'] != source_hash:
        raise ValueError('Source and raw tracker mismatch')
    rows = build_path(raw['predictions'], saved['frames'], FIRST, LAST, RAW_ID, PLAYER_ID,
                      MAX_INTERPOLATED_FRAMES)
    saved_hash = sha256(SAVED)
    stem = f'sam_image_path_{FIRST}_{LAST}_{saved_hash[:10]}'
    output = DIR / f'{stem}.json'
    image = DIR / f'{stem}.jpg'
    payload = {
        'status': 'provisional_image_path_not_trajectory_accuracy',
        'source_sha256': source_hash, 'raw_sha256': sha256(RAW),
        'saved_annotations_sha256': saved_hash,
        'frame_range_inclusive': [FIRST, LAST],
        'visual_player_id_from_user': PLAYER_ID, 'candidate_raw_track_id': RAW_ID,
        'maximum_interpolated_frames': MAX_INTERPOLATED_FRAMES,
        'counts': dict(Counter(row['status'] for row in rows.values())),
        'interpretation': 'Image points are visible-box centres, not feet or court positions. Orange points are straight interpolation between saved/raw endpoints, not detections. The raw-ID portions remain unverified; no distance, speed, coverage or accuracy metric is supported.',
        'preview': image.name, 'frames': rows,
    }
    if output.exists() or image.exists():
        raise FileExistsError(f'Refusing to overwrite a path draft: {stem}')
    output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    render(VIDEO, rows, image)
    print(output.name, payload['counts'])


if __name__ == '__main__':
    main()
