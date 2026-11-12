"""Conservative lower-net-tape cue restricted to a detected player's torso."""

from evaluate_pilot_tracker import iou
from net_tape_visibility import tape_visibility


MIN_POSE_IOU = .35
MIN_KEYPOINT_CONFIDENCE = .40


def torso_at_tape(box, pose_boxes, keypoints_xy, keypoints_conf, tape_line):
    """Return a torso rectangle crossing the tape, or None if uncertain."""
    matches = [(iou(box, pose_box), idx) for idx, pose_box in enumerate(pose_boxes)]
    if not matches:
        return None
    overlap, idx = max(matches)
    if overlap < MIN_POSE_IOU:
        return None
    points = keypoints_xy[idx]
    scores = keypoints_conf[idx]
    if any(scores[j] < MIN_KEYPOINT_CONFIDENCE for j in (5, 6, 11, 12)):
        return None
    shoulders = [points[5], points[6]]
    hips = [points[11], points[12]]
    shoulder_y = (shoulders[0][1] + shoulders[1][1]) / 2
    hip_y = (hips[0][1] + hips[1][1]) / 2
    centre_x = (box[0] + box[2]) / 2
    (ax, ay), (bx, by) = tape_line
    tape_y = ay + (centre_x - ax) * (by - ay) / (bx - ax)
    if not shoulder_y + 8 <= tape_y <= hip_y - 8:
        return None
    t = (tape_y - shoulder_y) / (hip_y - shoulder_y)
    left = shoulders[0][0] * (1 - t) + hips[0][0] * t
    right = shoulders[1][0] * (1 - t) + hips[1][0] * t
    if left > right:
        left, right = right, left
    width = right - left
    if width < 18:
        return None
    return [left - .08 * width, shoulder_y, right + .08 * width, hip_y]


def pose_tape_visibility(image, hsv, box, pose_boxes, keypoints_xy,
                         keypoints_conf, tape_line):
    torso = torso_at_tape(box, pose_boxes, keypoints_xy, keypoints_conf,
                          tape_line)
    if torso is None:
        return {'status': 'not_applicable', 'reason': 'no_usable_torso_crossing'}
    return tape_visibility(image, torso, tape_line, hsv)
