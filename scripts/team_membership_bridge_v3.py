"""Experimental team-membership continuity across a short detector gap.

The bridge carries only a near-team candidate state. It never emits a court
position for a box that fails the court gate and never creates a missing box.
"""

from dataclasses import dataclass

import cv2

from evaluate_pilot_tracker import in_target_region, project
from evaluate_team_appearance import THRESHOLD, torso_histogram


MAX_GAP_FRAMES = 6
MAX_ANCHOR_AGE_FRAMES = 30
MAX_STEP_HEIGHT_FRACTION = .25
MIN_RISE_HEIGHT_FRACTION = .03
MIN_HEIGHT_RATIO = .70
MIN_OUTSIDE_NET_Y_M = 9.5


@dataclass
class State:
    last_frame: int
    last_box: list
    last_hist: object
    accepted_run: int
    anchor_frame: int | None
    anchor_box: list | None


def _centre(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def _continuous(state, frame, box, hist):
    gap = frame - state.last_frame
    if not 1 <= gap <= MAX_GAP_FRAMES:
        return False
    height = state.last_box[3] - state.last_box[1]
    old_x, old_y = _centre(state.last_box)
    new_x, new_y = _centre(box)
    return (height > 0 and
            abs(new_x - old_x) <= MAX_STEP_HEIGHT_FRACTION * height * min(gap, 2) and
            abs(new_y - old_y) <= MAX_STEP_HEIGHT_FRACTION * height * min(gap, 2) and
            cv2.compareHist(hist, state.last_hist,
                            cv2.HISTCMP_BHATTACHARYYA) <= THRESHOLD)


def bridge_window(video, raw, accepted, matrix, first, last):
    states = {}
    pending = {}
    active = set()
    rescued = {str(frame): [] for frame in range(first, last + 1)}
    diagnostics = {'accepted_anchor_events': [], 'rescued': []}
    for frame in range(first, last + 1):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = video.read()
        if not ok:
            raise RuntimeError(f'Cannot decode frame {frame}')
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        key = str(frame)
        accepted_by_id = {int(row['track_id']): row for row in accepted[key]}
        for track_id, row in accepted_by_id.items():
            box = row['bbox']
            xy = project([(box[0] + box[2]) / 2, box[3]], matrix)
            appearance = torso_histogram(hsv, box)
            if appearance is None:
                states.pop(track_id, None)
                pending.pop(track_id, None)
                active.discard(track_id)
                continue
            hist = appearance[0]
            previous = states.get(track_id)
            continuous = previous is not None and _continuous(previous, frame, box, hist)
            strict_court = (0 <= float(xy[1]) <= 9.5 and
                            -1.5 <= float(xy[0]) <= 10.5)
            if strict_court and continuous:
                run = previous.accepted_run + 1
            elif strict_court:
                run = 1
            else:
                run = 0
            if run >= 2:
                anchor_frame, anchor_box = frame, box
                if run == 2:
                    diagnostics['accepted_anchor_events'].append(
                        {'frame': frame, 'track_id': track_id})
            elif continuous and previous.anchor_frame is not None:
                # A padded-court acceptance maintains the image path only.
                anchor_frame, anchor_box = previous.anchor_frame, previous.anchor_box
            else:
                anchor_frame, anchor_box = None, None
            states[track_id] = State(frame, box, hist, run, anchor_frame, anchor_box)
            pending.pop(track_id, None)
            active.discard(track_id)

        for row in raw[key]:
            track_id = int(row['track_id'])
            if track_id in accepted_by_id or track_id not in states:
                continue
            state = states[track_id]
            if state.anchor_frame is None or frame - state.anchor_frame > MAX_ANCHOR_AGE_FRAMES:
                continue
            box = row['bbox']
            xy = project([(box[0] + box[2]) / 2, box[3]], matrix)
            if in_target_region(xy, False) or float(xy[1]) < MIN_OUTSIDE_NET_Y_M:
                continue
            anchor_height = state.anchor_box[3] - state.anchor_box[1]
            if (anchor_height <= 0 or
                    state.anchor_box[3] - box[3] < MIN_RISE_HEIGHT_FRACTION * anchor_height or
                    box[3] - box[1] < MIN_HEIGHT_RATIO * anchor_height):
                pending.pop(track_id, None)
                active.discard(track_id)
                continue
            appearance = torso_histogram(hsv, box)
            if appearance is None or not _continuous(state, frame, box, appearance[0]):
                pending.pop(track_id, None)
                active.discard(track_id)
                continue
            if track_id in active:
                enriched = {**row, 'team_status': 'target_candidate_airborne',
                            'court_position_status': 'unknown_airborne',
                            'last_court_compatible_frame': state.anchor_frame}
                rescued[key].append(enriched)
                diagnostics['rescued'].append({'frame': frame, 'track_id': track_id,
                                               'anchor_frame': state.anchor_frame})
                states[track_id] = State(frame, box, appearance[0], 0,
                                         state.anchor_frame, state.anchor_box)
                continue
            previous_pending = pending.get(track_id)
            if previous_pending is None:
                pending[track_id] = (frame, row)
                states[track_id] = State(frame, box, appearance[0], 0,
                                         state.anchor_frame, state.anchor_box)
                continue
            pending_frame, pending_row = previous_pending
            if frame - pending_frame > MAX_GAP_FRAMES:
                pending[track_id] = (frame, row)
                states[track_id] = State(frame, box, appearance[0], 0,
                                         state.anchor_frame, state.anchor_box)
                continue
            for rescue_frame, rescue_row in ((pending_frame, pending_row), (frame, row)):
                enriched = {**rescue_row,
                            'team_status': 'target_candidate_airborne',
                            'court_position_status': 'unknown_airborne',
                            'last_court_compatible_frame': state.anchor_frame}
                rescued[str(rescue_frame)].append(enriched)
                diagnostics['rescued'].append({'frame': rescue_frame,
                                               'track_id': track_id,
                                               'anchor_frame': state.anchor_frame})
            pending.pop(track_id, None)
            active.add(track_id)
            states[track_id] = State(frame, box, appearance[0], 0,
                                     state.anchor_frame, state.anchor_box)
    diagnostics['rescued_count'] = len(diagnostics['rescued'])
    return rescued, diagnostics
