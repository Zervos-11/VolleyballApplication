"""Apply the unchanged court + jersey candidate filter to frozen ref match boxes."""

import hashlib
import json
import argparse
from pathlib import Path

import cv2

from evaluate_pilot_tracker import image_to_court
from evaluate_team_appearance import THRESHOLD, filter_rally


BASE = Path('data/processed/pilot_tracker_evaluation/independent_side_eval_ref_audio1')
RAW = BASE / 'raw_320_369.json'
SOURCE = Path('data/matches/yt_ref_audio1/youtube_rBgLLAwDU8M.mp4')
CALIBRATION = Path('data/matches/yt_ref_audio1/homography.json')
RULE = Path('scripts/evaluate_team_appearance.py')
OUT = BASE / 'unchanged_court_jersey_candidates.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_filter(raw_path=RAW, out=OUT, source=SOURCE, calibration=CALIBRATION):
    if out.exists():
        raise FileExistsError(out)
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(source) or raw['calibration_sha256'] != sha256(calibration):
        raise ValueError('Frozen source or calibration changed')
    matrix = image_to_court(json.loads(calibration.read_text(encoding='utf-8')))
    video = cv2.VideoCapture(str(source))
    if not video.isOpened():
        raise FileNotFoundError(source)
    try:
        selected, diagnostics = filter_rally(
            video, f"ref_audio1_{raw['first_frame']}_{raw['last_frame']}",
            {'frames': {str(frame): None for frame in range(raw['first_frame'],
                                                           raw['last_frame'] + 1)}},
            {'predictions': raw['predictions']}, matrix)
    finally:
        video.release()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        'status': 'frozen_unlabelled_application',
        'source_sha256': raw['source_sha256'], 'raw_sha256': sha256(raw_path),
        'calibration_sha256': sha256(calibration), 'rule_sha256': sha256(RULE),
        'appearance_threshold': THRESHOLD, 'label_access': 'none',
        'diagnostics': diagnostics, 'predictions': selected['predictions'],
    }, indent=2) + '\n', encoding='utf-8')
    print(diagnostics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=RAW)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--calibration', type=Path, default=CALIBRATION)
    args = parser.parse_args()
    apply_filter(args.raw, args.out, args.source, args.calibration)


if __name__ == '__main__':
    main()
