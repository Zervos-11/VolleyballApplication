"""Check static court-image alignment on locally reviewed source frames.

The result is an encoded-image registration diagnostic, not an independent
court-landmark or player-floor accuracy reference.
"""
import hashlib
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_u5HnY2aNW14'
SCREEN = MATCH / 'screening'
REFERENCE_VIDEO = SCREEN / 'clip_4m50.mp4'
SOURCE_VIDEO = MATCH / 'source_720p.mp4'
REFERENCE_TRACKS = SCREEN / 'live_track_screen_300_435.json'
SELECTED = SCREEN / 'bracketed_candidate_source_qc.json'
TRACKS = SCREEN / 'dense_live_track_screen.json'
CALIBRATION = SCREEN / 'near_court_candidate.json'
ZERO_RUN = SCREEN / 'zero_run_source_review/index.json'
OUT = SCREEN / 'selected_camera_registration.json'
REF_FRAME = 360


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_frame(cap, number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
    ok, frame = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
        raise RuntimeError(f'Could not decode exact frame {number}')
    return frame


def features(sift, frame, boxes):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = np.zeros_like(gray)
    # Court floor and printed logo; exclude scoreboard, net/crowd, and people.
    mask[330:700, 120:1170] = 255
    for box in boxes:
        x1, y1, x2, y2 = box['bbox_px']
        xa, ya = max(0, int(x1) - 15), max(0, int(y1) - 15)
        xb, yb = min(gray.shape[1], int(x2) + 15), min(gray.shape[0], int(y2) + 15)
        mask[ya:yb, xa:xb] = 0
    return sift.detectAndCompute(gray, mask)


def register(ref_features, target_features):
    ref_kp, ref_des = ref_features
    tar_kp, tar_des = target_features
    if ref_des is None or tar_des is None:
        return {'status': 'insufficient_features'}
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(ref_des, tar_des, k=2)
    good = [first for first, second in pairs if first.distance < .72 * second.distance]
    if len(good) < 12:
        return {'status': 'insufficient_matches', 'good_matches': len(good)}
    src = np.float32([ref_kp[m.queryIdx].pt for m in good])
    dst = np.float32([tar_kp[m.trainIdx].pt for m in good])
    matrix, inlier_mask = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.0,
        maxIters=10000, confidence=.999)
    if matrix is None:
        return {'status': 'fit_failed', 'good_matches': len(good)}
    inliers = inlier_mask.ravel().astype(bool)
    if int(inliers.sum()) < 12:
        return {'status': 'weak_registration', 'good_matches': len(good),
                'inliers': int(inliers.sum())}
    residuals = np.linalg.norm(src @ matrix[:, :2].T + matrix[:, 2] - dst, axis=1)
    landmarks = np.float64([[239, 648], [1122, 648], [1046, 313], [297, 313],
                            [285, 410], [1060, 410]])
    mapped = landmarks @ matrix[:, :2].T + matrix[:, 2]
    shifts = np.linalg.norm(mapped - landmarks, axis=1)
    scale = math.hypot(matrix[0, 0], matrix[0, 1])
    return {'status': 'registered', 'good_matches': len(good),
            'inliers': int(inliers.sum()),
            'median_inlier_residual_px': round(float(np.median(residuals[inliers])), 3),
            'estimated_static_landmark_shift_px': [round(float(x), 3) for x in shifts],
            'maximum_static_landmark_shift_px': round(float(max(shifts)), 3),
            'image_dx_px': round(float(matrix[0, 2]), 3),
            'image_dy_px': round(float(matrix[1, 2]), 3),
            'image_scale': round(scale, 7),
            'image_rotation_deg': round(math.degrees(math.atan2(matrix[1, 0], matrix[0, 0])), 5),
            'affine_reference_to_target': matrix.tolist()}


def main():
    ref_tracks = json.loads(REFERENCE_TRACKS.read_text(encoding='utf-8'))
    selected = json.loads(SELECTED.read_text(encoding='utf-8'))
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    zero_run = json.loads(ZERO_RUN.read_text(encoding='utf-8'))
    assert ref_tracks['excerpt_sha256'] == sha(REFERENCE_VIDEO) == calibration['excerpt_sha256']
    assert selected['source_sha256'] == tracks['source_sha256'] == sha(SOURCE_VIDEO)
    assert selected['summary']['reviewed_local_frames'] == 15
    assert zero_run['source_sha256'] == selected['source_sha256']
    assert len(zero_run['entries']) == 3
    ref_row = next(row for row in ref_tracks['rows'] if row['excerpt_frame'] == REF_FRAME)
    lookup = {(p['set'], p['point_number'], row['source_frame']): row
              for p in tracks['points'] for row in p['rows']}
    sift = cv2.SIFT_create(nfeatures=4000)
    ref_cap = cv2.VideoCapture(str(REFERENCE_VIDEO))
    source_cap = cv2.VideoCapture(str(SOURCE_VIDEO))
    rows = []
    try:
        reference = read_frame(ref_cap, REF_FRAME)
        ref_features = features(sift, reference, ref_row['near_court_proposals'])
        for item in selected['rows']:
            key = item['set'], item['point_number'], item['source_frame']
            target = read_frame(source_cap, item['source_frame'])
            target_features = features(sift, target, lookup[key]['proposals'])
            result = register(ref_features, target_features)
            rows.append({'set': key[0], 'point_number': key[1], 'source_frame': key[2],
                         'evidence_type': 'source_reviewed_six_detector_boxes',
                         **result})
        for item in zero_run['entries']:
            frames = item['source_frames']
            for frame in [frames[0], frames[len(frames) // 2], frames[-1]]:
                target = read_frame(source_cap, frame)
                # These three points have no six-ID run. Moving players are
                # handled by robust registration, but cannot be box-masked here.
                target_features = features(sift, target, [])
                result = register(ref_features, target_features)
                rows.append({'set': item['set'], 'point_number': item['point_number'],
                             'source_frame': frame, 'evidence_type': 'source_only_no_six_id_run',
                             **result})
    finally:
        ref_cap.release()
        source_cap.release()
    registered = [r for r in rows if r['status'] == 'registered']
    summary = {'reviewed_selected_frames': len(rows), 'frames_registered': len(registered),
               'frozen_points_covered': len({(r['set'], r['point_number']) for r in rows}),
               'maximum_static_landmark_shift_px': max((r['maximum_static_landmark_shift_px']
                                                        for r in registered), default=None),
               'median_static_landmark_shift_px': round(statistics.median(
                   r['maximum_static_landmark_shift_px'] for r in registered), 3) if registered else None}
    OUT.write_text(json.dumps({
        'status': 'static_court_image_registration_not_floor_position_validation',
        'reference_excerpt_frame': REF_FRAME,
        'source_sha256': selected['source_sha256'],
        'input_sha256': {'reference_video': sha(REFERENCE_VIDEO), 'source_video': sha(SOURCE_VIDEO),
                         'reference_tracks': sha(REFERENCE_TRACKS), 'selected_qc': sha(SELECTED),
                         'dense_tracks': sha(TRACKS), 'calibration': sha(CALIBRATION),
                         'zero_run_review': sha(ZERO_RUN)},
        'method': 'SIFT floor features with person masks; ratio-match and RANSAC partial-affine registration. Landmark shifts are model estimates.',
        'summary': summary, 'rows': rows,
        'limitations': ['Partial-affine floor-image registration does not independently measure court-line mapping error.',
                        'The reference frame is from a separately encoded excerpt; offsets may be caused by encoding or crop shifts.',
                        'The nine source-only frames lack detector box masks, so robust matching must reject moving-player features.',
                        'This does not validate player shoe-floor coordinates or airborne states.'],
    }, indent=2) + '\n', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
