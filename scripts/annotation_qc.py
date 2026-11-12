"""Week 6 structural checks. Passing these checks does not certify visual accuracy."""
import csv
import json
import math
from collections import Counter
from pathlib import Path

BASE_COLUMNS = set('match_id rally_id frame_index time_s object_type id_type id x1 y1 x2 y2 confidence occlusion'.split())
REVIEW_COLUMNS = set('annotation_source annotator_id review_status reviewer_id'.split())
POSITION_COLUMNS = set('team_id foot_x_px foot_y_px position_status'.split())


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def probe_video(path):
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError(f'Cannot open video: {path}')
        info = dict(zip(('width', 'height', 'fps', 'frame_count'),
                        (cap.get(p) for p in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT,
                                             cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_COUNT))))
        if not all(math.isfinite(v) and v > 0 for v in info.values()):
            raise ValueError('Video has invalid dimensions, FPS or frame count')
        for key in ('width', 'height', 'frame_count'):
            info[key] = int(info[key])
        info['file'] = Path(path).name
        return info
    finally:
        cap.release()


def number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('non-finite number')
    return result


def run_checks(match_dir, annotations_csv, out_path=None, video=None):
    directory = Path(match_dir)
    issues = []

    def issue(code, line=None, severity='error', **details):
        issues.append(dict(code=code, severity=severity, line=line, **details))

    try:
        meta = read_json(directory / 'metadata.json')
        if not isinstance(meta, dict):
            raise ValueError('metadata must be an object')
    except (OSError, ValueError) as exc:
        meta = {}
        issue('metadata_unavailable', detail=str(exc))
    if meta.get('match_id') != directory.name:
        issue('metadata_match_id_mismatch', expected=directory.name, actual=meta.get('match_id'))
    videos = [Path(video)] if video else sorted(directory.glob('*.mp4'))
    measured = None
    if len(videos) != 1:
        issue('video_missing_or_ambiguous', count=len(videos))
    else:
        try:
            measured = probe_video(videos[0])
        except (ImportError, ValueError) as exc:
            issue('video_probe_failed', detail=str(exc))
    camera = meta.get('camera') or {}
    if not isinstance(camera, dict):
        camera = {}
    for key in ('width', 'height', 'fps'):
        try:
            declared = number(camera[key])
            if declared <= 0:
                raise ValueError('must be positive')
            if measured and not math.isclose(declared, measured[key], rel_tol=0, abs_tol=0.001):
                issue('camera_metadata_mismatch', field=key, declared=declared, measured=measured[key])
        except (KeyError, ValueError, TypeError):
            issue('invalid_camera_metadata', field=key)
    width = measured['width'] if measured else None
    height = measured['height'] if measured else None
    fps = measured['fps'] if measured else None

    rallies = {}
    raw_rallies = meta.get('rallies', [])
    if not isinstance(raw_rallies, list):
        raw_rallies = []
        issue('invalid_rallies')
    for rally in raw_rallies:
        try:
            rid = rally['rally_id']
            start, end = number(rally['t_start']), number(rally['t_end'])
            if not rid or rid in rallies or not 0 <= start < end:
                raise ValueError('duplicate/empty ID or invalid interval')
            rallies[rid] = (start, end)
            if measured and end > measured['frame_count'] / fps + 1 / fps:
                issue('rally_exceeds_video', rally_id=rid)
        except (KeyError, TypeError, ValueError) as exc:
            issue('invalid_rally', detail=str(exc))
    if not rallies:
        issue('no_valid_rallies')

    calibration_ok = False
    try:
        import cv2
        import numpy as np
        calibration = meta.get('homography') or read_json(directory / 'homography.json')
        source = np.asarray(calibration['points_px'], dtype=float)
        target = np.asarray(calibration['points_court_m'], dtype=float)
        if source.shape != (4, 2) or target.shape != (4, 2):
            raise ValueError('four corresponding 2D points required')
        if not np.isfinite(source).all() or not np.isfinite(target).all():
            raise ValueError('non-finite calibration')
        for polygon in (source, target):
            contour = polygon.astype(np.float32)
            if not cv2.isContourConvex(contour) or abs(cv2.contourArea(contour)) < 1e-6:
                raise ValueError('corners must form a non-degenerate convex polygon in order')
        image_size = calibration.get('image_size')
        if image_size is not None:
            iw, ih = map(number, image_size)
            if iw <= 0 or ih <= 0:
                raise ValueError('invalid calibration image_size')
            if ((source < 0).any() or (source[:, 0] > iw).any() or (source[:, 1] > ih).any()):
                raise ValueError('calibration points outside reference image')
            if measured:
                source *= np.array([width / iw, height / ih])
        elif measured and ((source < 0).any() or (source[:, 0] > width).any() or (source[:, 1] > height).any()):
            raise ValueError('calibration points outside native video')
        matrix = cv2.getPerspectiveTransform(source.astype(np.float32), target.astype(np.float32))
        if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) != 3:
            raise ValueError('singular homography')
        calibration_ok = True
    except (OSError, ImportError, ValueError, KeyError, TypeError) as exc:
        issue('calibration_unavailable_or_invalid', severity='warning', detail=str(exc))

    rows = []
    columns = set()
    try:
        with Path(annotations_csv).open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            rows = list(reader)
    except OSError as exc:
        issue('annotations_unavailable', detail=str(exc))
    for name, required in [('base', BASE_COLUMNS), ('review', REVIEW_COLUMNS), ('position', POSITION_COLUMNS)]:
        missing = sorted(required - columns)
        if missing:
            issue('missing_columns', group=name, columns=missing)
    if not rows:
        issue('empty_annotations')

    seen = set()
    verified = 0
    frames = set()
    for line, row in enumerate(rows, start=2):
        if row.get('match_id') != directory.name:
            issue('annotation_match_id_mismatch', line)
        rid = row.get('rally_id')
        if rid not in rallies:
            issue('unknown_rally_id', line, rally_id=rid)
        try:
            frame = int(row['frame_index'])
            timestamp = number(row['time_s'])
            frames.add(frame)
            if frame < 0 or (measured and frame >= measured['frame_count']):
                issue('frame_out_of_bounds', line)
            if timestamp < 0 or (fps and abs(timestamp - frame / fps) > 0.5 / fps + 1e-6):
                issue('timestamp_frame_mismatch', line)
            if rid in rallies and fps and not rallies[rid][0] <= frame / fps < rallies[rid][1]:
                issue('frame_outside_rally', line)
            key = (row.get('match_id'), frame, row.get('object_type'), row.get('id_type'), row.get('id'))
            if key in seen:
                issue('duplicate_id_same_frame', line)
            seen.add(key)
        except (KeyError, ValueError, TypeError):
            issue('invalid_frame_or_timestamp', line)
        if row.get('object_type') not in ('player', 'ball'):
            issue('invalid_object_type', line)
        if row.get('id_type') not in ('player_id', 'track_id') or not row.get('id'):
            issue('invalid_identity', line)
        if row.get('occlusion') not in ('none', 'partial', 'full'):
            issue('invalid_occlusion', line)
        bbox = [row.get(k, '') for k in ('x1', 'y1', 'x2', 'y2')]
        try:
            if any(bbox):
                x1, y1, x2, y2 = map(number, bbox)
                if not (0 <= x1 < x2 and 0 <= y1 < y2):
                    issue('invalid_bbox', line)
                elif width and (x2 > width or y2 > height):
                    issue('bbox_out_of_bounds', line)
                if row.get('occlusion') == 'full':
                    issue('fully_occluded_bbox_must_be_empty', line)
            elif row.get('occlusion') != 'full':
                issue('missing_bbox', line)
            if row.get('confidence') and not 0 <= number(row['confidence']) <= 1:
                issue('invalid_confidence', line)
        except (ValueError, TypeError):
            issue('invalid_bbox_or_confidence', line)
        source = row.get('annotation_source')
        status = row.get('review_status')
        if source not in ('manual', 'assisted', 'automatic', 'example'):
            issue('missing_or_invalid_annotation_source', line)
        if status not in ('unreviewed', 'reviewed', 'adjudicated', 'rejected'):
            issue('missing_or_invalid_review_status', line)
        review_ok = (source in ('manual', 'assisted') and status in ('reviewed', 'adjudicated')
                     and bool(row.get('annotator_id')) and bool(row.get('reviewer_id'))
                     and row.get('annotator_id') != row.get('reviewer_id'))
        if review_ok:
            verified += 1
        else:
            issue('not_independently_reviewed', line)
        if row.get('object_type') == 'player':
            if row.get('team_id') not in ('home', 'away', 'unknown'):
                issue('invalid_team_id', line)
            position = row.get('position_status')
            if position not in ('visible', 'occluded', 'airborne', 'out_of_frame', 'uncertain'):
                issue('missing_or_invalid_position_status', line)
            fx, fy = row.get('foot_x_px'), row.get('foot_y_px')
            try:
                if position == 'visible':
                    x, y = number(fx), number(fy)
                    if x < 0 or y < 0 or (width and (x >= width or y >= height)):
                        issue('footpoint_out_of_bounds', line)
                    if row.get('occlusion') == 'full':
                        issue('fully_occluded_position_marked_visible', line)
                elif fx or fy:
                    issue('unobservable_footpoint_must_be_empty', line)
            except (ValueError, TypeError):
                issue('invalid_footpoint', line)

    errors = sum(i['severity'] == 'error' for i in issues)
    summary = {
        'match_dir': str(directory), 'annotations_csv': str(annotations_csv),
        'rows_checked': len(rows), 'distinct_frames': len(frames),
        'review_provenance_rows': verified, 'measured_video': measured,
        'calibration_structurally_valid': calibration_ok,
        'issues_found': len(issues), 'errors': errors,
        'issue_counts': dict(sorted(Counter(i['code'] for i in issues).items())),
        'structural_status': 'fail' if errors else 'pass',
        'visual_accuracy': 'not_assessed',
        'release_status': 'blocked' if errors else 'requires_visual_and_dataset_review',
        'issues': issues,
    }
    if out_path:
        output = Path(out_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return summary
