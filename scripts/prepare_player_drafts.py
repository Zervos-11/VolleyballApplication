"""Create person-box proposals for pilot annotation; never create reviewed labels."""
import argparse
import hashlib
import json
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'data/processed/ultralytics_config'
(CONFIG / 'Ultralytics').mkdir(parents=True, exist_ok=True)
os.environ.setdefault('YOLO_CONFIG_DIR', str(CONFIG))

import cv2
from ultralytics import YOLO


def prepare(match, rally_id, refresh=False):
    out = match / 'pilot/player_drafts'
    path = out / f'{rally_id}.json'
    if path.exists() and not refresh:
        raise ValueError('Draft already exists; use --refresh only before saving player labels')
    saved = match / 'pilot/player_annotations' / f'{rally_id}.json'
    if refresh and saved.exists() and json.loads(saved.read_text()).get('frames'):
        raise ValueError('Saved player labels exist; reconcile their frame schedule before regeneration')
    source = json.loads((match / 'source_record.json').read_text())
    selection = json.loads((match / 'pilot/selection.json').read_text())
    rally = next(r for r in selection['rallies'] if r['rally_id'] == rally_id)
    review_file = match / 'pilot/boundary_review.json'
    reviews = json.loads(review_file.read_text()) if review_file.exists() else {}
    boundary = reviews.get(rally_id, rally)
    if boundary.get('usable') is False:
        raise ValueError('This rally has been excluded')
    start, end = boundary['start_frame'], boundary['end_frame_exclusive']
    fps = source['camera']['fps']
    sparse = list(range(start, end, round(fps)))
    sparse = sorted(set(sparse + [end - 1]))
    dense_start = min((start + end) // 2, max(start, end - round(2 * fps)))
    dense_end = min(end, dense_start + round(2 * fps))
    # Record a dense identity window for future annotation; generate sparse proposals first.
    model_path = ROOT / 'yolov8n.pt'
    if not model_path.exists():
        raise ValueError('Local model weights missing; no implicit model download')
    model = YOLO(str(model_path))
    video = ROOT / source['video_file']
    cap = cv2.VideoCapture(str(video))
    frames = []
    try:
        for index in sparse:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, image = cap.read()
            if not ok:
                raise ValueError(f'Cannot decode frame {index}')
            result = model.predict(image, classes=[0], conf=0.30, imgsz=960, device='cpu', verbose=False)[0]
            people = []
            for j, box in enumerate(result.boxes):
                coords = [round(float(v), 2) for v in box.xyxy[0].tolist()]
                people.append(dict(proposal_id=f'f{index}_det{j + 1:02d}', bbox=coords,
                                   confidence=round(float(box.conf[0]), 5)))
            frames.append(dict(frame_index=index, time_s=index / fps, proposals=people))
            print(f'{rally_id} frame {index}: {len(people)} person proposals', flush=True)
    finally:
        cap.release()
    result = dict(match_id=match.name, rally_id=rally_id, start_frame=start, end_frame_exclusive=end,
                  boundary_status=boundary.get('boundary_status', 'model_proposed_unreviewed'),
                  source_sha256=source['sha256'], fps=fps,
                  model='yolov8n.pt', model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
                  confidence_threshold=0.30, imgsz=960, frames=frames,
                  dense_window=(dict(start_frame=dense_start, end_frame_exclusive=dense_end, annotation_status='not_started')
                                if rally_id == selection['rallies'][0]['rally_id'] else None),
                  status='automatic_proposals_only',
                  notes='Person detections include non-players and missed/incorrect boxes. Proposal IDs do not identify people across frames. Footpoints, identities and visibility require manual annotation.')
    out.mkdir(exist_ok=True)
    if path.exists():
        history = out / 'history'
        history.mkdir(exist_ok=True)
        (history / f'{rally_id}_{uuid.uuid4().hex}.json').write_text(path.read_text())
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, indent=2) + '\n')
    temporary.replace(path)
    print(f'Saved {len(frames)} sparse frames to {path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--match-dir', type=Path, required=True)
    parser.add_argument('--rally', default='r1')
    parser.add_argument('--refresh', action='store_true', help='Archive and replace proposals only if no player labels are saved')
    args = parser.parse_args()
    prepare(args.match_dir, args.rally, args.refresh)
