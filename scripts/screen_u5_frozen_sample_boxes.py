"""Screen fixed pre-score source frames from every frozen point for near boxes."""
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
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
CALIBRATION = BASE / 'screening/near_court_candidate.json'
SAMPLE = BASE / 'screening/rally_sample_score_only.json'
CONTEXT = BASE / 'screening/selected_point_review/record.json'
MODEL = ROOT / 'yolov8n.pt'
OUT = BASE / 'screening/frozen_sample_box_screen.json'
SHEETS = BASE / 'screening/frozen_sample_box_sheets'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def frame_at(cap, second):
    number = second * 30
    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
    ok, image = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
        raise RuntimeError(f'Could not decode frame {number}')
    return image


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    context = json.loads(CONTEXT.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    if not (digest(VIDEO) == manifest['video']['sha256'] == sample['source_sha256']):
        raise ValueError('Source mismatch')
    if context['sample_sha256'] != digest(SAMPLE):
        raise ValueError('Context does not match frozen sample')
    matrix = np.asarray(calibration['homography_image_to_court'], np.float64)
    model = YOLO(str(MODEL))
    cap = cv2.VideoCapture(str(VIDEO))
    SHEETS.mkdir(exist_ok=True)
    rows = []
    try:
        for set_number in (1, 2, 3):
            entries = [row for row in context['source_seconds'] if row['set'] == set_number]
            sheet = np.full((6 * 250, 3 * 427, 3), 245, np.uint8)
            for row_no, entry in enumerate(entries):
                for column, second in enumerate(entry['context_picks_s'][:3]):
                    image = frame_at(cap, second)
                    result = model(image, classes=[0], conf=.2, imgsz=960, verbose=False)[0]
                    accepted = []
                    boxes = result.boxes.xyxy.cpu().numpy()
                    scores = result.boxes.conf.cpu().numpy()
                    for box, confidence in zip(boxes, scores):
                        x1, y1, x2, y2 = map(float, box)
                        floor = cv2.perspectiveTransform(
                            np.asarray([[[(x1 + x2) / 2, y2]]], np.float32), matrix)[0, 0]
                        if not np.isfinite(floor).all() or not ((floor >= -0.25) & (floor <= 9.25)).all():
                            continue
                        accepted.append({'bbox_px': [round(v, 1) for v in (x1, y1, x2, y2)],
                                         'box_bottom_court_m': [round(float(v), 3) for v in floor],
                                         'confidence': round(float(confidence), 3)})
                        cv2.rectangle(image, (round(x1), round(y1)), (round(x2), round(y2)),
                                      (0, 190, 0), 2)
                    x, y = column * 427, row_no * 250
                    sheet[y:y + 240, x:x + 427] = cv2.resize(image, (427, 240),
                                                               interpolation=cv2.INTER_AREA)
                    cv2.putText(sheet, f"S{set_number} P{entry['point_number']} {second}s n={len(accepted)}",
                                (x + 4, y + 248), cv2.FONT_HERSHEY_SIMPLEX, .42,
                                (20, 20, 20), 1)
                    rows.append({'set': set_number, 'point_number': entry['point_number'],
                                 'second': second, 'source_frame': second * 30,
                                 'near_court_proposal_count': len(accepted),
                                 'near_court_proposals': accepted})
            if not cv2.imwrite(str(SHEETS / f'set_{set_number}.jpg'), sheet,
                               [cv2.IMWRITE_JPEG_QUALITY, 93]):
                raise RuntimeError('Could not write box sheet')
    finally:
        cap.release()
    histogram = Counter(row['near_court_proposal_count'] for row in rows)
    output = {
        'status': 'detector_proposals_not_six_teammate_validation',
        'video_id': 'u5HnY2aNW14', 'source_sha256': manifest['video']['sha256'],
        'frozen_sample_sha256': digest(SAMPLE), 'context_sha256': digest(CONTEXT),
        'calibration_sha256': digest(CALIBRATION), 'model_sha256': digest(MODEL),
        'method': 'YOLOv8n person conf .20 imgsz 960, staged box-bottom court gate -0.25 to 9.25 m',
        'frames_screened': len(rows), 'count_histogram': dict(sorted(histogram.items())),
        'frames_with_at_least_six_proposals': sum(row['near_court_proposal_count'] >= 6 for row in rows),
        'rows': rows,
        'limitations': ['Gated proposals can include far-side players and officials.',
                        'The server may be off court or out of frame.',
                        'Three one-second-spaced navigation frames do not establish a full trajectory.',
                        'Staged court mapping and box-bottom floor positions are not validated.'],
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print({'frames': len(rows), 'at_least_six': output['frames_with_at_least_six_proposals'],
           'histogram': output['count_histogram']})


if __name__ == '__main__':
    main()
