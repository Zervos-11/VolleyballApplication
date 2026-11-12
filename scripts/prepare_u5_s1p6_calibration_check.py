"""Freeze an out-of-point source-only check of the already fitted court mapping."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SOURCE = SCREEN / 's1p6_fixed_window_source_review'
CANDIDATE = SCREEN / 's3p34_calibration_review/refined_candidate.json'
OUT = SCREEN / 's1p6_fixed_window_calibration_review'
FRAMES = (1759, 1783)
LANDMARKS = [
    {'code': 'baseline_left', 'label': 'Near baseline × left sideline', 'court_m': [0, 0]},
    {'code': 'baseline_right', 'label': 'Near baseline × right sideline', 'court_m': [9, 0]},
    {'code': 'attack_left', 'label': 'Attack line × left sideline', 'court_m': [0, 6]},
    {'code': 'attack_right', 'label': 'Attack line × right sideline', 'court_m': [9, 6]},
    {'code': 'net_left', 'label': 'Floor net line × left sideline', 'court_m': [0, 9]},
    {'code': 'net_right', 'label': 'Floor net line × right sideline', 'court_m': [9, 9]},
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_manifest = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
    images = {row['source_frame']: row for row in source_manifest['images']}
    frames = []
    for number in FRAMES:
        image = images[number]
        assert sha(SOURCE / image['image']) == image['sha256']
        frames.append({'frame': number, 'image': image['image'], 'sha256': image['sha256']})
    candidate = json.loads(CANDIDATE.read_text(encoding='utf-8'))
    assert candidate['strict_metric_approval'] is False
    protocol = {
        'status': 'frozen_unmarked_out_of_point_calibration_check',
        'source_video_sha256': source_manifest['source_sha256'],
        'source_manifest_sha256': sha(SOURCE / 'manifest.json'),
        'candidate_transform_sha256': sha(CANDIDATE),
        'candidate_transform_fit_source_frame': candidate['source_frame_used_for_fit'],
        'purpose': 'test_existing_refined_near_court_mapping_on_two_new_s1p6_source_frames',
        'reviewer_context': 'same reviewer, previously exposed to staged transform and player tracker; transform frozen before these new marks',
        'frames': frames,
        'landmarks': LANDMARKS,
        'marking_rule': 'Click centre of each painted court-line intersection on the unboxed native-resolution image; uncertain or occluded intersections get null coordinates. The floor net line is below the suspended net.',
        'decision_rule_frozen_before_new_marks': {
            'required_visible_landmarks': 12,
            'maximum_projected_landmark_error_m': 0.2,
            'maximum_static_camera_registration_shift_px': 2.0,
            'scope': 'single_camera_near_court_operational_check_only',
            'interpretation': 'Passing is an out-of-point single-reviewer check of mapping stability, not independent player-position truth or full-rally validation.',
        },
    }
    OUT.mkdir(exist_ok=True)
    target = OUT / 'protocol.json'
    content = json.dumps(protocol, indent=2) + '\n'
    if target.exists():
        assert target.read_text(encoding='utf-8') == content, 'Frozen protocol changed'
    else:
        target.write_text(content, encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main()
