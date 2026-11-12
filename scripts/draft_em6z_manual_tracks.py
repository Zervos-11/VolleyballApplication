"""Propagate hand-drawn boxes with OpenCV MIL for visual checking only.

This script deliberately does not read detector or ByteTrack predictions. Its
output is a draft, not evaluation ground truth, until each frame is checked.
"""

import json
from pathlib import Path

import cv2


MATCH = Path('data/matches/yt_em6zFUxfYpc')
VIDEO = MATCH / 'heldout_source_cfr.mp4'
WINDOWS = {
    'cross_a': (243, 267, {
        'near_1': [305, 577, 437, 827],
        'near_2': [784, 635, 979, 874],
        'near_3': [937, 617, 1015, 825],
        'near_4': [1006, 604, 1092, 817],
        'near_5': [1150, 619, 1270, 835],
        'near_6': [1368, 465, 1500, 680],
    }),
    'cross_b': (754, 778, {
        'near_1': [493, 538, 651, 896],
        'near_2': [760, 595, 844, 809],
        'near_3': [791, 577, 911, 811],
        'near_4': [945, 534, 1114, 973],
        'near_5': [1154, 575, 1245, 803],
        'near_6': [1170, 583, 1320, 877],
    }),
}


def main():
    for name, (first, last, seeds) in WINDOWS.items():
        cap = cv2.VideoCapture(str(VIDEO))
        cap.set(cv2.CAP_PROP_POS_FRAMES, first)
        ok, image = cap.read()
        if not ok:
            raise RuntimeError(f'Cannot decode {first}')
        trackers = {}
        for player_id, (x1, y1, x2, y2) in seeds.items():
            tracker = cv2.TrackerMIL_create()
            tracker.init(image, (x1, y1, x2 - x1, y2 - y1))
            trackers[player_id] = tracker
        positions = {str(first): seeds}
        images = {first: image.copy()}
        for frame in range(first + 1, last + 1):
            ok, image = cap.read()
            if not ok:
                raise RuntimeError(f'Cannot decode {frame}')
            boxes = {}
            for player_id, tracker in trackers.items():
                found, (x, y, w, h) = tracker.update(image)
                boxes[player_id] = ([int(x), int(y), int(x + w), int(y + h)]
                                    if found else None)
            positions[str(frame)] = boxes
            if frame in (first + 6, first + 12, first + 18, last):
                images[frame] = image.copy()
        cap.release()
        output = MATCH / 'pilot' / f'{name}_mil_draft.json'
        output.write_text(json.dumps(positions, indent=2) + '\n', encoding='utf-8')
        previews = []
        for frame, image in images.items():
            for player_id, box in positions[str(frame)].items():
                if box is None:
                    continue
                x1, y1, x2, y2 = box
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 255), 3)
                cv2.putText(image, player_id, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(image, str(frame), (20, 80), cv2.FONT_HERSHEY_SIMPLEX,
                        2, (0, 255, 255), 4)
            previews.append(cv2.resize(image, (960, 540)))
        sheet = cv2.vconcat(previews)
        cv2.imwrite(str(MATCH / 'pilot' / f'{name}_mil_preview.jpg'), sheet)
        for chunk in range(5):
            rows = []
            for frame in range(first + chunk * 5, first + (chunk + 1) * 5):
                cap = cv2.VideoCapture(str(VIDEO))
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, image = cap.read()
                cap.release()
                if not ok:
                    raise RuntimeError(f'Cannot decode {frame}')
                image = image[440:990, 250:1550].copy()
                for player_id, box in positions[str(frame)].items():
                    if box is None:
                        continue
                    x1, y1, x2, y2 = box
                    cv2.rectangle(image, (x1 - 250, y1 - 440),
                                  (x2 - 250, y2 - 440), (0, 255, 255), 3)
                    cv2.putText(image, player_id, (x1 - 250, y1 - 448),
                                cv2.FONT_HERSHEY_SIMPLEX, .9, (0, 255, 255), 2)
                cv2.putText(image, str(frame), (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                rows.append(cv2.resize(image, (1000, 423)))
            cv2.imwrite(str(MATCH / 'pilot' / f'{name}_mil_check_{chunk+1}.jpg'),
                        cv2.vconcat(rows))
        print(f'{name}: {len(positions)} draft frames, {sum(sum(b is None for b in boxes.values()) for boxes in positions.values())} lost boxes')


if __name__ == '__main__':
    main()
