"""Audit short raw-ID handoffs from the AoEP near-side visual seeds.

This writes review candidates and rejection reasons only. It never relabels a
raw box or propagates a team/player identity to another tracker ID.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from evaluate_team_appearance import torso_histogram


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
RAW = DIR / 'raw_74880_75540.json'
SEEDS = DIR / 'temporal_team_candidate.json'
VIDEO = ROOT / 'data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4'
OUT = DIR / 'id_handoff_audit.json'
MAX_HANDOFF_GAP = 12
MAX_CENTRE_DISTANCE_HEIGHTS = .65
MAX_HIST_DISTANCE = .60
MAX_HUE_DISTANCE = 25
MIN_SEED_SATURATION = 55


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_distance(old, new):
    a, b = old['bbox'], new['bbox']
    height = a[3] - a[1]
    if height <= 0:
        return float('inf'), float('inf')
    ac = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
    bc = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    distance = np.hypot(ac[0] - bc[0], ac[1] - bc[1]) / height
    ratio = (b[3] - b[1]) / height
    return float(distance), float(ratio)


def hue_distance(a, b):
    difference = abs(float(a) - float(b))
    return min(difference, 180 - difference)


def decision(source_status, source_seed_median, source_end_median,
             destination_median, gap, centre_distance, height_ratio,
             histogram_distance):
    reasons = []
    if not source_status.startswith('near_candidate'):
        reasons.append('source_team_status_unknown')
    if not 1 <= gap <= MAX_HANDOFF_GAP:
        reasons.append('gap_too_long')
    if centre_distance > MAX_CENTRE_DISTANCE_HEIGHTS or not .65 <= height_ratio <= 1.5:
        reasons.append('image_motion_or_scale_mismatch')
    if histogram_distance > MAX_HIST_DISTANCE:
        reasons.append('torso_histogram_mismatch')
    if source_seed_median[1] >= MIN_SEED_SATURATION:
        if hue_distance(source_seed_median[0], source_end_median[0]) > MAX_HUE_DISTANCE:
            reasons.append('source_jersey_unstable')
        if (destination_median[1] < MIN_SEED_SATURATION or
                hue_distance(source_seed_median[0], destination_median[0]) > MAX_HUE_DISTANCE):
            reasons.append('destination_jersey_mismatch')
    return reasons


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    seeded = json.loads(SEEDS.read_text(encoding='utf-8'))
    if raw['source_sha256'] != sha256(VIDEO) or seeded['raw_sha256'] != sha256(RAW):
        raise ValueError('Frozen source/prediction mismatch')
    first, last = seeded['frame_range_inclusive']
    starts = defaultdict(list)
    last_seen = {}
    for frame in range(first, last + 1):
        for row in raw['predictions'][str(frame)]:
            track_id = int(row['track_id'])
            if track_id not in last_seen or frame - last_seen[track_id] > 6:
                starts[frame].append(row)
            last_seen[track_id] = frame
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    cache = {}

    def appearance(frame, box):
        if frame not in cache:
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            cache[frame] = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        return torso_histogram(cache[frame], box)

    events = []
    try:
        for seed_id, stop in seeded['stopped_seed_tracks'].items():
            seed_id = int(seed_id)
            history = [(int(frame), row)
                       for frame, rows in seeded['tracked_seed_rows_by_frame'].items()
                       for row in rows if int(row['track_id']) == seed_id]
            end_frame, end_row = history[-1]
            seed_frame, seed_row = history[0]
            seed_appearance = appearance(seed_frame, seed_row['bbox'])
            end_appearance = appearance(end_frame, end_row['bbox'])
            candidates = []
            for frame in range(end_frame + 1, min(last, end_frame + MAX_HANDOFF_GAP) + 1):
                for row in starts[frame]:
                    if int(row['track_id']) == seed_id:
                        continue
                    distance, ratio = image_distance(end_row, row)
                    if distance > 1.0:
                        continue
                    dest_appearance = appearance(frame, row['bbox'])
                    if dest_appearance is None or end_appearance is None or seed_appearance is None:
                        continue
                    hist_distance = cv2.compareHist(end_appearance[0], dest_appearance[0],
                                                    cv2.HISTCMP_BHATTACHARYYA)
                    reasons = decision(end_row['team_status'], seed_appearance[1],
                                       end_appearance[1], dest_appearance[1],
                                       frame - end_frame, distance, ratio, hist_distance)
                    candidates.append({
                        'destination_raw_track_id': int(row['track_id']),
                        'destination_start_frame': frame,
                        'centre_distance_prior_box_heights': round(distance, 3),
                        'height_ratio': round(ratio, 3),
                        'torso_histogram_distance': round(hist_distance, 3),
                        'stable_seed_hsv_median': seed_appearance[1].tolist(),
                        'endpoint_hsv_median': end_appearance[1].tolist(),
                        'destination_hsv_median': dest_appearance[1].tolist(),
                        'rejection_reasons': reasons,
                    })
            eligible = [r for r in candidates if not r['rejection_reasons']]
            events.append({
                'source_raw_track_id': seed_id, 'last_tracked_frame': end_frame,
                'source_status_at_endpoint': end_row['team_status'],
                'stop_event': stop, 'candidate_count': len(candidates),
                'handoff_review_status': ('ambiguous_multiple_candidates' if len(eligible) > 1 else
                                          'single_candidate_needs_visual_review' if eligible else
                                          'no_supported_handoff'),
                'candidate_starts': candidates,
            })
    finally:
        video.release()
    payload = {
        'status': 'handoff_diagnostic_no_identity_assignments',
        'source_sha256': sha256(VIDEO), 'raw_sha256': sha256(RAW),
        'seeded_diagnostic_sha256': sha256(SEEDS),
        'thresholds': {'max_gap_frames': MAX_HANDOFF_GAP,
                       'max_centre_distance_prior_box_heights': MAX_CENTRE_DISTANCE_HEIGHTS,
                       'height_ratio_range': [.65, 1.5],
                       'max_torso_histogram_distance': MAX_HIST_DISTANCE,
                       'max_saturated_jersey_hue_distance': MAX_HUE_DISTANCE},
        'interpretation': 'A single passing edge is only a review proposal, not an identity match. Nearby detections already active before a source disappears are excluded, and long gaps remain unresolved. No team label is transferred.',
        'events': events,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    for event in events:
        print(event['source_raw_track_id'], event['handoff_review_status'],
              [(r['destination_raw_track_id'], r['rejection_reasons'])
               for r in event['candidate_starts']])


if __name__ == '__main__':
    main()
