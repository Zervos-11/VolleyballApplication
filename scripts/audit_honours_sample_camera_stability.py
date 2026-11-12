"""Check static-background image registration across the frozen sample."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
OUT = ROOT / 'data/processed/honours_camera_stability_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_CAMERA_STABILITY_AUDIT.md'
REFERENCES = {1: 21270, 2: 78261, 3: 78261}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_frame(cap, number):
    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
    ok, frame = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
        raise RuntimeError(f'Could not decode exact frame {number}')
    return frame


def features(detector, frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mask = np.zeros_like(gray)
    # Court-free wall. Excludes score graphics, the net, athletes and floor.
    mask[190:590, 230:1690] = 255
    return detector.detectAndCompute(gray, mask)


def estimate(ref_features, target_features):
    kp1, des1 = ref_features
    kp2, des2 = target_features
    if des1 is None or des2 is None:
        return {'status': 'insufficient_features'}
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    pairs = matcher.knnMatch(des1, des2, k=2)
    good = [a for a, b in pairs if a.distance < .72 * b.distance]
    if len(good) < 12:
        return {'status': 'insufficient_matches', 'good_matches': len(good)}
    src = np.float32([kp1[m.queryIdx].pt for m in good])
    dst = np.float32([kp2[m.trainIdx].pt for m in good])
    mat, inlier_mask = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.5,
        maxIters=10000, confidence=.999)
    if mat is None:
        return {'status': 'fit_failed', 'good_matches': len(good)}
    inliers = inlier_mask.ravel().astype(bool)
    residual = np.linalg.norm((src @ mat[:, :2].T + mat[:, 2]) - dst, axis=1)
    scale = float(np.hypot(mat[0, 0], mat[0, 1]))
    angle = float(np.degrees(np.arctan2(mat[1, 0], mat[0, 0])))
    return {'status': 'registered' if sum(inliers) >= 12 else 'weak_registration',
            'good_matches': len(good), 'inliers': int(sum(inliers)),
            'median_inlier_residual_px': round(float(np.median(residual[inliers])), 3),
            'dx_px': round(float(mat[0, 2]), 3), 'dy_px': round(float(mat[1, 2]), 3),
            'scale': round(scale, 7), 'angle_deg': round(angle, 5),
            'affine_ref_to_target': mat.tolist()}


def main():
    sample, audit, source = read(SAMPLE), read(AUDIT), read(SOURCE)
    video = ROOT / source['video_file']
    if sha(video) != source['sha256'] or audit['source_sha256'] != source['sha256']:
        raise ValueError('Source hash mismatch')
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError('Video unavailable')
    detector = cv2.SIFT_create(nfeatures=2500)
    ref_features = {}
    rows = []
    try:
        for ref in set(REFERENCES.values()):
            ref_features[ref] = features(detector, read_frame(cap, ref))
        for point in audit['points']:
            ref = REFERENCES[point['set']]
            for frame in point['frame_rows']:
                number = frame['frame']
                target = features(detector, read_frame(cap, number))
                registration = estimate(ref_features[ref], target)
                rows.append({'set': point['set'], 'point_number': point['point_number'],
                             'frame': number, 'reference_frame': ref, **registration})
    finally:
        cap.release()
    good = [r for r in rows if r['status'] == 'registered']
    result = {'status': 'static_background_image_registration_not_ground_plane_validation',
              'source_sha256': source['sha256'], 'sample_sha256': sha(SAMPLE),
              'completed_audit_sha256': sha(AUDIT),
              'method': 'SIFT ratio matches and RANSAC partial affine fit on the fixed wall at y=190..589 px, x=230..1689 px.',
              'references': REFERENCES, 'frames_total': len(rows), 'frames_registered': len(good),
              'max_abs_dx_px': max((abs(r['dx_px']) for r in good), default=None),
              'max_abs_dy_px': max((abs(r['dy_px']) for r in good), default=None),
              'rows': rows,
              'limitations': ['Static-wall alignment is not a check of court-line landmark error or foot contact.',
                              'A wall affine transform is an image-alignment diagnostic; it does not establish physical camera motion and must not be applied as a floor homography.',
                              'Set 3 currently borrows the set 2 court transform; inspect its court lines separately.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    summary = []
    for set_number in (1, 2, 3):
        group = [r for r in rows if r['set'] == set_number]
        registered = [r for r in group if r['status'] == 'registered']
        summary.append((set_number, len(registered), len(group),
                        max((abs(r['dx_px']) for r in registered), default=None),
                        max((abs(r['dy_px']) for r in registered), default=None)))
    table = '\n'.join(f'| {s} | {n}/{total} | {dx} | {dy} |' for s, n, total, dx, dy in summary)
    REPORT.write_text(f'''# Court image alignment check

The [source-bound registration record](../data/processed/honours_camera_stability_audit.json) compares the static gym wall in each of the {len(rows)} saved sample frames with a calibration reference frame. It excludes score graphics, players, net and floor from SIFT feature detection and uses a robust partial-affine fit. This measures **image-coordinate alignment**, not physical camera movement, court-line accuracy or shoe-position accuracy.

| Set | Registered frames | Maximum absolute x shift (px) | Maximum absolute y shift (px) |
| ---: | ---: | ---: | ---: |
{table}

Any frame with a weak or failed registration is identified in the JSON and cannot inherit a stability claim. Set 3 currently borrows the set 2 court transform. Court-line checks on exact frames, especially in set 3, are needed before approving any metre coordinate for final metrics.

Set-one point 39 has an approximately 12 px scene offset relative to the earlier set-one reference. An [independent phase-correlation and ECC check](../data/processed/honours_image_alignment_diagnostic/diagnostic.json) finds the same offset. The [direct interleaved source crop](../data/processed/honours_image_alignment_diagnostic/wall_checker_65656.jpg) shows the wall features at different pixel positions. This does not identify the physical cause; a fixed camera and an encoded-image offset are compatible.
''', encoding='utf-8')
    print(f'Registered {len(good)}/{len(rows)} frames; max |dx|={result["max_abs_dx_px"]}, |dy|={result["max_abs_dy_px"]}')


if __name__ == '__main__':
    main()
