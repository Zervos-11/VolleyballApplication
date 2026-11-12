"""Experimental v2: keep image continuity through padded-court acceptances.

The court projection of a person box bottom is invalid while their feet are
airborne. This filter keeps a raw detection only when the same tracker ID was
recently accepted by the court gate, its box rises, and its image motion and
torso appearance remain consistent. A strict-court box anchors the putative
floor position. Padded-court boxes refresh only the image track; the floor
anchor is left stale because they do not establish ground contact.
"""

from dataclasses import dataclass

import cv2

from evaluate_pilot_tracker import in_target_region, project
from evaluate_team_appearance import THRESHOLD, torso_histogram


MAX_GRACE_SECONDS = 0.5
MAX_MISSING_FRAMES = 3
MIN_RISE_FRACTION = 0.03
MIN_CONFIRMED_RISE_FRACTION = 0.08
MIN_HEIGHT_RATIO = 0.70
MAX_STEP_FRACTION = 0.25
MIN_ANCHOR_NET_DISTANCE_M = 6.0
MIN_OUTSIDE_NET_POSITION_M = 9.5
BLUE_HUE_RANGE = (90, 120)
MIN_BLUE_SATURATION = 100
MIN_BLUE_VALUE = 75


@dataclass
class TrackState:
    last_frame: int
    last_box: list
    last_hist: object
    anchor_frame: int
    anchor_box: list
    anchor_position: list


def _centre(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def filter_window(video, raw, accepted, matrix, first, last, fps):
    """Return filtered predictions and diagnostics without consulting labels.

    The existing court + jersey result supplies court-compatible anchors. Rescued
    boxes can extend an anchor but cannot create one or change tracker IDs.
    """
    states = {}
    pending = {}
    active_grace = set()
    output = {}
    rescued = []
    max_grace_frames = round(MAX_GRACE_SECONDS * fps)
    for frame in range(first, last + 1):
        video.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = video.read()
        if not ok:
            raise RuntimeError(f"Cannot decode frame {frame}")
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        key = str(frame)
        kept = list(accepted[key])
        accepted_keys = {(row['track_id'], tuple(row['bbox'])) for row in kept}

        # A first-frame geometry candidate is not yet jersey confirmed. An
        # anchor must lie in the strict near court, but later accepted boxes
        # can maintain image continuity without refreshing its floor point.
        if frame > first:
            for row in kept:
                appearance = torso_histogram(hsv, row['bbox'])
                if appearance is None:
                    continue
                box = row['bbox']
                position = project([(box[0] + box[2]) / 2, box[3]], matrix)
                track_id = int(row['track_id'])
                strict_anchor = (MIN_ANCHOR_NET_DISTANCE_M <= float(position[1]) <= 9
                                 and -1.5 <= float(position[0]) <= 10.5)
                if strict_anchor:
                    states[track_id] = TrackState(
                        frame, box, appearance[0], frame, box,
                        [float(position[0]), float(position[1])])
                elif track_id in states:
                    state = states[track_id]
                    gap = frame - state.last_frame
                    old_centre, new_centre = _centre(state.last_box), _centre(box)
                    height = state.anchor_box[3] - state.anchor_box[1]
                    if (height <= 0 or not 1 <= gap <= MAX_MISSING_FRAMES
                            or abs(new_centre[0] - old_centre[0])
                            > MAX_STEP_FRACTION * height * gap
                            or abs(new_centre[1] - old_centre[1])
                            > MAX_STEP_FRACTION * height * gap
                            or cv2.compareHist(appearance[0], state.last_hist,
                                               cv2.HISTCMP_BHATTACHARYYA) > THRESHOLD):
                        states.pop(track_id)
                        pending.pop(track_id, None)
                        active_grace.discard(track_id)
                        continue
                    states[track_id] = TrackState(
                        frame, box, appearance[0], state.anchor_frame,
                        state.anchor_box, state.anchor_position)
                else:
                    continue
                pending.pop(track_id, None)
                active_grace.discard(track_id)

        for row in raw[key]:
            track_id = int(row['track_id'])
            box = row['bbox']
            if (track_id < 1 or (track_id, tuple(box)) in accepted_keys
                    or track_id not in states):
                continue
            state = states[track_id]
            gap = frame - state.last_frame
            if not (1 <= gap <= MAX_MISSING_FRAMES
                    and frame - state.anchor_frame <= max_grace_frames):
                continue
            position = project([(box[0] + box[2]) / 2, box[3]], matrix)
            if (in_target_region(position, False)
                    or float(position[1]) < MIN_OUTSIDE_NET_POSITION_M):
                continue  # Only test upward escapes past the near-net line.
            height = state.anchor_box[3] - state.anchor_box[1]
            if height <= 0 or state.anchor_box[3] - box[3] < MIN_RISE_FRACTION * height:
                pending.pop(track_id, None)
                active_grace.discard(track_id)
                continue
            if box[3] - box[1] < MIN_HEIGHT_RATIO * height:
                pending.pop(track_id, None)
                active_grace.discard(track_id)
                continue
            old_centre, new_centre = _centre(state.last_box), _centre(box)
            if (abs(new_centre[0] - old_centre[0]) > MAX_STEP_FRACTION * height * gap
                    or abs(new_centre[1] - old_centre[1]) > MAX_STEP_FRACTION * height * gap):
                continue
            appearance = torso_histogram(hsv, box)
            if (appearance is None or cv2.compareHist(
                    appearance[0], state.last_hist,
                    cv2.HISTCMP_BHATTACHARYYA) > THRESHOLD):
                continue
            median_hsv = appearance[1]
            if not (BLUE_HUE_RANGE[0] <= median_hsv[0] <= BLUE_HUE_RANGE[1]
                    and median_hsv[1] >= MIN_BLUE_SATURATION
                    and median_hsv[2] >= MIN_BLUE_VALUE):
                continue
            previous_candidate = pending.get(track_id)
            if track_id not in active_grace:
                if previous_candidate is None:
                    pending[track_id] = (frame, row, appearance[0])
                    continue
                pending_frame, pending_row, pending_hist = previous_candidate
                if frame - pending_frame > MAX_MISSING_FRAMES:
                    pending[track_id] = (frame, row, appearance[0])
                    continue
                if (state.anchor_box[3] - box[3]
                        < MIN_CONFIRMED_RISE_FRACTION * height):
                    continue
                pending_centre = _centre(pending_row['bbox'])
                if (abs(new_centre[0] - pending_centre[0])
                        > MAX_STEP_FRACTION * height * (frame - pending_frame)
                        or abs(new_centre[1] - pending_centre[1])
                        > MAX_STEP_FRACTION * height * (frame - pending_frame)
                        or cv2.compareHist(appearance[0], pending_hist,
                                           cv2.HISTCMP_BHATTACHARYYA) > THRESHOLD):
                    pending[track_id] = (frame, row, appearance[0])
                    continue
                first_rescue = {
                    **pending_row, 'court_position_status': 'possible_airborne',
                    'last_court_compatible_position_m': state.anchor_position,
                    'last_court_compatible_frame': state.anchor_frame}
                output[str(pending_frame)].append(first_rescue)
                rescued.append({'frame': pending_frame, 'track_id': track_id,
                                'anchor_frame': state.anchor_frame})
                pending.pop(track_id)
                active_grace.add(track_id)
            rescued_row = {**row, 'court_position_status': 'possible_airborne',
                           'last_court_compatible_position_m': state.anchor_position,
                           'last_court_compatible_frame': state.anchor_frame}
            kept.append(rescued_row)
            states[track_id] = TrackState(
                frame, box, appearance[0], state.anchor_frame,
                state.anchor_box, state.anchor_position)
            rescued.append({'frame': frame, 'track_id': track_id,
                            'anchor_frame': state.anchor_frame})
        output[key] = kept
    return output, {'rescued': rescued, 'rescued_count': len(rescued),
                    'max_grace_frames': max_grace_frames,
                    'first_frame_requires_court_compatible_anchor': True}
