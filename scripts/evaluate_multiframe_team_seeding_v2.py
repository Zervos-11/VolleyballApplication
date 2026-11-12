"""Test two-frame jersey seeding without changing the frozen appearance rule."""

import hashlib
import json
from pathlib import Path

import cv2

from evaluate_pilot_tracker import evaluate_rally, image_to_court, in_target_region, iou, project
from evaluate_team_appearance import THRESHOLD, filter_rally, torso_histogram


MATCH = Path('data/matches/yt_FqE5pTJqx8g')
EVAL = Path('data/processed/pilot_tracker_evaluation')
OUT = EVAL / 'start_boundary_audit/multiframe_team_seed_v2_comparison.json'
RALLIES = ('r3', 'r5')


def filter_two_seed_frames(video, saved, tracked, matrix):
    frames = sorted(map(int, saved['frames']))
    seeds = []
    seed_boxes = []
    seed_sources = []
    filtered = {}
    for index, frame in enumerate(frames):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = video.read()
        if not ok:
            raise RuntimeError(f'Cannot decode frame {frame}')
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        candidates = []
        for pred in tracked['predictions'][str(frame)]:
            box = pred['bbox']
            xy = project([(box[0] + box[2]) / 2, box[3]], matrix)
            if not in_target_region(xy, index == 0):
                continue
            appearance = torso_histogram(hsv, box)
            if appearance is not None:
                candidates.append((pred, xy, *appearance))
        if index == 0:
            for pred, (x, y), hist, median_hsv in sorted(
                    candidates, key=lambda item: -item[0]['confidence']):
                yellow = (12 <= median_hsv[0] <= 38 and median_hsv[1] >= 85
                          and median_hsv[2] >= 120)
                if (0 <= x <= 9 and -3 <= y <= (9.5 if yellow else 6.5)
                        and all(iou(pred['bbox'], old) < .6 for old in seed_boxes)):
                    seeds.append(hist)
                    seed_boxes.append(pred['bbox'])
                    seed_sources.append({'frame': frame, 'track_id': pred['track_id']})
            if not seeds:
                raise ValueError('No first-frame seeds')
        kept = []
        for pred, _, hist, _ in candidates:
            if index == 0 or min(cv2.compareHist(
                    hist, seed, cv2.HISTCMP_BHATTACHARYYA)
                    for seed in seeds) <= THRESHOLD:
                kept.append(pred)
        filtered[str(frame)] = kept
        # Only add already accepted, high-confidence players in the interior
        # court on the second sampled frame. This cannot create a player box.
        if index == 1:
            for pred, (x, y), hist, _ in candidates:
                if (pred in kept and pred['confidence'] >= .65
                        and 0 <= x <= 9 and 0 <= y <= 9.0):
                    seeds.append(hist)
                    seed_sources.append({'frame': frame, 'track_id': pred['track_id']})
    return {**tracked, 'predictions': filtered}, seed_sources


def compact(metrics):
    keys = ('matched', 'missed', 'extra', 'sampled_identity_change_pairs',
            'sampled_identity_pairs')
    return {key: metrics[key] for key in keys}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    manifest = json.loads((MATCH / 'pilot/calibration/calibration_manifest.json').read_text())
    video = cv2.VideoCapture(str(MATCH / 'source_FqE5pTJqx8g.mp4'))
    if not video.isOpened():
        raise FileNotFoundError('Source video')
    result = {'source_file': str(MATCH / 'source_FqE5pTJqx8g.mp4'),
              'rule_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'method': 'Add high-confidence, already accepted near-court torso exemplars from the second saved frame, including players near the net; no labels used for filtering.',
              'rallies': {}}
    try:
        for rally in RALLIES:
            saved = json.loads((MATCH / 'pilot/player_annotations' / f'{rally}.json').read_text())
            tracked = json.loads((EVAL / f'{rally}_tracker_predictions.json').read_text())
            segment = next(value for value in manifest['camera_segments'].values()
                           if rally in value['rallies'])
            calibration = json.loads((MATCH / 'pilot/calibration' /
                                      segment['homography_file']).read_text())
            matrix = image_to_court(calibration)
            old, old_diagnostic = filter_rally(video, rally, saved, tracked, matrix)
            new, sources = filter_two_seed_frames(video, saved, tracked, matrix)
            old_metrics, _, _, _, _, _ = evaluate_rally(rally, saved, old, matrix)
            new_metrics, _, _, _, _, _ = evaluate_rally(rally, saved, new, matrix)
            result['rallies'][rally] = {
                'old_seed_track_ids': old_diagnostic['seed_track_ids'],
                'new_seed_sources': sources,
                'old': compact(old_metrics), 'two_frame': compact(new_metrics),
                'changed_boxes_by_frame': {
                    frame: {'old': len(old['predictions'][frame]),
                            'two_frame': len(new['predictions'][frame])}
                    for frame in new['predictions']
                    if old['predictions'][frame] != new['predictions'][frame]},
            }
            print(rally, result['rallies'][rally]['old'],
                  result['rallies'][rally]['two_frame'])
    finally:
        video.release()
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
