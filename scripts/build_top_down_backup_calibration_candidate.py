"""Stage a source-image court-floor homography for the backup excerpt."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'source_screen.json'
CLIP = BASE / 'clip_4m50.mp4'
OUT = BASE / 'near_court_candidate.json'
OVERLAY = BASE / 'near_court_candidate_overlay.jpg'
FRAME = 360
# Manually placed line intersections on decoded excerpt frame 360.
# Image order: near left baseline, near right baseline, right centreline, left centreline.
POINTS_PX = [[239, 648], [1122, 648], [1046, 313], [297, 313]]
POINTS_M = [[0, 0], [9, 0], [9, 9], [0, 9]]
# Independent visible 3 m attack-line intersections with the sidelines.
HELD_OUT_ATTACK_PX = [[285, 410], [1060, 410]]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    if screen['extended_excerpt_sha256'] != sha(CLIP):
        raise ValueError('Extended excerpt hash differs from source screen')
    H = cv2.getPerspectiveTransform(np.asarray(POINTS_PX, np.float32),
                                    np.asarray(POINTS_M, np.float32))
    if not np.isfinite(H).all():
        raise ValueError('Nonfinite court transform')
    held = cv2.perspectiveTransform(np.asarray([HELD_OUT_ATTACK_PX], np.float32), H)[0]
    residual_m = [round(float(abs(p[1] - 6)), 4) for p in held]
    cap = cv2.VideoCapture(str(CLIP))
    cap.set(cv2.CAP_PROP_POS_FRAMES, FRAME)
    ok, image = cap.read()
    decoded = round(cap.get(cv2.CAP_PROP_POS_FRAMES))
    cap.release()
    if not ok or decoded != FRAME + 1:
        raise RuntimeError('Could not decode calibration frame')
    reverse = np.linalg.inv(H)
    for court_y, colour in [(0, (0, 180, 0)), (3, (0, 160, 210)),
                             (6, (255, 0, 0)), (9, (0, 180, 0))]:
        segment = cv2.perspectiveTransform(
            np.asarray([[[0, court_y], [9, court_y]]], np.float32), reverse)[0]
        p1, p2 = [tuple(map(round, point)) for point in segment]
        cv2.line(image, p1, p2, colour, 2)
        cv2.putText(image, f'court y={court_y}m', (p1[0] + 8, p1[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, .55, colour, 2)
    for x, y in HELD_OUT_ATTACK_PX:
        cv2.circle(image, (x, y), 6, (0, 0, 255), -1)
    if not cv2.imwrite(str(OVERLAY), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise RuntimeError('Could not write overlay')
    output = {
        'status': 'staged_floor_line_homography_not_validated_player_positions',
        'video_id': screen['video_id'], 'excerpt_sha256': sha(CLIP),
        'source_frame_within_excerpt': FRAME,
        'coordinate_rule': 'near baseline y=0 m, floor centreline under net y=9 m; x from image left to right',
        'points_px': POINTS_PX, 'points_court_m': POINTS_M,
        'homography_image_to_court': H.tolist(),
        'held_out_attack_line_px': HELD_OUT_ATTACK_PX,
        'held_out_attack_line_projected_m': [[round(float(x), 4), round(float(y), 4)] for x, y in held],
        'held_out_expected_court_y_m': 6,
        'held_out_y_abs_residual_m': residual_m,
        'overlay': str(OVERLAY.relative_to(ROOT)).replace('\\', '/'),
        'use_for_final_metrics': False,
        'limitations': ['Four court corners were placed by one reviewer on one frame.',
                        'Held-out attack-line placements are approximate and not independent inter-observer validation.',
                        'The transform is not a test of grounded player box-bottom accuracy.',
                        'Airborne players and off-court positions must remain separately flagged.']}
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(f'held-out attack-line depth residuals: {residual_m} m')


if __name__ == '__main__':
    main()
