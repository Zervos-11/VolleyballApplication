"""Register the AoEP source and create proposal-free review frames without labels."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
VIDEO = MATCH / 'source_AoEP-YiWRvc.mp4'
PROBE = MATCH / 'screening/video_probe.json'
RAW = ROOT / 'data/processed/aoep_new_source/raw_74880_75540.json'
POINT = (74980, 75390)
DENSE = (75180, 75230)


def write_if_new(path, value):
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8')) != value:
            raise ValueError(f'Refusing to overwrite existing data: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    probe = json.loads(PROBE.read_text(encoding='utf-8'))
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    sha = probe['sha256']
    if raw['source_sha256'] != sha or not probe['meets_basic_resolution_and_fps_rule']:
        raise ValueError('Source screening and frozen tracker disagree')
    if not (raw['first_frame'] <= POINT[0] < POINT[1] <= raw['last_frame'] + 1):
        raise ValueError('Proposed point is not within frozen inference')
    if not (POINT[0] <= DENSE[0] < DENSE[1] <= POINT[1]):
        raise ValueError('Dense review interval is outside the point')
    source = {
        'match_id': MATCH.name, 'source_group_id': 'youtube_AoEP-YiWRvc',
        'source_url': 'https://www.youtube.com/watch?v=AoEP-YiWRvc',
        'source_title': 'ROUND 6 SVL 2025 - Lynx Volleyball Club vs ProVolley Academy',
        'uploader': 'ProVolley Australia', 'upload_date': '20250706',
        'video_file': VIDEO.relative_to(ROOT).as_posix(), 'sha256': sha,
        'camera': {'width': probe['width'], 'height': probe['height'], 'fps': probe['fps']},
        'frame_count': probe['frame_count'], 'duration_s': probe['duration_s'],
        'split': 'new_source_release_evaluation',
        'content_note': 'Video contains a GAME HIGHLIGHTS watermark; selected point appears continuous in sampled frames.',
        'frame_rate_verified': False, 'rights_status': 'pending',
        'privacy_review_status': 'pending', 'annotation_status': 'not_started',
    }
    write_if_new(MATCH / 'source_record.json', source)
    selection = {
        'match_id': MATCH.name, 'dataset_stage': 'new_source_release_evaluation',
        'split': 'heldout', 'source_sha256': sha,
        'raw_prediction_sha256': hashlib.sha256(RAW.read_bytes()).hexdigest(),
        'design': 'Source-only visually selected point; detector output frozen before any labels. Boundaries are provisional.',
        'rallies': [{
            'rally_id': 'point_21m', 'start_frame': POINT[0],
            'end_frame_exclusive': POINT[1], 'target_half': 'near_camera',
            'window_start_frame': raw['first_frame'],
            'window_end_frame_exclusive': raw['last_frame'] + 1,
            'target_team': 'yellow team on near court',
            'boundary_status': 'visual_bracket_unverified',
            'notes': 'Source-only frames show a far-white serve toss near 74990, likely contact around 75029, active play around 75285, and players walking by 75320. Confirm exact contact and dead-ball frames before full-rally scoring.',
        }],
        'dense_review_window': {'first_frame': DENSE[0], 'last_frame': DENSE[1] - 1,
                                'target_players': 6, 'status': 'not_annotated'},
    }
    write_if_new(MATCH / 'pilot/selection.json', selection)
    draft = {
        'match_id': MATCH.name, 'rally_id': 'point_21m',
        'start_frame': POINT[0], 'end_frame_exclusive': POINT[1],
        'boundary_status': 'visual_bracket_unverified', 'source_sha256': sha,
        'fps': probe['fps'], 'annotation_mode': 'independent_manual_no_detector_proposals',
        'frames': [{'frame_index': frame, 'time_s': round(frame / probe['fps'], 6),
                    'proposals': []} for frame in range(*POINT)],
        'status': 'blank_source_only_review_schedule',
    }
    write_if_new(MATCH / 'pilot/player_drafts/point_21m.json', draft)
    print(f'Prepared {POINT[1] - POINT[0]} proposal-free point frames; '
          f'dense window {DENSE[0]}-{DENSE[1] - 1}')


if __name__ == '__main__':
    main()
