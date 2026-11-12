"""Make an unreviewed 50-frame source-image draft from visual anchors.

This fills gaps between manually inspected anchor frames for review navigation.
It does not create independent labels or estimate court positions.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_AoEP-YiWRvc/source_AoEP-YiWRvc.mp4'
ANCHORS = ROOT / 'data/processed/aoep_new_source/visual_anchors_75180_75229.json'
CONTACT = ROOT / 'data/processed/aoep_new_source/setter_contact_candidate.json'
OUT = ROOT / 'data/processed/aoep_new_source/anchor_interpolation_75180_75229'
FIRST, LAST = 75180, 75229
PLAYER_COLORS = [(20, 200, 255), (0, 150, 255), (0, 220, 0),
                 (255, 160, 0), (255, 80, 80), (220, 0, 255)]


def interpolate_box(before, after, fraction):
    return [round(a + fraction * (b - a)) for a, b in zip(before, after)]


def proposal(frame, player_id, frame_rows):
    if frame in frame_rows:
        source = frame_rows[frame]
        return {'bbox_source_px': source['bbox_source_px'],
                'visibility': source['visibility'],
                'draft_status': 'source_visual_anchor_development'}
    before = max(f for f in frame_rows if f < frame)
    after = min(f for f in frame_rows if f > frame)
    left, right = frame_rows[before], frame_rows[after]
    box_a, box_b = left['bbox_source_px'], right['bbox_source_px']
    if box_a is None and box_b is None:
        return {'bbox_source_px': None, 'visibility': 'out_of_frame',
                'draft_status': 'interpolated_absence_unreviewed'}
    if box_a is None or box_b is None:
        return {'bbox_source_px': None, 'visibility': 'unknown_edge_transition',
                'draft_status': 'requires_source_frame_review'}
    fraction = (frame - before) / (after - before)
    visibility = ('partially_occluded_or_truncated'
                  if player_id == 'yellow_centre_left' and frame >= 75201
                  else 'unknown_interpolated')
    return {'bbox_source_px': interpolate_box(box_a, box_b, fraction),
            'visibility': visibility,
            'draft_status': 'interpolated_unreviewed'}


def court_position_status(frame, player_id, contact):
    if player_id != contact['visual_player_id']:
        return 'not_estimated'
    for observation in contact['observations']:
        first, last = observation['frames_inclusive']
        if first <= frame <= last:
            return observation['court_position_status']
    return 'not_estimated'


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    anchors = json.loads(ANCHORS.read_text(encoding='utf-8'))
    contact = json.loads(CONTACT.read_text(encoding='utf-8'))
    if anchors['source_sha256'] != hashlib.sha256(VIDEO.read_bytes()).hexdigest():
        raise ValueError('Source video differs from visual anchors')
    if contact['source_sha256'] != anchors['source_sha256']:
        raise ValueError('Contact cue uses a different source')
    by_player = {player_id: {} for player_id in anchors['player_descriptions']}
    for frame, rows in anchors['frames'].items():
        for row in rows:
            by_player[row['visual_player_id']][int(frame)] = row
    OUT.mkdir(parents=True)
    video = cv2.VideoCapture(str(VIDEO))
    if not video.isOpened():
        raise FileNotFoundError(VIDEO)
    video.set(cv2.CAP_PROP_POS_FRAMES, FIRST)
    frames = {}
    previews = []
    statuses = Counter()
    try:
        for frame in range(FIRST, LAST + 1):
            ok, image = video.read()
            if not ok:
                raise RuntimeError(f'Cannot decode frame {frame}')
            preview = image.copy()
            rows = []
            for index, player_id in enumerate(by_player):
                row = {'visual_player_id': player_id,
                       **proposal(frame, player_id, by_player[player_id]),
                       'court_position_status': court_position_status(frame, player_id, contact)}
                rows.append(row)
                statuses[row['draft_status']] += 1
                box = row['bbox_source_px']
                if box is None:
                    continue
                x1, y1, x2, y2 = box
                color = PLAYER_COLORS[index]
                cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
                label = f'{index + 1}:{"A" if row["draft_status"] == "source_visual_anchor_development" else "?"}'
                cv2.putText(preview, label, (x1, max(20, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 0), 3)
                cv2.putText(preview, label, (x1, max(20, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1)
            cv2.putText(preview, str(frame), (30, 52), cv2.FONT_HERSHEY_SIMPLEX,
                        1.1, (0, 0, 0), 4)
            cv2.putText(preview, str(frame), (30, 52), cv2.FONT_HERSHEY_SIMPLEX,
                        1.1, (255, 255, 255), 2)
            frames[str(frame)] = rows
            previews.append(cv2.resize(preview, (960, 540)))
    finally:
        video.release()
    for chunk in range(10):
        path = OUT / f'check_{chunk + 1:02d}.jpg'
        if not cv2.imwrite(str(path), cv2.vconcat(previews[chunk * 5:(chunk + 1) * 5])):
            raise OSError(path)
    priority = {
        'edge_entry_first_visibility': list(range(75191, 75201)),
        'centre_left_partial_overlap': list(range(75201, 75230)),
        'setter_rapid_vertical_motion': list(range(75180, 75211)),
    }
    payload = {
        'status': 'source_image_interpolation_draft_unreviewed',
        'source_sha256': anchors['source_sha256'],
        'visual_anchors_sha256': hashlib.sha256(ANCHORS.read_bytes()).hexdigest(),
        'setter_contact_candidate_sha256': hashlib.sha256(CONTACT.read_bytes()).hexdigest(),
        'frame_range_inclusive': [FIRST, LAST],
        'player_descriptions': anchors['player_descriptions'],
        'method': 'Linear image-box interpolation between six source-visual development anchors. Transitions from out of frame to visible have no invented box. No detector boxes were used for interpolation.',
        'limitations': 'No interpolated box has been checked on its own source frame. The centre-left player is partly hidden; the right entrant first appears between anchors; the setter jumps. Do not import as ground truth, report accuracy, or infer court positions.',
        'draft_status_counts': dict(statuses),
        'review_priority_frames': priority,
        'frames': frames,
    }
    (OUT / 'draft.json').write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print('Draft rows:', sum(statuses.values()), dict(statuses))


if __name__ == '__main__':
    main()
