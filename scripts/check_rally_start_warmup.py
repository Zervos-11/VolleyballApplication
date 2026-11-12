"""Compare a 50-frame ByteTrack pre-roll on the two partly visible starts.

Original rally boundaries, saved annotations, and frozen predictions are read
only. Candidate predictions and scores are written under start_boundary_audit.
"""

import hashlib
import json
import os
from pathlib import Path

from evaluate_pilot_tracker import evaluate_rally, image_to_court, track_rally


MATCH = Path('data/matches/yt_FqE5pTJqx8g')
EVAL = Path('data/processed/pilot_tracker_evaluation')
OUT = EVAL / 'start_boundary_audit'
RALLIES = ('r3', 'r5')
WARMUP = 50


def summary(metrics):
    keys = ('matched', 'missed', 'extra', 'sampled_identity_change_pairs',
            'sampled_identity_pairs')
    return {key: metrics[key] for key in keys}


def main():
    score_path = OUT / 'warmup50_comparison.json'
    if score_path.exists():
        raise FileExistsError(score_path)
    model_path = Path('yolov8n.pt')
    os.environ['YOLO_CONFIG_DIR'] = str(Path('data/processed/ultralytics_config').resolve())
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    manifest = json.loads((MATCH / 'pilot/calibration/calibration_manifest.json').read_text())
    video_path = MATCH / 'source_FqE5pTJqx8g.mp4'
    result = {
        'source_video': str(video_path), 'model_sha256': model_hash,
        'warmup_frames': WARMUP,
        'scope': 'Two development rallies; sparse-frame box/ID diagnostic, not dense IDF1.',
        'rallies': {},
    }
    for rally in RALLIES:
        saved = json.loads((MATCH / 'pilot/player_annotations' / f'{rally}.json').read_text())
        original = json.loads((EVAL / f'{rally}_tracker_predictions.json').read_text())
        segment = next(value for value in manifest['camera_segments'].values()
                       if rally in value['rallies'])
        calibration = json.loads((MATCH / 'pilot/calibration' /
                                  segment['homography_file']).read_text())
        matrix = image_to_court(calibration)
        candidate_path = OUT / f'{rally}_warmup50_full.json'
        if candidate_path.exists():
            candidate = json.loads(candidate_path.read_text())
        else:
            candidate = track_rally(model_path, model_hash, video_path, rally,
                                    saved, candidate_path, warmup_frames=WARMUP)
        if (candidate['warmup_first_frame'] != saved['start_frame'] - WARMUP
                or candidate['start_frame'] != saved['start_frame']
                or candidate['end_frame_exclusive'] != saved['end_frame_exclusive']
                or candidate['model_sha256'] != original['model_sha256']):
            raise ValueError(f'{rally}: candidate provenance mismatch')
        baseline_metrics, _, _, _, _, _ = evaluate_rally(
            rally, saved, original, matrix)
        candidate_metrics, _, _, _, _, _ = evaluate_rally(
            rally, saved, candidate, matrix)
        result['rallies'][rally] = {
            'start_frame': saved['start_frame'],
            'warmup_first_frame': candidate['warmup_first_frame'],
            'baseline': summary(baseline_metrics),
            'warmup50': summary(candidate_metrics),
            'candidate_predictions_file': str(candidate_path),
        }
        print(rally, result['rallies'][rally])
    score_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
