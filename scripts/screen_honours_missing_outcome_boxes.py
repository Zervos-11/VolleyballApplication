"""Search nearby source frames for six-person box proposals in missing outcome groups."""
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('YOLO_CONFIG_DIR', str(ROOT / '.yolo_config'))
from ultralytics import YOLO  # noqa: E402

SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
SCAN = ROOT / 'data/processed/honours_saved_game_state_scan.json'
MODEL = ROOT / 'yolov8n.pt'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration'
OUT = ROOT / 'data/processed/honours_missing_outcome_box_screen.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_MISSING_OUTCOME_BOX_SCREEN.md'
SHEET = ROOT / 'data/processed/honours_missing_outcome_box_screen.jpg'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, sample, scan = read(SOURCE), read(SAMPLE), read(SCAN)
    if len({source['sha256'], sample['source_sha256'], scan['source_sha256']}) != 1:
        raise ValueError('Source hashes disagree')
    model = YOLO(str(MODEL))
    matrices = {}
    for set_number in (2, 3):
        path = CALIBRATION / 'camera_r2_r5.json'
        camera = read(path)
        matrices[set_number] = cv2.getPerspectiveTransform(
            np.asarray(camera['points_px'], np.float32),
            np.asarray(camera['points_court_m'], np.float32))
    selected = {(p['set'], p['point_number']): p for p in sample['selected_points']}
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    points = []
    try:
        for point in scan['by_point']:
            if point['set'] not in (2, 3) or point['winner'] != 'UTS':
                continue
            key = point['set'], point['point_number']
            entry = selected[key]
            bounds = (entry['seek_from_frame'], entry['seek_to_frame_exclusive'])
            centers = point['play_frame_indices']
            frames = sorted({c + offset for c in centers for offset in (-30, -15, 0, 15, 30)
                             if bounds[0] <= c + offset < bounds[1]})
            rows = []
            for number in frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, number)
                ok, image = cap.read()
                if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
                    raise RuntimeError(f'Could not decode frame {number}')
                prediction = model.predict(image, classes=[0], conf=.20, imgsz=960,
                                           verbose=False)[0]
                boxes = prediction.boxes.xyxy.cpu().numpy() if prediction.boxes is not None else np.empty((0, 4))
                confs = prediction.boxes.conf.cpu().numpy() if prediction.boxes is not None else np.empty((0,))
                candidates = []
                for box, confidence in zip(boxes, confs):
                    x1, y1, x2, y2 = map(float, box)
                    if y2 - y1 < 35:
                        continue
                    ground = cv2.perspectiveTransform(
                        np.asarray([[[.5 * (x1 + x2), y2]]], np.float32), matrices[key[0]])[0, 0]
                    if np.isfinite(ground).all() and ((ground >= 0) & (ground <= 9)).all():
                        candidates.append({'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                           'confidence': round(float(confidence), 3)})
                rows.append({'frame': number, 'near_court_candidate_count': len(candidates),
                             'candidates': candidates})
            points.append({'set': key[0], 'point_number': key[1], 'winner': point['winner'],
                           'play_proposal_centers': centers, 'screened_frames': len(rows),
                           'six_candidate_frames': [r['frame'] for r in rows if r['near_court_candidate_count'] >= 6],
                           'max_candidate_count': max((r['near_court_candidate_count'] for r in rows), default=0),
                           'rows': rows})
            print(f'S{key[0]} P{key[1]}: {len(rows)} frames, max {points[-1]["max_candidate_count"]}, '
                  f'{len(points[-1]["six_candidate_frames"])} six-box proposals', flush=True)
    finally:
        cap.release()
    result = {'status': 'detector_navigation_proposals_not_player_labels',
              'source_sha256': source['sha256'], 'sample_sha256': sha(SAMPLE),
              'game_state_scan_sha256': sha(SCAN), 'detector_sha256': sha(MODEL),
              'calibration_sha256': sha(CALIBRATION / 'camera_r2_r5.json'),
              'method': 'At each saved model-play centre in UTS-won sets 2-3, screen centre +/-30 frames every 15 frames with YOLOv8n conf=.20 imgsz=960; retain person boxes whose bottom centre projects into the nominal 9m square.',
              'points': points,
              'limitations': ['Six detections do not establish six distinct near-side players.',
                              'The model play centre is not a source-reviewed phase label.',
                              'Box bottoms and staged court projection are unvalidated proxy positions.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    sheet = np.full((1080, 2880, 3), 240, dtype=np.uint8)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    try:
        for index, point in enumerate(points):
            best = max(point['rows'], key=lambda r: (r['near_court_candidate_count'], -abs(
                r['frame'] - point['play_proposal_centers'][0])))
            cap.set(cv2.CAP_PROP_POS_FRAMES, best['frame'])
            ok, image = cap.read()
            if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != best['frame'] + 1:
                raise RuntimeError(f'Could not decode review frame {best["frame"]}')
            for candidate in best['candidates']:
                x1, y1, x2, y2 = map(round, candidate['bbox_px'])
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 175, 0), 3)
            cv2.putText(image, f'S{point["set"]} P{point["point_number"]} frame {best["frame"]} n={len(best["candidates"])}',
                        (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
            row, col = divmod(index, 3)
            sheet[row * 540:(row + 1) * 540, col * 960:(col + 1) * 960] = cv2.resize(
                image, (960, 540), interpolation=cv2.INTER_AREA)
    finally:
        cap.release()
    if not cv2.imwrite(str(SHEET), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError(f'Failed to write {SHEET}')
    result['review_sheet_sha256'] = sha(SHEET)
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(f"| {p['set']} | {p['point_number']} | {p['screened_frames']} | "
                      f"{p['max_candidate_count']} | {len(p['six_candidate_frames'])} | "
                      f"{', '.join(map(str, p['six_candidate_frames'][:8])) or 'none'} |"
                      for p in points)
    REPORT.write_text(f'''# Nearby box proposals for missing outcome groups

The [source-bound detector screen](../data/processed/honours_missing_outcome_box_screen.json) searched short neighborhoods around model-proposed play frames for the six UTS-won points in sets two and three. It preserves the frozen sample and all saved annotations. The detector counts person boxes whose bottom centre projects into the nominal near-side court; these are proposals, not six verified teammates or final metric positions.

| Set | Point | Frames screened | Max near-court boxes | Frames with 6+ boxes | First candidate frames |
| ---: | ---: | ---: | ---: | ---: | --- |
{table}

The next source check is to inspect the listed six-box frames for actual live play, six distinct near-side players and usable grounded boxes. A detector count alone cannot resolve team identity, occlusion or a player partly outside the image. Only after that check should a box-centre image movement proxy or tested box-bottom court proxy be measured. Existing saved frames with fewer boxes remain valid evidence of missingness.

[Best-frame review sheet](../data/processed/honours_missing_outcome_box_screen.jpg).
''', encoding='utf-8')


if __name__ == '__main__':
    main()
