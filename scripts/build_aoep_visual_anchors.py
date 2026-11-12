"""Record source-frame visual anchors for the AoEP dense slice.

Boxes were drawn from unmarked source frames and centre/right crops. They are
development review anchors, not exhaustive independent ground truth.
"""

import hashlib
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4'
OUT = ROOT / 'data/processed/aoep_new_source/visual_anchors_75180_75229.json'
FRAMES = (75180, 75190, 75200, 75210, 75220, 75229)
PLAYERS = {
    'yellow_left_5': 'Left yellow player with visible jersey 5',
    'yellow_centre_left': 'Yellow player immediately left of jersey 4; jersey number unclear',
    'yellow_centre_4': 'Near-side yellow jersey 4',
    'yellow_setter_18': 'Near-side yellow jersey 18 at the set',
    'navy_libero_10': 'Near-side navy jersey 10',
    'yellow_right_entrant': 'Yellow player entering from the right edge; number unclear',
}
# Source-image pixels [x1,y1,x2,y2]. None means outside the source frame.
BOXES = {
    75180: [[134, 275, 245, 500], [511, 283, 584, 461], [575, 289, 667, 529],
            [719, 228, 807, 465], [848, 311, 970, 534], None],
    75190: [[137, 270, 275, 490], [515, 279, 594, 460], [576, 285, 665, 527],
            [732, 215, 817, 469], [884, 311, 999, 524], None],
    75200: [[137, 286, 270, 494], [548, 281, 622, 455], [578, 288, 663, 528],
            [722, 238, 814, 474], [919, 314, 1005, 520], [1243, 284, 1280, 421]],
    75210: [[172, 287, 272, 477], [561, 282, 637, 451], [577, 286, 670, 520],
            [729, 244, 814, 480], [936, 300, 1010, 490], [1209, 286, 1280, 479]],
    75220: [[183, 282, 296, 477], [626, 279, 708, 438], [577, 299, 696, 520],
            [727, 258, 809, 481], [935, 301, 1023, 484], [1147, 281, 1280, 461]],
    75229: [[207, 284, 314, 469], [650, 281, 730, 434], [577, 297, 708, 524],
            [727, 257, 819, 480], [932, 302, 1009, 473], [1117, 281, 1254, 458]],
}
PARTIAL = {
    (75200, 'yellow_right_entrant'),
    (75210, 'yellow_right_entrant'),
    (75210, 'yellow_centre_left'),
    (75220, 'yellow_centre_left'),
    (75229, 'yellow_centre_left'),
}


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    frames = {}
    try:
        for frame in FRAMES:
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(frame)
            preview = image.copy()
            rows = []
            for (player_id, description), box in zip(PLAYERS.items(), BOXES[frame]):
                state = ('out_of_frame' if box is None else
                         'partially_occluded_or_truncated' if (frame, player_id) in PARTIAL else
                         'visible')
                rows.append({'visual_player_id': player_id, 'bbox_source_px': box,
                             'visibility': state})
                if box is not None:
                    x1, y1, x2, y2 = box
                    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 220, 255), 2)
                    cv2.putText(preview, player_id, (x1, max(20, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .43, (0, 0, 0), 3)
                    cv2.putText(preview, player_id, (x1, max(20, y1 - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, .43, (0, 220, 255), 1)
            frames[str(frame)] = rows
            path = OUT.parent / f'visual_anchors_{frame}.jpg'
            if path.exists() or not cv2.imwrite(str(path), preview):
                raise OSError(path)
    finally:
        video.release()
    payload = {
        'status': 'source_visual_development_anchors_not_ground_truth',
        'source_sha256': hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
        'method': 'Visual boxes and visibility from unmarked source frames/crops. Prior tracker diagnostics were seen, so these anchors are not independent evaluation labels. Boxes are approximate and six sampled frames are not a dense 50-frame annotation.',
        'player_descriptions': PLAYERS,
        'frames': frames,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(frames)} source-frame anchors')


if __name__ == '__main__':
    main()
