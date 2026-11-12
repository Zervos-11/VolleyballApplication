"""Run point-local five-Hz player tracking across all 18 selected edited clips."""

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402


BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = BASE / 'screening'
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
SAMPLE = SCREEN / 'rally_sample_score_only.json'
CLIPS = SCREEN / 'rally_cut_clip_register.json'
CORE = SCREEN / 'live_core_second_review.json'
CALIBRATION = SCREEN / 'near_court_candidate.json'
MODEL = ROOT / 'yolov8n.pt'
CHECKPOINTS = SCREEN / 'full_clip_track_checkpoints'
OUT = SCREEN / 'full_clip_track_screen.json'
FRAME_STEP = 6
METHOD = 'YOLOv8n conf .20 imgsz 960 plus ByteTrack at 5 Hz; tracker reset at each edited clip'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def grid(start, end):
    first = ((start + FRAME_STEP - 1) // FRAME_STEP) * FRAME_STEP
    return range(first, end, FRAME_STEP)


def checkpoint_path(set_number, point_number):
    return CHECKPOINTS / f's{set_number}_p{point_number:02d}.json'


def point_screen(model, cap, clip, core, transform, net_y):
    start = clip['clip_start_frame_inclusive']
    end = clip['clip_end_frame_exclusive']
    core_first = core['core_seconds_inclusive'][0] * 30
    core_end = (core['core_seconds_inclusive'][1] + 1) * 30
    assert start <= core_first < core_end <= end
    if getattr(model, 'predictor', None) and getattr(model.predictor, 'trackers', None):
        model.predictor.trackers[0].reset()
    rows = []
    for number in grid(start, end):
        cap.set(cv2.CAP_PROP_POS_FRAMES, number)
        ok, image = cap.read()
        if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
            raise RuntimeError(f'Could not decode source frame {number}')
        result = model.track(image, classes=[0], conf=.2, imgsz=960,
                             tracker='bytetrack.yaml', persist=True, verbose=False)[0]
        boxes = result.boxes.xyxy.cpu().numpy()
        scores = result.boxes.conf.cpu().numpy()
        ids = (result.boxes.id.int().cpu().tolist() if result.boxes.id is not None
               else [None] * len(boxes))
        proposals = []
        for box, confidence, track_id in zip(boxes, scores, ids):
            x1, y1, x2, y2 = map(float, box)
            floor = cv2.perspectiveTransform(
                np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), transform)[0, 0]
            if not np.isfinite(floor).all() or not ((floor >= -.25) & (floor <= 9.25)).all():
                continue
            proposals.append({
                'raw_track_id': track_id,
                'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                'box_bottom_court_m': [round(float(v), 3) for v in floor],
                'confidence': round(float(confidence), 3),
                'net_side_status': ('near_floor_side_candidate' if y2 >= net_y
                                    else 'net_boundary_review')
            })
        near_count = sum(p['net_side_status'] == 'near_floor_side_candidate'
                         for p in proposals)
        rows.append({'source_frame': number,
                     'in_conservative_core': core_first <= number < core_end,
                     'near_floor_side_candidate_count': near_count,
                     'net_boundary_review_count': len(proposals) - near_count,
                     'proposals': proposals})
    return rows


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    clips = json.loads(CLIPS.read_text(encoding='utf-8'))
    cores = json.loads(CORE.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    source_hash = manifest['video']['sha256']
    assert digest(VIDEO) == source_hash
    assert source_hash == sample['source_sha256'] == clips['source_sha256'] == cores['source_sha256']
    assert clips['frozen_sample_sha256'] == digest(SAMPLE)
    assert cores['frozen_sample_sha256'] == digest(SAMPLE)
    assert calibration['points_court_m'] == [[0, 0], [9, 0], [9, 9], [0, 9]]
    transform = np.asarray(calibration['homography_image_to_court'], np.float64)
    net_y = calibration['points_px'][2][1]
    assert calibration['points_px'][3][1] == net_y
    by_core = {(r['set'], r['point_number']): r for r in cores['rows']}
    by_clip = {(r['set'], r['point_number']): r for r in clips['selected_clips']}
    by_sample = {(r['set'], r['point_number']): r for r in sample['selected_events']}
    assert len(by_core) == len(by_clip) == len(by_sample) == 18
    assert set(by_core) == set(by_clip) == set(by_sample)
    metadata = {'source_sha256': source_hash, 'sample_sha256': digest(SAMPLE),
                'clips_sha256': digest(CLIPS), 'core_sha256': digest(CORE),
                'calibration_sha256': digest(CALIBRATION), 'model_sha256': digest(MODEL),
                'method': METHOD, 'frame_step': FRAME_STEP}
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    assert cap.isOpened()
    points = []
    try:
        for key in sorted(by_clip):
            clip = by_clip[key]
            checkpoint = checkpoint_path(*key)
            if checkpoint.exists():
                saved = json.loads(checkpoint.read_text(encoding='utf-8'))
                assert saved['metadata'] == metadata
                assert saved['set'] == key[0] and saved['point_number'] == key[1]
                assert saved['clip_start_frame'] == clip['clip_start_frame_inclusive']
                assert saved['clip_end_frame_exclusive'] == clip['clip_end_frame_exclusive']
                assert len(saved['rows']) == len(grid(saved['clip_start_frame'],
                                                      saved['clip_end_frame_exclusive']))
                points.append(saved)
                print(f'S{key[0]} P{key[1]}: reused {len(saved["rows"])} sampled frames', flush=True)
                continue
            rows = point_screen(model, cap, clip, by_core[key], transform, net_y)
            histogram = Counter(r['near_floor_side_candidate_count'] for r in rows)
            point = {'metadata': metadata, 'set': key[0], 'point_number': key[1],
                     'clip_start_frame': clip['clip_start_frame_inclusive'],
                     'clip_end_frame_exclusive': clip['clip_end_frame_exclusive'],
                     'core_seconds_inclusive': by_core[key]['core_seconds_inclusive'],
                     'candidate_count_histogram': dict(sorted(histogram.items())),
                     'rows': rows}
            checkpoint.write_text(json.dumps(point, indent=2) + '\n', encoding='utf-8')
            points.append(point)
            print(f'S{key[0]} P{key[1]}: screened {len(rows)} sampled frames; '
                  f'exactly six in {histogram[6]}', flush=True)
    finally:
        cap.release()
    summary = {'selected_clips': len(points),
               'sampled_frames': sum(len(p['rows']) for p in points),
               'exactly_six_near_candidates': sum(
                   r['near_floor_side_candidate_count'] == 6
                   for p in points for r in p['rows']),
               'at_least_six_near_candidates': sum(
                   r['near_floor_side_candidate_count'] >= 6
                   for p in points for r in p['rows']),
               'frames_in_conservative_core': sum(
                   r['in_conservative_core'] for p in points for r in p['rows']),
               'validated_six_player_trajectory_frames': 0}
    assert summary['selected_clips'] == 18 and summary['sampled_frames'] == 1005
    out = {'status': 'full_edited_clip_raw_tracking_proposals_not_validated_trajectories',
           **metadata, 'summary': summary, 'points': points,
           'limitations': ['Edited clip bounds include setup and aftermath, not exact live-play timing.',
                           'Point-local ByteTrack IDs can switch within a clip and differ from earlier core-only IDs.',
                           'Net-side and homography gates are geometric candidates, not source-reviewed identity.',
                           'Box bottoms during jumps or low posture may not locate grounded players.']}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(summary, flush=True)


if __name__ == '__main__':
    main()
