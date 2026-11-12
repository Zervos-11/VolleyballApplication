"""Build source-frame review leads from a rejected jump-bridge trial.

This script never assigns team side. Its output explicitly withholds each
proposed rescue until an independent side decision is recorded.
"""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import cv2


BASE = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial')
TRIAL = BASE / 'team_membership_bridge_trial_v4.json'
SOURCE = Path('data/matches/yt_em6zFUxfYpc/heldout_source_cfr.mp4')
OUT = BASE / 'team_bridge_side_review_queue.json'
SHEETS = BASE / 'side_review_frames'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_frame(video, frame):
    video.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, image = video.read()
    if not ok:
        raise RuntimeError(f'Cannot decode source frame {frame}')
    return image


def panel(image, box, label):
    image = image.copy()
    x1, y1, x2, y2 = (int(round(n)) for n in box)
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 255), 4)
    cv2.putText(image, label, (20, 48), cv2.FONT_HERSHEY_SIMPLEX,
                1.2, (0, 0, 0), 6, cv2.LINE_AA)
    cv2.putText(image, label, (20, 48), cv2.FONT_HERSHEY_SIMPLEX,
                1.2, (255, 255, 255), 2, cv2.LINE_AA)
    height, width = image.shape[:2]
    return cv2.resize(image, (960, round(height * 960 / width)))


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    trial = json.loads(TRIAL.read_text(encoding='utf-8'))
    if trial['source_sha256'] != sha256(SOURCE):
        raise ValueError('Source video changed since bridge trial')
    video = cv2.VideoCapture(str(SOURCE))
    if not video.isOpened():
        raise FileNotFoundError(SOURCE)
    SHEETS.mkdir(parents=True, exist_ok=True)
    leads = []
    try:
        for window, data in trial['windows'].items():
            grouped = defaultdict(list)
            for frame, rows in data['rescued'].items():
                for row in rows:
                    grouped[int(row['track_id'])].append((int(frame), row))
            for track_id, rescues in sorted(grouped.items()):
                rescues.sort(key=lambda item: item[0])
                first_frame, first_row = rescues[0]
                anchor_frame = first_row['last_court_compatible_frame']
                anchors = [event for event in data['diagnostics']['accepted_anchor_events']
                           if event['track_id'] == track_id and event['frame'] <= anchor_frame]
                if not anchors:
                    raise ValueError(f'{window}:{track_id} has no recorded anchor')
                # The rescue records the last anchor frame. Find its accepted box
                # in the frozen input rather than guessing its image location.
                accepted_file = ('data/matches/yt_em6zFUxfYpc/pilot/heldout_team_filtered_predictions.json'
                                 if window.startswith('cross_') else
                                 f'data/processed/heldout_crossing_eval_em6z/frozen_{"jump_segment_150_239" if window.startswith("jump_") else "block_segment_860_960"}.json')
                accepted_data = json.loads(Path(accepted_file).read_text(encoding='utf-8'))
                accepted = (accepted_data['windows'][window]['predictions']
                            if window.startswith('cross_') else
                            accepted_data['court_jersey_predictions'])
                anchor_row = next((row for row in accepted[str(anchor_frame)]
                                   if int(row['track_id']) == track_id), None)
                if anchor_row is None:
                    raise ValueError(f'{window}:{track_id} anchor box absent')
                a = panel(read_frame(video, anchor_frame), anchor_row['bbox'],
                          f'{window} ID {track_id} anchor {anchor_frame}')
                b = panel(read_frame(video, first_frame), first_row['bbox'],
                          f'{window} ID {track_id} proposed {first_frame}')
                sheet = SHEETS / f'{window}_track_{track_id}.jpg'
                if not cv2.imwrite(str(sheet), cv2.hconcat([a, b])):
                    raise RuntimeError(f'Cannot write {sheet}')
                leads.append({
                    'window': window, 'track_id': track_id,
                    'anchor_frame': anchor_frame,
                    'anchor_bottom_range_px': anchors[-1]['bottom_range_px'],
                    'proposed_frames': [frame for frame, _ in rescues],
                    'source_review_image': str(sheet).replace('\\', '/'),
                    'team_status': 'unknown',
                    'proposed_status': 'target_candidate_airborne',
                    'decision': 'requires_source_side_review',
                })
    finally:
        video.release()
    OUT.write_text(json.dumps({
        'status': 'review_only', 'source_sha256': sha256(SOURCE),
        'trial_sha256': sha256(TRIAL),
        'policy': 'No team status is promoted from this queue without a separate side decision.',
        'leads': leads,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'{len(leads)} track leads, {sum(len(x["proposed_frames"]) for x in leads)} proposed boxes')


if __name__ == '__main__':
    main()
