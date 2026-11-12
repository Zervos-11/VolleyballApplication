"""Screen frozen sample navigation stills for near-court person proposals.

This uses detector box bottoms and staged geometry only as a review queue. It
does not create player identities, accepted floor points, or metric input.
"""
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402

MANIFEST = ROOT / 'data/processed/honours_sample_sheets/manifest.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
MODEL = ROOT / 'yolov8n.pt'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration'
OUTPUT = ROOT / 'data/processed/honours_sample_detector_feasibility.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_SAMPLE_DETECTOR_SCREEN.md'
SHEET_DIR = ROOT / 'data/processed/honours_sample_detector_sheets'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest, source = read(MANIFEST), read(SOURCE)
    assert manifest['source_sha256'] == source['sha256']
    model = YOLO(str(MODEL))
    camera_files = {1: CALIBRATION / 'camera_r1.json',
                    2: CALIBRATION / 'camera_r2_r5.json',
                    3: CALIBRATION / 'camera_r2_r5.json'}
    matrices = {}
    for set_number, path in camera_files.items():
        c = read(path)
        matrices[set_number] = cv2.getPerspectiveTransform(
            np.asarray(c['points_px'], np.float32),
            np.asarray(c['points_court_m'], np.float32))
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    points = []
    try:
        for sheet in manifest['sheets']:
            set_number = sheet['set']
            for point in sheet['rows']:
                frame_rows = []
                for frame_number in point['shown_frames']:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                    ok, frame = cap.read()
                    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
                        raise RuntimeError(f'Could not decode exact frame {frame_number}')
                    result = model.predict(frame, classes=[0], conf=.20, imgsz=960,
                                           verbose=False)[0]
                    boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else np.empty((0, 4))
                    confs = result.boxes.conf.cpu().numpy() if result.boxes is not None else np.empty((0,))
                    candidates = []
                    for box, confidence in zip(boxes, confs):
                        x1, y1, x2, y2 = map(float, box)
                        if y2 - y1 < 35:
                            continue
                        foot = np.asarray([[[.5 * (x1 + x2), y2]]], np.float32)
                        court = cv2.perspectiveTransform(foot, matrices[set_number])[0, 0]
                        x_m, y_m = map(float, court)
                        if np.isfinite(x_m) and np.isfinite(y_m) and 0 <= x_m <= 9 and 0 <= y_m <= 9:
                            candidates.append({'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                               'confidence': round(float(confidence), 3),
                                               'box_bottom_court_m': [round(x_m, 2), round(y_m, 2)]})
                    frame_rows.append({'frame': frame_number, 'all_person_detections': len(boxes),
                                       'near_court_box_bottom_candidates': len(candidates),
                                       'candidates': candidates})
                points.append({'set': set_number, 'point_number': point['point_number'],
                               'winner': point['winner'], 'timing_basis': point['timing_basis'],
                               'frames': frame_rows,
                               'max_near_court_box_bottom_candidates': max(
                                   r['near_court_box_bottom_candidates'] for r in frame_rows)})
    finally:
        cap.release()
    summary = {'frozen_sample_points': len(points),
               'points_with_six_or_more_candidates_on_a_navigation_frame': sum(
                   p['max_near_court_box_bottom_candidates'] >= 6 for p in points),
               'points_without_six_candidates_on_any_navigation_frame': sum(
                   p['max_near_court_box_bottom_candidates'] < 6 for p in points)}
    result = {'status': 'automatic_navigation_frame_detector_screen_not_labels',
              'source_sha256': source['sha256'],
              'source_manifest_sha256': sha(MANIFEST), 'model_sha256': sha(MODEL),
              'camera_r1_sha256': sha(camera_files[1]),
              'camera_r2_r5_sha256': sha(camera_files[2]),
              'method': 'YOLOv8n person boxes at three heuristic navigation frames per frozen point; box bottoms projected through staged court transforms; count candidates inside 0-9m square.',
              'limitations': ['Heuristic navigation frames may miss actual play.',
                              'Box bottoms are not verified floor contacts.',
                              'Detections have no player identity or team membership.',
                              'The set-three camera transform is a coarse screen only and has not been checked for every selected frame.'],
              'summary': summary, 'points': points}
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    try:
        for set_number in (1, 2, 3):
            sheet = np.full((1080, 2880, 3), 240, dtype=np.uint8)
            for index, point in enumerate(p for p in points if p['set'] == set_number):
                best = max(point['frames'], key=lambda r: r['near_court_box_bottom_candidates'])
                cap.set(cv2.CAP_PROP_POS_FRAMES, best['frame'])
                ok, frame = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != best['frame'] + 1:
                    raise RuntimeError(f'Could not decode exact frame {best["frame"]}')
                for candidate in best['candidates']:
                    x1, y1, x2, y2 = map(round, candidate['bbox_px'])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 175, 0), 3)
                    cv2.circle(frame, (round(.5 * (x1 + x2)), y2), 8, (0, 175, 0), -1)
                cv2.putText(frame, f'S{set_number} P{point["point_number"]} frame {best["frame"]} n={len(best["candidates"])}',
                            (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
                row, col = divmod(index, 3)
                sheet[row * 540:(row + 1) * 540, col * 960:(col + 1) * 960] = cv2.resize(
                    frame, (960, 540), interpolation=cv2.INTER_AREA)
            path = SHEET_DIR / f'set_{set_number}_best_navigation_frames.jpg'
            if not cv2.imwrite(str(path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92]):
                raise RuntimeError(f'Failed to write {path}')
    finally:
        cap.release()
    result['best_frame_sheet_sha256'] = {
        str(set_number): sha(SHEET_DIR / f'set_{set_number}_best_navigation_frames.jpg')
        for set_number in (1, 2, 3)}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    rows = '\n'.join(f"| {p['set']} | {p['point_number']} | {p['winner']} | "
                     f"{', '.join(str(f['near_court_box_bottom_candidates']) for f in p['frames'])} | "
                     f"{p['max_near_court_box_bottom_candidates']} |" for p in points)
    REPORT.write_text(f'''# Frozen-sample detector feasibility screen

The [machine-readable screen](../data/processed/honours_sample_detector_feasibility.json) applies the local YOLOv8n person model to three **heuristic navigation frames** for each of the 18 frozen ProVolley vs UTS points. It counts detector boxes whose bottom centre projects into the nominal near-side 9 m square using staged camera geometry. These are proposals, not identified players or accepted floor positions.

{summary['points_with_six_or_more_candidates_on_a_navigation_frame']}/18 points have at least one navigation frame with six or more projected near-court person boxes. A lower count does not exclude a point: the heuristic frames may miss play, a player may be hidden, or the detector may miss a person. A count of six does not establish that six distinct target-team players are present. The score sample remains frozen; do not substitute points based on this screen.

| Set | Point | Winner | Three frame candidate counts | Maximum |
| ---: | ---: | --- | --- | ---: |
{rows}

The [R2 source audit](HONOURS_R2_READINESS.md) remains the only point with linked pilot player annotations. This detector screen is a review-navigation aid and contributes **zero validated metric frames**.

Best-frame sheets: [set 1](../data/processed/honours_sample_detector_sheets/set_1_best_navigation_frames.jpg), [set 2](../data/processed/honours_sample_detector_sheets/set_2_best_navigation_frames.jpg), [set 3](../data/processed/honours_sample_detector_sheets/set_3_best_navigation_frames.jpg). Green boxes are automatic near-court proposals; they may include opponents or miss target players.
''', encoding='utf-8')
    print(f'Wrote {OUTPUT} and {REPORT}: {summary}')


if __name__ == '__main__':
    main()
