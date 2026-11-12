"""Create six provisional image paths without filling unresolved player gaps."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2

from build_aoep_sam_image_path import build_path as sam_path, centre


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
RAW = DIR / 'raw_74880_75540.json'
NAV = DIR / 'dense_review_gap_audit.json'
SAVED = MATCH / 'pilot/player_annotations/point_21m.json'
VIDEO = MATCH / 'source_AoEP-YiWRvc.mp4'
FIRST, LAST = 75180, 75229
PLAYER_IDS = {
    'yellow_left_5': '5',
    'yellow_centre_left': '19',
    'yellow_centre_4': '4',
    'yellow_setter_18': '18',
    'navy_libero_10': '10',
    'yellow_right_entrant': 'Sam',
}
COLOURS = {
    'yellow_left_5': (180, 150, 0),
    'yellow_centre_left': (225, 100, 230),
    'yellow_centre_4': (60, 230, 230),
    'yellow_setter_18': (90, 180, 70),
    'navy_libero_10': (245, 170, 50),
    'yellow_right_entrant': (80, 80, 255),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_rows(predictions, navigation, saved_frames, first, last):
    rows = {player_id: {} for player_id in PLAYER_IDS}
    sam = sam_path(predictions, saved_frames, 75198, last, 517, 'Sam', 8)
    for frame in range(first, last + 1):
        key = str(frame)
        nav_by_player = {row['visual_player_id']: row for row in navigation[key]}
        saved_by_id = {p['player_id']: p for p in saved_frames.get(key, {}).get('players', [])}
        for visual_id, user_id in PLAYER_IDS.items():
            if visual_id == 'yellow_right_entrant':
                if frame < 75198:
                    status = 'out_of_frame_provisional' if frame <= 75192 else 'edge_entry_unresolved'
                    row = {'status': status, 'image_point_px': None,
                           'court_position_m': None, 'raw_track_id': None}
                else:
                    row = dict(sam[key])
                    row['raw_track_id'] = (517 if row['status'] == 'raw_box_centre_unverified' else None)
                rows[visual_id][key] = row
                continue
            saved = saved_by_id.get(user_id)
            if saved is not None:
                row = {'status': ('saved_assisted_box_centre' if saved['bbox'] else 'saved_no_box'),
                       'image_point_px': centre(saved['bbox']) if saved['bbox'] else None,
                       'court_position_m': None, 'raw_track_id': None}
            else:
                nav = nav_by_player[visual_id]
                raw_id = nav['candidate_raw_track_id']
                matches = ([p for p in predictions[key] if p['track_id'] == raw_id]
                           if nav['navigation_status'] == 'single_box_candidate' and raw_id is not None else [])
                if len(matches) > 1:
                    raise ValueError(f'Duplicate raw ID {raw_id} at frame {frame}')
                row = {'status': ('raw_box_candidate_unverified' if matches else
                                  'unresolved_no_distinct_box'),
                       'image_point_px': centre(matches[0]['bbox']) if matches else None,
                       'court_position_m': None,
                       'raw_track_id': raw_id if matches else None}
            rows[visual_id][key] = row
    # Two raw-ID changes for the setter are review boundaries, not silent ID merges.
    for frame in range(first + 1, last + 1):
        previous = rows['yellow_setter_18'][str(frame - 1)]
        current = rows['yellow_setter_18'][str(frame)]
        if (previous['raw_track_id'] is not None and current['raw_track_id'] is not None
                and previous['raw_track_id'] != current['raw_track_id']):
            current['identity_transition_review'] = {
                'from_raw_track_id': previous['raw_track_id'],
                'to_raw_track_id': current['raw_track_id'],
            }
    return rows


def render(video_path, players, path):
    cap = cv2.VideoCapture(str(video_path))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 75220)
        ok, image = cap.read()
        if not ok:
            raise RuntimeError('Cannot decode source frame 75220')
    finally:
        cap.release()
    for player_id, path_rows in players.items():
        colour = COLOURS[player_id]
        previous = None
        for frame, row in path_rows.items():
            point = row['image_point_px']
            if point is None:
                previous = None
                continue
            pixel = tuple(round(value) for value in point)
            if row.get('identity_transition_review'):
                previous = None
            if previous is not None:
                line_colour = ((20, 145, 255) if row['status'] == 'interpolated_image_centre_not_observed'
                               else colour)
                cv2.line(image, previous, pixel, line_colour, 3)
            if int(frame) in (FIRST, LAST) or row['status'] == 'interpolated_image_centre_not_observed':
                dot_colour = ((20, 145, 255) if row['status'] == 'interpolated_image_centre_not_observed'
                              else colour)
                cv2.circle(image, pixel, 4, dot_colour, -1)
            previous = pixel
    cv2.rectangle(image, (6, 5), (800, 130), (12, 18, 30), -1)
    cv2.putText(image, 'AoEP six near-player image paths, frames 75180-75229',
                (16, 31), cv2.FONT_HERSHEY_SIMPLEX, .65, (255, 255, 255), 2)
    cv2.putText(image, 'BOX CENTRES ONLY: orange=Sam estimated; centre-left stops at 75205',
                (16, 57), cv2.FONT_HERSHEY_SIMPLEX, .48, (255, 255, 255), 1)
    for index, player_id in enumerate(PLAYER_IDS):
        x = 16 + (index % 3) * 260
        y = 84 + (index // 3) * 27
        cv2.circle(image, (x + 8, y - 5), 6, COLOURS[player_id], -1)
        cv2.putText(image, player_id.replace('yellow_', '').replace('navy_', ''),
                    (x + 20, y), cv2.FONT_HERSHEY_SIMPLEX, .42, (255, 255, 255), 1)
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f'Cannot write {path}')


def main():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    nav = json.loads(NAV.read_text(encoding='utf-8'))
    saved = json.loads(SAVED.read_text(encoding='utf-8'))
    source_hash = sha256(VIDEO)
    if raw['source_sha256'] != source_hash or nav['source_sha256'] != source_hash:
        raise ValueError('Source provenance mismatch')
    if nav['duplicate_adjusted_sha256'] is None:
        raise ValueError('Expected frozen navigation provenance')
    players = candidate_rows(raw['predictions'], nav['frames'], saved['frames'], FIRST, LAST)
    saved_hash = sha256(SAVED)
    stem = f'six_image_paths_{FIRST}_{LAST}_{saved_hash[:10]}_v2'
    output, preview = DIR / f'{stem}.json', DIR / f'{stem}.jpg'
    if output.exists() or preview.exists():
        raise FileExistsError(f'Refusing to overwrite {stem}')
    payload = {
        'status': 'provisional_six_player_image_paths_not_court_metrics_or_accuracy',
        'source_sha256': source_hash, 'raw_sha256': sha256(RAW),
        'navigation_sha256': sha256(NAV), 'saved_annotations_sha256': saved_hash,
        'frame_range_inclusive': [FIRST, LAST],
        'player_ids': PLAYER_IDS,
        'status_counts_by_player': {player_id: dict(Counter(r['status'] for r in path.values()))
                                    for player_id, path in players.items()},
        'interpretation': 'All points are image-box centres. Saved boxes are assisted and raw candidates are unverified. Only the short Sam gap is interpolated; the centre-left overlap remains unresolved. Setter raw-ID changes break the drawn line. No footpoint, court metres, speed, coverage or accuracy is inferred.',
        'preview': preview.name,
        'players': players,
    }
    output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    render(VIDEO, players, preview)
    print(output.name)
    for player_id, counts in payload['status_counts_by_player'].items():
        print(player_id, counts)


if __name__ == '__main__':
    main()
