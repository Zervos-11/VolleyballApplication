"""Exploratory near-team continuity on frozen AoEP detections.

Only six visually checked boxes at frame 74970 seed this pass. Raw tracker IDs
are followed while image motion and shirt appearance remain continuous; no new
identity is assigned after a break. This is not a team classifier or metric.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from audit_aoep_candidate_gate import category
from evaluate_team_appearance import torso_histogram


ROOT = Path(__file__).resolve().parents[1]
MATCH = ROOT / 'data/matches/yt_AoEP-YiWRvc'
VIDEO = MATCH / 'source_AoEP-YiWRvc.mp4'
RAW = ROOT / 'data/processed/aoep_new_source/raw_74880_75540.json'
CALIBRATION = MATCH / 'pilot/calibration/near_court_candidate.json'
OUT = ROOT / 'data/processed/aoep_new_source/temporal_team_candidate.json'
FIRST, LAST = 74970, 75320
SEED_IDS = (1, 2, 3, 5, 8, 131)
MAX_GAP = 6
MAX_STEP_HEIGHT_FRACTION = .25
MAX_HIST_DISTANCE = .60
MAX_ANCHOR_AGE = 30


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def continuous(previous, frame, box, hist):
    gap = frame - previous['frame']
    old = previous['box']
    height = old[3] - old[1]
    old_centre = ((old[0] + old[2]) / 2, (old[1] + old[3]) / 2)
    new_centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
    return (1 <= gap <= MAX_GAP and height > 0 and
            abs(new_centre[0] - old_centre[0]) <= MAX_STEP_HEIGHT_FRACTION * height * min(gap, 2) and
            abs(new_centre[1] - old_centre[1]) <= MAX_STEP_HEIGHT_FRACTION * height * min(gap, 2) and
            cv2.compareHist(hist, previous['hist'], cv2.HISTCMP_BHATTACHARYYA) <= MAX_HIST_DISTANCE)


def team_status(region, frame, box, anchor):
    if region == 'strict_near_region':
        return 'near_candidate_in_region'
    if region == 'boundary_band_unresolved':
        return 'near_candidate_boundary'
    if region == 'beyond_projected_net_unresolved' and anchor is not None:
        age = frame - anchor['frame']
        height = anchor['box'][3] - anchor['box'][1]
        rise = anchor['box'][3] - box[3]
        if (0 <= age <= MAX_ANCHOR_AGE and height > 0 and
                rise >= .03 * height and box[3] - box[1] >= .70 * height):
            return 'near_candidate_airborne_image_only'
    return 'unknown'


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(VIDEO) or calibration['use_for_metrics'] is not False:
        raise ValueError('Source mismatch or unexpectedly approved calibration')
    matrix = cv2.getPerspectiveTransform(np.asarray(calibration['points_px'], np.float32),
                                         np.asarray(calibration['points_court_m'], np.float32))
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    video.set(cv2.CAP_PROP_POS_FRAMES, FIRST)
    states = {}
    stopped = {}
    results = {}
    totals = Counter()
    try:
        for frame in range(FIRST, LAST + 1):
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode source frame {frame}')
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            source_rows = raw['predictions'][str(frame)]
            by_id = {int(row['track_id']): row for row in source_rows if int(row['track_id']) in SEED_IDS}
            output_rows = []
            for track_id in SEED_IDS:
                if track_id in stopped:
                    continue
                row = by_id.get(track_id)
                previous = states.get(track_id)
                if row is None:
                    if previous is not None and frame - previous['frame'] > MAX_GAP:
                        stopped[track_id] = {'frame': frame, 'reason': 'tracker_gap'}
                    continue
                box = row['bbox']
                appearance = torso_histogram(hsv, box)
                if appearance is None:
                    stopped[track_id] = {'frame': frame, 'reason': 'no_torso_appearance'}
                    continue
                hist = appearance[0]
                if frame != FIRST and (previous is None or not continuous(previous, frame, box, hist)):
                    stopped[track_id] = {'frame': frame, 'reason': 'image_or_appearance_discontinuity'}
                    continue
                foot = np.asarray([[[(box[0] + box[2]) / 2, box[3]]]], np.float32)
                x, y = cv2.perspectiveTransform(foot, matrix)[0][0]
                region = category(float(x), float(y))
                anchor = previous['anchor'] if previous else None
                if region == 'strict_near_region':
                    anchor = {'frame': frame, 'box': box}
                status = team_status(region, frame, box, anchor)
                # The visually checked seed is near-side even if its box bottom
                # is outside the candidate polygon. This does not infer a floor point.
                if frame == FIRST:
                    status = 'near_candidate_visual_seed'
                states[track_id] = {'frame': frame, 'box': box, 'hist': hist, 'anchor': anchor}
                output_rows.append({'track_id': track_id, 'bbox': box,
                                    'team_status': status,
                                    'region_diagnostic': region,
                                    'court_position_status': 'unknown_airborne' if 'airborne' in status else 'not_estimated'})
                totals[status] += 1
            results[str(frame)] = output_rows
    finally:
        video.release()
    payload = {
        'status': 'exploratory_candidate_not_ground_truth',
        'source_sha256': sha256(VIDEO), 'raw_sha256': sha256(RAW),
        'calibration_candidate_sha256': sha256(CALIBRATION),
        'frame_range_inclusive': [FIRST, LAST],
        'seed': {'frame': FIRST, 'raw_track_ids': list(SEED_IDS),
                 'basis': 'source-frame visual inspection of six near-side boxes; IDs are raw tracker labels, not verified player identities'},
        'thresholds': {'max_gap_frames': MAX_GAP,
                       'max_step_fraction_of_prior_box_height': MAX_STEP_HEIGHT_FRACTION,
                       'max_torso_histogram_distance': MAX_HIST_DISTANCE,
                       'max_airborne_anchor_age_frames': MAX_ANCHOR_AGE},
        'interpretation': 'Rows absent from this seeded pass remain unresolved, not far-team. Same-ID path stops on a gap or appearance/motion break; no ID switch is bridged. Airborne status does not supply a court position. Candidate homography is unverified.',
        'totals': dict(totals), 'stopped_seed_tracks': stopped,
        'tracked_seed_rows_by_frame': results,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    video = cv2.VideoCapture(str(VIDEO))
    try:
        for frame in (74970, 75180, 75280):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode review frame {frame}')
            raw_rows = raw['predictions'][str(frame)]
            tracked = {r['track_id']: r for r in results[str(frame)]}
            for row in raw_rows:
                box = row['bbox']
                track_id = int(row['track_id'])
                status = tracked.get(track_id, {}).get('team_status', 'unresolved')
                color = ((20, 210, 20) if status.startswith('near_candidate') else
                         (0, 180, 255) if status == 'unknown' else (120, 120, 120))
                x1, y1, x2, y2 = [int(round(v)) for v in box]
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                label = f'{track_id}:{status.replace("near_candidate_", "")}'
                cv2.putText(image, label, (x1, max(20, y1 - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX, .42, color, 1, cv2.LINE_AA)
            path = OUT.parent / f'temporal_team_candidate_{frame}.jpg'
            if path.exists() or not cv2.imwrite(str(path), image):
                raise OSError(path)
    finally:
        video.release()
    print('Candidate rows:', sum(totals.values()), dict(totals))
    print('Stopped:', stopped)


if __name__ == '__main__':
    main()
