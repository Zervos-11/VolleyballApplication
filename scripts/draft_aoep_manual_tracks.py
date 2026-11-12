"""Propagate source-only hand boxes on AoEP; output incomplete review material."""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4'
OUT = ROOT / 'data/processed/aoep_new_source/source_only_mil_75180_75229'
FIRST, LAST = 75180, 75229
# Boxes drawn from the original source frame 75180, without detector overlays.
SEEDS = {
    'near_1_yellow_left_5': [128, 275, 242, 501],
    'near_2_yellow_centre_left': [505, 289, 584, 463],
    'near_3_yellow_centre_4': [572, 284, 666, 531],
    'near_4_yellow_setter': [718, 210, 806, 470],
    'near_5_navy_libero_10': [842, 317, 970, 534],
}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir(parents=True)
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise FileNotFoundError(VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, FIRST)
    try:
        ok, first_image = cap.read()
        if not ok:
            raise RuntimeError(f'Cannot decode frame {FIRST}')
        trackers = {}
        for player_id, (x1, y1, x2, y2) in SEEDS.items():
            tracker = cv2.TrackerMIL_create()
            tracker.init(first_image, (x1, y1, x2 - x1, y2 - y1))
            trackers[player_id] = tracker
        rows = {}
        images = []
        for frame in range(FIRST, LAST + 1):
            if frame == FIRST:
                image = first_image
                boxes = SEEDS
            else:
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f'Cannot decode frame {frame}')
                boxes = {}
                for player_id, tracker in trackers.items():
                    found, (x, y, w, h) = tracker.update(image)
                    boxes[player_id] = ([int(x), int(y), int(x + w), int(y + h)]
                                        if found else None)
            rows[str(frame)] = boxes
            preview = image.copy()
            for player_id, box in boxes.items():
                if box is None:
                    continue
                x1, y1, x2, y2 = box
                cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(preview, player_id.split('_')[1], (x1, max(20, y1 - 7)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 0), 3)
                cv2.putText(preview, player_id.split('_')[1], (x1, max(20, y1 - 7)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 1)
            cv2.putText(preview, str(frame), (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            images.append(cv2.resize(preview, (960, 540)))
    finally:
        cap.release()
    payload = {
        'status': 'source_only_assisted_draft_unreviewed',
        'source_sha256': hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
        'first_frame': FIRST, 'last_frame': LAST,
        'seed_source': 'manual boxes drawn from unmarked source frame 75180',
        'warning': 'MIL can drift and only five near people are seeded. The sixth person is unlocated. Do not score these boxes as ground truth.',
        'boxes': rows,
    }
    (OUT / 'draft.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    for chunk in range(10):
        sheet = cv2.vconcat(images[chunk * 5:(chunk + 1) * 5])
        if not cv2.imwrite(str(OUT / f'check_{chunk + 1:02d}.jpg'), sheet):
            raise OSError('Could not save visual review sheet')
    print(f'Saved {len(rows)} incomplete source-only draft frames to {OUT}')


if __name__ == '__main__':
    main()
