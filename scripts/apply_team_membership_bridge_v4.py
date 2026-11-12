"""Apply the team-only jump bridge to frozen heldout windows and jump events."""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_pilot_tracker import image_to_court
from team_membership_bridge_v4 import bridge_window


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
EVAL = Path('data/processed/heldout_crossing_eval_em6z')
OUT = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial/team_membership_bridge_trial_v4.json')
CALIBRATION = PILOT / 'calibration/near_court.json'
SOURCE = MATCH / 'heldout_source_cfr.mp4'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    matrix = image_to_court(json.loads(CALIBRATION.read_text()))
    source_hash = sha256(SOURCE)
    raw_path = PILOT / 'heldout_tracker_predictions.json'
    accepted_path = PILOT / 'heldout_team_filtered_predictions.json'
    raw = json.loads(raw_path.read_text())
    accepted = json.loads(accepted_path.read_text())
    if raw['source_sha256'] != source_hash or accepted['source_sha256'] != source_hash:
        raise ValueError('Heldout source hash mismatch')
    tasks = []
    for name in ('cross_a', 'cross_b'):
        window = raw['windows'][name]
        tasks.append((name, window['first_frame'], window['last_frame'],
                      window['predictions'], accepted['windows'][name]['predictions'],
                      {'raw_sha256': sha256(raw_path), 'accepted_sha256': sha256(accepted_path)}))
    for name, filename in (('jump_150_239', 'frozen_jump_segment_150_239.json'),
                           ('block_860_960', 'frozen_block_segment_860_960.json')):
        path = EVAL / filename
        segment = json.loads(path.read_text())
        if segment['source_sha256'] != source_hash:
            raise ValueError(f'{name}: source hash mismatch')
        tasks.append((name, segment['segment'][0], segment['segment'][1],
                      segment['raw_predictions'], segment['court_jersey_predictions'],
                      {'frozen_segment_sha256': sha256(path)}))
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    windows = {}
    try:
        for name, first, last, raw_predictions, accepted_predictions, hashes in tasks:
            rescued, diagnostics = bridge_window(
                video, raw_predictions, accepted_predictions, matrix, first, last)
            windows[name] = {'first_frame': first, 'last_frame': last,
                             **hashes, 'rescued': rescued, 'diagnostics': diagnostics}
            print(name, diagnostics['rescued_count'], diagnostics['rescued'][:15], flush=True)
    finally:
        video.release()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        'status': 'development_candidate',
        'source_sha256': source_hash,
        'calibration_sha256': sha256(CALIBRATION),
        'rule_sha256': sha256(Path('scripts/team_membership_bridge_v4.py')),
        'method': 'Same raw ByteTrack ID, five consecutive accepted near-court observations with box-bottom range <=15 px, rising box, image/jersey continuity across up to six frames with capped displacement, two-frame confirmation; team candidate only, airborne court position unknown.',
        'label_access': 'none', 'windows': windows,
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
