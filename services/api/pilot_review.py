"""Local, frame-indexed review of pilot rally boundaries. Run on loopback only."""
import csv
import hashlib
import html
import io
import json
import math
import re
import threading
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Literal

import cv2
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MATCHES = ROOT / 'data' / 'matches'
R1_CASE_STUDY = ROOT / 'data' / 'processed' / 'fqe_r1_boundary_recheck'
CASE_STUDY_CATALOG = ROOT / 'data' / 'processed' / 'case_studies_catalog.json'
AOEP_CASE_STUDY = ROOT / 'data' / 'processed' / 'aoep_new_source'
D79_CASE_STUDY = ROOT / 'data' / 'processed' / 'd79_new_source'
SAVE_LOCK = threading.Lock()
app = FastAPI(title='Volley pilot boundary review')
HONOURS_WORKSPACE = 'data/processed/honours_annotation_workspace'
S3P34_PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s3p34_30fps_ground_review'
S3P34_JERSEYS = ('28', '12', '15', '7', '19', '21')
S3P34_CALIBRATION_PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review'
S3P34_CALIBRATION_CODES = ('baseline_left', 'baseline_right', 'attack_left',
                           'attack_right', 'net_left', 'net_right')
S1P6_FIXED_PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review'
S1P6_CALIBRATION_PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_calibration_review'
S3P34_REMAINING_PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s3p34_remaining_rally_review'
TRANSITION_PACK = ROOT / 'data/processed/receive_to_attack_transition'
SIDEOUT_PACK = ROOT / 'data/processed/source_view_screen/usc_byu_sideout_review'


def s3p34_blank_rows():
    with (S3P34_PACK / 'single_reviewer_unsampled_blank.csv').open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def s3p34_draft():
    path = S3P34_PACK / 'single_reviewer_web_draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'reviewer_code': '', 'frames': {},
            'scope': 'single_reviewer_unblinded_diagnostic_segment',
            'strict_metric_approval': False}


def s3p34_save_draft(data, event):
    path = S3P34_PACK / 'single_reviewer_web_draft.json'
    history = S3P34_PACK / 'single_reviewer_web_history'
    history.mkdir(exist_ok=True)
    revision_id = uuid.uuid4().hex
    (history / f'{revision_id}.json').write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


class S3P34SourceRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jersey: Literal['28', '12', '15', '7', '19', '21']
    identity_status: Literal['confirmed', 'sequence_only', 'uncertain']
    ground_status: Literal['grounded', 'airborne', 'occluded', 'uncertain']
    shoe_midpoint_x_px: float | None = None
    shoe_midpoint_y_px: float | None = None
    reading_uncertainty_px: float | None = None
    notes: str = Field(default='', max_length=2000)


class S3P34PairedRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jersey: Literal['28', '12', '15', '7', '19', '21']
    candidate_alignment: Literal['same_player', 'wrong_player', 'uncertain']
    proxy_floor_alignment: Literal['plausible', 'implausible', 'uncertain']


class S3P34SourceSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    reviewer_code: str = Field(min_length=1, max_length=80)
    rows: list[S3P34SourceRow] = Field(min_length=6, max_length=6)


class S3P34PairedSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    rows: list[S3P34PairedRow] = Field(min_length=6, max_length=6)


class S3P34RemainingSourceRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jersey: Literal['28', '12', '15', '7', '19', '21']
    identity_status: Literal['digit_confirmed', 'sequence_consistent', 'uncertain', 'not_visible']
    ground_status: Literal['grounded', 'airborne', 'feet_occluded', 'not_visible', 'uncertain']
    shoe_x_px: float | None = None
    shoe_y_px: float | None = None
    note: str = Field(default='', max_length=1000)


class S3P34RemainingSourceSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    reviewer_code: str = Field(default='', max_length=80)
    checked_source_frame: bool
    candidate_boxes_shown_before_source: bool = False
    rows: list[S3P34RemainingSourceRow] = Field(min_length=6, max_length=6)


class S3P34RemainingPairedRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jersey: Literal['28', '12', '15', '7', '19', '21']
    candidate_alignment: Literal['same_player', 'wrong_player', 'no_box', 'uncertain']
    floor_alignment: Literal['plausible', 'implausible', 'not_applicable', 'uncertain']
    note: str = Field(default='', max_length=1000)


class S3P34RemainingPairedSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    checked_source_and_boxes: bool
    rows: list[S3P34RemainingPairedRow] = Field(min_length=6, max_length=6)


class TransitionEventSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    reviewer_code: str = Field(min_length=1, max_length=80)
    near_side_receives: bool | None
    reception_contact_frame_interval: list[int] | None
    first_near_side_attack_contact_frame_interval: list[int] | None
    attack_absent: bool | None
    source_only_before_metric: bool
    note: str = Field(default='', max_length=2000)


class SideoutEventSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=0)
    reviewer_code: str = Field(min_length=1, max_length=80)
    checked_unboxed_source: Literal[True]
    usc_served: bool | None
    byu_won: bool | None
    score_before: str = Field(default='', max_length=20)
    score_after: str = Field(default='', max_length=20)
    serve: list[int] | None
    reception: list[int] | None
    set: list[int] | None
    attack: list[int] | None
    point_end: list[int] | None
    note: str = Field(default='', max_length=2000)


def sideout_protocol():
    return json.loads((SIDEOUT_PACK / 'event_protocol.json').read_text(encoding='utf-8'))


def sideout_draft():
    path = SIDEOUT_PACK / 'event_review_draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'status': 'pending_source_review', 'verdict': None}


@app.get('/usc-byu-sideout-review')
def sideout_page():
    return FileResponse(ROOT / 'web/usc_byu_sideout_review.html')


@app.get('/usc-byu-sideout-clip')
def sideout_clip():
    protocol = sideout_protocol()
    source = ROOT / protocol['source_clip']
    return FileResponse(source, media_type='video/mp4')


@app.get('/api/usc-byu-sideout-review')
def sideout_state():
    return {'protocol': sideout_protocol(), 'draft': sideout_draft()}


@app.get('/api/usc-byu-sideout-review/frame/{frame}')
def sideout_image(frame: int):
    protocol = sideout_protocol()
    lo, hi = protocol['review_frame_interval_inclusive']
    if not lo <= frame <= hi:
        raise HTTPException(404, 'Frame outside side-out review clip')
    source = ROOT / protocol['source_clip']
    if hashlib.sha256(source.read_bytes()).hexdigest() != protocol['source_clip_sha256']:
        raise HTTPException(409, 'Review clip hash changed')
    capture = cv2.VideoCapture(str(source))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = capture.read()
        if not ok or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1:
            raise HTTPException(409, 'Source frame could not be decoded')
        ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok:
            raise HTTPException(500, 'Image encoding failed')
        return Response(content=encoded.tobytes(), media_type='image/jpeg',
                        headers={'Cache-Control': 'private, max-age=300'})
    finally:
        capture.release()


@app.put('/api/usc-byu-sideout-review')
def sideout_save(payload: SideoutEventSave, request: Request):
    s3p34_check_origin(request)
    protocol = sideout_protocol()
    lo, hi = protocol['review_frame_interval_inclusive']
    sequence = [payload.serve, payload.reception, payload.set,
                payload.attack, payload.point_end]
    for interval in sequence:
        if interval is not None and (len(interval) != 2 or
                not all(isinstance(n, int) and not isinstance(n, bool) for n in interval) or
                not lo <= interval[0] <= interval[1] <= hi):
            raise HTTPException(422, 'An event interval is invalid or outside the clip')
    observed = [interval for interval in sequence if interval is not None]
    if any(left[1] >= right[0] for left, right in zip(observed, observed[1:])):
        raise HTTPException(422, 'Marked events must be in time order')
    with SAVE_LOCK:
        draft = sideout_draft()
        if draft['revision'] != payload.expected_revision:
            raise HTTPException(409, 'A newer review revision exists; reload')
        new = {'revision': draft['revision'] + 1,
               'status': 'single_reviewer_source_event_draft',
               'source_clip_sha256': protocol['source_clip_sha256'],
               'verdict': payload.model_dump(exclude={'expected_revision'}),
               'saved_at_utc': datetime.now(timezone.utc).isoformat()}
        history = SIDEOUT_PACK / 'event_review_history'
        history.mkdir(exist_ok=True)
        (history / f'{uuid.uuid4().hex}.json').write_text(
            json.dumps({'prior': draft, 'new': new}, indent=2) + '\n', encoding='utf-8')
        path = SIDEOUT_PACK / 'event_review_draft.json'
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(new, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    return {'draft': new}


def transition_protocol():
    return json.loads((TRANSITION_PACK / 'protocol.json').read_text(encoding='utf-8'))


def transition_case(match_id, rally_id):
    case = next((r for r in transition_protocol()['cases']
                 if r['match_id'] == match_id and r['rally_id'] == rally_id), None)
    if case is None:
        raise HTTPException(404, 'Point is outside the frozen transition review')
    return case


def transition_draft():
    path = TRANSITION_PACK / 'draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'cases': {}}


@app.get('/receive-to-attack-review')
def transition_page():
    return FileResponse(ROOT / 'web/receive_to_attack_review.html')


@app.get('/receive_to_attack_review.js')
def transition_js():
    return FileResponse(ROOT / 'web/receive_to_attack_review.js', media_type='text/javascript')


@app.get('/api/receive-to-attack-review')
def transition_state():
    return {'protocol': transition_protocol(), 'draft': transition_draft(),
            'completed_exists': (TRANSITION_PACK / 'completed.json').exists()}


@app.get('/api/receive-to-attack-review/image/{match_id}/{rally_id}/{frame}')
def transition_image(match_id: str, rally_id: str, frame: int):
    case = transition_case(match_id, rally_id)
    first, last = case['provisional_interval_inclusive']
    if not first <= frame <= last:
        raise HTTPException(404, 'Frame outside frozen source interval')
    source = ROOT / 'data/matches' / match_id / f'source_{match_id[3:]}.mp4'
    if not source.is_file():
        raise HTTPException(404, 'Source video unavailable')
    capture = cv2.VideoCapture(str(source))
    try:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = capture.read()
        if not ok or round(capture.get(cv2.CAP_PROP_POS_FRAMES)) != frame + 1:
            raise HTTPException(409, 'Source frame could not be decoded')
        ok, encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ok:
            raise HTTPException(500, 'Image encoding failed')
        return Response(content=encoded.tobytes(), media_type='image/jpeg',
                        headers={'Cache-Control': 'private, max-age=300'})
    finally:
        capture.release()


@app.put('/api/receive-to-attack-review/{match_id}/{rally_id}')
def transition_save(match_id: str, rally_id: str, payload: TransitionEventSave, request: Request):
    s3p34_check_origin(request)
    case = transition_case(match_id, rally_id)
    if not payload.source_only_before_metric:
        raise HTTPException(422, 'Confirm source-only event review')
    first, last = case['provisional_interval_inclusive']
    for interval in (payload.reception_contact_frame_interval,
                     payload.first_near_side_attack_contact_frame_interval):
        if interval is not None and (len(interval) != 2 or
                not first <= interval[0] <= interval[1] <= last):
            raise HTTPException(422, 'Event interval is outside this point')
    if (payload.reception_contact_frame_interval and payload.first_near_side_attack_contact_frame_interval
            and payload.reception_contact_frame_interval[1] >= payload.first_near_side_attack_contact_frame_interval[0]):
        raise HTTPException(422, 'First attack must follow reception')
    with SAVE_LOCK:
        if (TRANSITION_PACK / 'completed.json').exists():
            raise HTTPException(409, 'Completed event review is frozen')
        data = transition_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'A newer revision exists; reload')
        key = f'{match_id}/{rally_id}'
        data['cases'][key] = payload.model_dump(exclude={'expected_revision'})
        data['cases'][key]['saved_at_utc'] = datetime.now(timezone.utc).isoformat()
        data['revision'] += 1
        history = TRANSITION_PACK / 'history'
        history.mkdir(exist_ok=True)
        (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps({'case': key, 'revision': data['revision']}, indent=2) + '\n', encoding='utf-8')
        target = TRANSITION_PACK / 'draft.json'
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        temporary.replace(target)
    return {'draft': data}


@app.post('/api/receive-to-attack-review/export')
def transition_export(request: Request):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        target = TRANSITION_PACK / 'completed.json'
        if target.exists():
            raise HTTPException(409, 'Completed event review already exists')
        protocol_path = TRANSITION_PACK / 'protocol.json'
        protocol = transition_protocol()
        data = transition_draft()
        cases = []
        for item in protocol['cases']:
            key = f"{item['match_id']}/{item['rally_id']}"
            row = data['cases'].get(key)
            if row is None:
                raise HTTPException(409, 'Both selected points need a saved event verdict')
            cases.append({'match_id': item['match_id'], 'rally_id': item['rally_id'],
                          **{k: row[k] for k in ('near_side_receives',
                            'reception_contact_frame_interval',
                            'first_near_side_attack_contact_frame_interval', 'attack_absent',
                            'reviewer_code', 'source_only_before_metric', 'note')}})
        output = {'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
                  'cases': cases}
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
        temporary.replace(target)
    return {'completed_json': str(target), 'cases': len(cases)}


def s3p34_remaining_manifest():
    return json.loads((S3P34_REMAINING_PACK / 'manifest.json').read_text(encoding='utf-8'))


def s3p34_focused_frames():
    protocol = json.loads((S3P34_REMAINING_PACK / 'focused_10hz_protocol.json').read_text(encoding='utf-8'))
    return set(protocol['new_frames_to_review'])


def s3p34_remaining_draft():
    path = S3P34_REMAINING_PACK / 'draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'reviewer_code': '', 'frames': {},
            'scope': 'single_reviewer_whole_candidate_interval_source_state_review'}


def s3p34_remaining_write(data, event):
    history = S3P34_REMAINING_PACK / 'history'
    history.mkdir(exist_ok=True)
    (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
    target = S3P34_REMAINING_PACK / 'draft.json'
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    temporary.replace(target)


def s3p34_remaining_frame(number):
    row = next((r for r in s3p34_remaining_manifest()['frames'] if r['source_frame'] == number), None)
    if row is None:
        raise HTTPException(404, 'Frame is outside frozen remaining-rally queue')
    return row


@app.get('/s3p34-remaining-rally-review')
def s3p34_remaining_page():
    return FileResponse(ROOT / 'web/s3p34_remaining_rally_review.html')


@app.get('/s3p34_remaining_rally_review.js')
def s3p34_remaining_js():
    return FileResponse(ROOT / 'web/s3p34_remaining_rally_review.js', media_type='text/javascript')


@app.get('/api/u5/s3p34-remaining-rally-review')
def s3p34_remaining_state(mode: str = 'focused'):
    if mode not in ('focused', 'full'):
        raise HTTPException(422, 'Review mode must be focused or full')
    manifest = s3p34_remaining_manifest()
    draft = s3p34_remaining_draft()
    selected = s3p34_focused_frames() if mode == 'focused' else None
    frames = [{'frame': row['source_frame'], 'image_url':
               f"/api/u5/s3p34-remaining-rally-review/image/{row['source_frame']}",
               'image_sha256': row['image_sha256'],
               'numbered_boxes': row['numbered_boxes']}
              for row in manifest['frames'] if selected is None or row['source_frame'] in selected]
    return {'frames': frames, 'roster': list(S3P34_JERSEYS), 'draft': draft,
            'mode': mode, 'completed_csv_exists': (S3P34_REMAINING_PACK /
            ('focused_completed.csv' if mode == 'focused' else 'completed.csv')).exists()}


@app.get('/api/u5/s3p34-remaining-rally-review/image/{frame}')
def s3p34_remaining_image(frame: int):
    row = s3p34_remaining_frame(frame)
    path = S3P34_REMAINING_PACK / row['image']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['image_sha256']:
        raise HTTPException(409, 'Frozen source image hash mismatch')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'private, max-age=3600'})


@app.put('/api/u5/s3p34-remaining-rally-review/{frame}/source')
def s3p34_remaining_save_source(frame: int, payload: S3P34RemainingSourceSave, request: Request):
    s3p34_check_origin(request)
    s3p34_remaining_frame(frame)
    s3p34_check_rows(payload.rows)
    if not payload.checked_source_frame:
        raise HTTPException(422, 'Confirm that this source frame was checked')
    for row in payload.rows:
        if (row.identity_status == 'not_visible') != (row.ground_status == 'not_visible'):
            raise HTTPException(422, 'Player visibility and ground state disagree')
        if (row.shoe_x_px is None) != (row.shoe_y_px is None):
            raise HTTPException(422, 'Both shoe coordinates are required together')
        if row.shoe_x_px is not None and (row.ground_status != 'grounded' or
                not 0 <= row.shoe_x_px < 1280 or not 0 <= row.shoe_y_px < 720 or
                not all(math.isfinite(v) for v in (row.shoe_x_px, row.shoe_y_px))):
            raise HTTPException(422, 'Shoe point must be on a grounded player in the source image')
    with SAVE_LOCK:
        if (S3P34_REMAINING_PACK / 'completed.csv').exists():
            raise HTTPException(409, 'Completed review is frozen')
        if frame in s3p34_focused_frames() and (S3P34_REMAINING_PACK / 'focused_completed.csv').exists():
            raise HTTPException(409, 'Focused review is frozen')
        data = s3p34_remaining_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'A newer revision exists; reload')
        before = data['frames'].get(str(frame))
        data['frames'][str(frame)] = {'source': [r.model_dump() for r in payload.rows],
                                     'paired': None,
                                     'candidate_boxes_shown_before_source': payload.candidate_boxes_shown_before_source,
                                     'source_saved_at_utc': datetime.now(timezone.utc).isoformat()}
        data['reviewer_code'] = payload.reviewer_code.strip() or 'MZ'
        data['revision'] += 1
        s3p34_remaining_write(data, {'frame': frame, 'stage': 'source',
                                     'previous': before, 'revision': data['revision']})
    return {'draft': data, 'numbered_boxes': s3p34_remaining_frame(frame)['numbered_boxes']}


@app.put('/api/u5/s3p34-remaining-rally-review/{frame}/paired')
def s3p34_remaining_save_paired(frame: int, payload: S3P34RemainingPairedSave, request: Request):
    s3p34_check_origin(request)
    manifest_frame = s3p34_remaining_frame(frame)
    s3p34_check_rows(payload.rows)
    if not payload.checked_source_and_boxes:
        raise HTTPException(422, 'Confirm that source and candidate boxes were compared')
    for row in payload.rows:
        has_box = manifest_frame['numbered_boxes'][row.jersey] is not None
        if (not has_box and row.candidate_alignment != 'no_box') or (has_box and row.candidate_alignment == 'no_box'):
            raise HTTPException(422, f'Candidate availability mismatch for slot {row.jersey}')
        if row.candidate_alignment != 'same_player' and row.floor_alignment == 'plausible':
            raise HTTPException(422, 'Unmatched box cannot have an accepted floor proxy')
    with SAVE_LOCK:
        if (S3P34_REMAINING_PACK / 'completed.csv').exists():
            raise HTTPException(409, 'Completed review is frozen')
        if frame in s3p34_focused_frames() and (S3P34_REMAINING_PACK / 'focused_completed.csv').exists():
            raise HTTPException(409, 'Focused review is frozen')
        data = s3p34_remaining_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'A newer revision exists; reload')
        record = data['frames'].get(str(frame))
        if not record or not record.get('source'):
            raise HTTPException(409, 'Save source-only review first')
        by_jersey = {r['jersey']: r for r in record['source']}
        for row in payload.rows:
            if (by_jersey[row.jersey]['identity_status'] == 'not_visible' or
                    by_jersey[row.jersey]['ground_status'] == 'not_visible') and row.candidate_alignment == 'same_player':
                raise HTTPException(422, 'A player marked not visible cannot have a same-player box')
            if by_jersey[row.jersey]['ground_status'] != 'grounded' and row.floor_alignment == 'plausible':
                raise HTTPException(422, 'Airborne or uncertain floor point cannot be accepted')
        record['paired'] = [r.model_dump() for r in payload.rows]
        record['paired_saved_at_utc'] = datetime.now(timezone.utc).isoformat()
        data['revision'] += 1
        s3p34_remaining_write(data, {'frame': frame, 'stage': 'paired',
                                     'revision': data['revision']})
    return {'draft': data}


def s3p34_remaining_export_selected(request: Request, focused: bool):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        output = S3P34_REMAINING_PACK / ('focused_completed.csv' if focused else 'completed.csv')
        if output.exists():
            raise HTTPException(409, 'Completed review already exists')
        manifest = s3p34_remaining_manifest()
        data = s3p34_remaining_draft()
        selected = s3p34_focused_frames() if focused else None
        items = [r for r in manifest['frames'] if selected is None or r['source_frame'] in selected]
        if focused and len(items) != len(selected):
            raise HTTPException(409, 'Focused protocol and manifest disagree')
        if any(
                not data['frames'].get(str(r['source_frame']), {}).get('paired')
                for r in items):
            raise HTTPException(409, f'Finish both stages on all {len(items)} selected frames first')
        if not focused:
            block_frame = data['frames'].get('36112', {})
            block_player = next((r for r in block_frame.get('source', []) if r['jersey'] == '15'), None)
            if block_player is None or block_player['ground_status'] == 'grounded':
                raise HTTPException(409, 'Review frame 36112: UCLA #15 is airborne in the prior source audit and cannot be saved as grounded')
        fields = ['source_frame', 'jersey', 'image_sha256', 'reviewer_code',
                  'candidate_boxes_shown_before_source',
                  'identity_status', 'ground_status', 'shoe_x_px', 'shoe_y_px',
                  'candidate_alignment', 'floor_alignment', 'raw_track_id', 'note']
        rows = []
        for item in items:
            frame = item['source_frame']
            record = data['frames'][str(frame)]
            for source, paired in zip(record['source'], record['paired']):
                assert source['jersey'] == paired['jersey']
                box = item['numbered_boxes'][source['jersey']]
                rows.append({'source_frame': frame, 'jersey': source['jersey'],
                             'image_sha256': item['image_sha256'],
                             'reviewer_code': data['reviewer_code'],
                             'candidate_boxes_shown_before_source': record.get('candidate_boxes_shown_before_source', False),
                             'identity_status': source['identity_status'],
                             'ground_status': source['ground_status'],
                             'shoe_x_px': source['shoe_x_px'], 'shoe_y_px': source['shoe_y_px'],
                             'candidate_alignment': paired['candidate_alignment'],
                             'floor_alignment': paired['floor_alignment'],
                             'raw_track_id': box['raw_track_id'] if box else None,
                             'note': (source['note'] + ' ' + paired['note']).strip()})
        temporary = output.with_suffix('.csv.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(output)
    return {'completed_csv': str(output), 'rows': len(rows)}


@app.post('/api/u5/s3p34-remaining-rally-review/export')
def s3p34_remaining_export(request: Request):
    return s3p34_remaining_export_selected(request, focused=False)


@app.post('/api/u5/s3p34-remaining-rally-review/export-focused')
def s3p34_remaining_export_focused(request: Request):
    return s3p34_remaining_export_selected(request, focused=True)


class S3P34CalibrationRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: Literal['baseline_left', 'baseline_right', 'attack_left',
                  'attack_right', 'net_left', 'net_right']
    status: Literal['marked', 'uncertain', 'occluded']
    x_px: float | None = None
    y_px: float | None = None
    note: str = Field(default='', max_length=1000)


class S3P34CalibrationSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    reviewer_code: str = Field(min_length=1, max_length=80)
    rows: list[S3P34CalibrationRow] = Field(min_length=6, max_length=6)


class S1P6FixedSourceRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    slot: Literal[1, 2, 3, 4, 5, 6]
    identity_status: Literal['sequence_consistent', 'uncertain', 'absent']
    ground_status: Literal['grounded', 'airborne', 'occluded', 'uncertain']
    shoe_x_px: float | None = None
    shoe_y_px: float | None = None
    note: str = Field(default='', max_length=1000)


class S1P6FixedSourceSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    reviewer_code: str = Field(min_length=1, max_length=80)
    source_phase: Literal['live', 'not_live', 'uncertain']
    rows: list[S1P6FixedSourceRow] = Field(min_length=6, max_length=6)


class S1P6PairedRow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    slot: Literal[1, 2, 3, 4, 5, 6]
    raw_track_id: int | None = None
    candidate_alignment: Literal['same_player', 'wrong_player', 'no_box', 'uncertain']
    floor_alignment: Literal['plausible', 'implausible', 'uncertain', 'not_applicable']
    note: str = Field(default='', max_length=1000)


class S1P6PairedSave(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int
    reviewer_code: str = Field(min_length=1, max_length=80)
    checked_source_and_boxes: bool
    rows: list[S1P6PairedRow] = Field(min_length=6, max_length=6)


def s3p34_calibration_protocol():
    return json.loads((S3P34_CALIBRATION_PACK / 'protocol.json').read_text(encoding='utf-8'))


def s3p34_calibration_draft():
    path = S3P34_CALIBRATION_PACK / 'draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'reviewer_code': '', 'frames': {},
            'scope': 'single_reviewer_source_only_calibration_check'}


def s3p34_calibration_save_draft(data, event):
    history = S3P34_CALIBRATION_PACK / 'history'
    history.mkdir(exist_ok=True)
    (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
    target = S3P34_CALIBRATION_PACK / 'draft.json'
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    temporary.replace(target)


def s3p34_check_origin(request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin writes are not allowed')


def s3p34_check_rows(rows):
    if [row.jersey for row in rows] != list(S3P34_JERSEYS):
        raise HTTPException(422, 'Six jersey rows must remain in the frozen order')


def s3p34_check_frame(frame):
    if str(frame) not in {row['source_frame'] for row in s3p34_blank_rows()}:
        raise HTTPException(404, 'Frame is outside the 30-frame review queue')


@app.get('/s3p34-ground-review')
def s3p34_ground_review_page():
    return FileResponse(ROOT / 'web/s3p34_ground_review.html')


@app.get('/s3p34_ground_review.js')
def s3p34_ground_review_js():
    return FileResponse(ROOT / 'web/s3p34_ground_review.js', media_type='text/javascript')


@app.get('/api/u5/s3p34-ground-review')
def s3p34_ground_review_state():
    reference = s3p34_blank_rows()
    manifest = json.loads((S3P34_PACK / 'manifest.json').read_text(encoding='utf-8'))
    frames = []
    for row in reference[::6]:
        frame = int(row['source_frame'])
        frames.append({'frame': frame,
                       'image_url': f'/api/u5/s3p34-ground-review/source/{frame}',
                       'paired_url': f'/api/u5/s3p34-ground-review/paired/{frame}',
                       'image_sha256': row['image_sha256']})
    return {'frames': frames, 'jerseys': S3P34_JERSEYS,
            'source_video_sha256': manifest['source_video_sha256'],
            'draft': s3p34_draft(), 'completed_csv_exists':
            (S3P34_PACK / 'single_reviewer_unsampled_completed.csv').exists()}


@app.get('/api/u5/s3p34-ground-review/source/{frame}')
def s3p34_ground_review_source(frame: int):
    s3p34_check_frame(frame)
    row = next(row for row in s3p34_blank_rows() if int(row['source_frame']) == frame)
    path = S3P34_PACK / row['unboxed_image']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['image_sha256']:
        raise HTTPException(409, 'Source image does not match frozen review hash')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})


@app.get('/api/u5/s3p34-ground-review/paired/{frame}')
def s3p34_ground_review_paired(frame: int):
    s3p34_check_frame(frame)
    if not s3p34_draft()['frames'].get(str(frame), {}).get('source'):
        raise HTTPException(409, 'Save source-only verdicts before opening the paired sheet')
    row = next(row for row in s3p34_blank_rows() if int(row['source_frame']) == frame)
    path = (S3P34_PACK / row['paired_sheet_after_unboxed_review']).resolve()
    expected_parent = (S3P34_PACK.parent / 's3p34_full_span_review').resolve()
    if path.parent != expected_parent or not path.is_file():
        raise HTTPException(404, 'Paired source sheet unavailable')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'private, max-age=3600'})


@app.put('/api/u5/s3p34-ground-review/{frame}/source')
def s3p34_ground_review_save_source(frame: int, payload: S3P34SourceSave, request: Request):
    s3p34_check_origin(request)
    s3p34_check_frame(frame)
    s3p34_check_rows(payload.rows)
    if not payload.reviewer_code.strip():
        raise HTTPException(422, 'Reviewer code is required')
    for row in payload.rows:
        x, y, uncertainty = row.shoe_midpoint_x_px, row.shoe_midpoint_y_px, row.reading_uncertainty_px
        if any(value is not None for value in (x, y, uncertainty)):
            if (row.ground_status != 'grounded' or x is None or y is None or uncertainty is None
                    or not all(math.isfinite(value) for value in (x, y, uncertainty))
                    or not 0 <= x < 1280 or not 0 <= y < 720 or uncertainty < 0):
                raise HTTPException(422, f'Invalid grounded shoe mark for #{row.jersey}')
    with SAVE_LOCK:
        if (S3P34_PACK / 'single_reviewer_unsampled_completed.csv').exists():
            raise HTTPException(409, 'Completed CSV already exists; preserve the exported annotation')
        data = s3p34_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'Another browser tab saved a newer revision; reload before editing')
        before = data['frames'].get(str(frame))
        data['frames'][str(frame)] = {'source': [row.model_dump() for row in payload.rows],
                                     'paired': None, 'saved_at_utc': datetime.now(timezone.utc).isoformat()}
        data['reviewer_code'] = payload.reviewer_code.strip()
        data['revision'] += 1
        s3p34_save_draft(data, {'frame': frame, 'stage': 'source', 'previous': before,
                                'current': data['frames'][str(frame)], 'revision': data['revision']})
    return {'draft': data}


@app.put('/api/u5/s3p34-ground-review/{frame}/paired')
def s3p34_ground_review_save_paired(frame: int, payload: S3P34PairedSave, request: Request):
    s3p34_check_origin(request)
    s3p34_check_frame(frame)
    s3p34_check_rows(payload.rows)
    with SAVE_LOCK:
        if (S3P34_PACK / 'single_reviewer_unsampled_completed.csv').exists():
            raise HTTPException(409, 'Completed CSV already exists; preserve the exported annotation')
        data = s3p34_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'Another browser tab saved a newer revision; reload before editing')
        record = data['frames'].get(str(frame))
        if not record or not record.get('source'):
            raise HTTPException(409, 'Save all six source-only verdicts before paired comparison')
        before = record.get('paired')
        record['paired'] = [row.model_dump() for row in payload.rows]
        record['paired_saved_at_utc'] = datetime.now(timezone.utc).isoformat()
        data['revision'] += 1
        s3p34_save_draft(data, {'frame': frame, 'stage': 'paired', 'previous': before,
                                'current': record['paired'], 'revision': data['revision']})
    return {'draft': data}


@app.post('/api/u5/s3p34-ground-review/export')
def s3p34_ground_review_export(request: Request):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        data = s3p34_draft()
        reference = s3p34_blank_rows()
        if len(data['frames']) != 30 or any(not data['frames'].get(row['source_frame'], {}).get('paired') for row in reference):
            raise HTTPException(409, 'Finish source and paired decisions for all 30 frames before exporting')
        output = S3P34_PACK / 'single_reviewer_unsampled_completed.csv'
        if output.exists():
            raise HTTPException(409, 'Completed CSV already exists; preserve the existing annotation')
        completed = []
        for row in reference:
            frame = data['frames'][row['source_frame']]
            jersey = row['jersey']
            source = next(item for item in frame['source'] if item['jersey'] == jersey)
            paired = next(item for item in frame['paired'] if item['jersey'] == jersey)
            copy = dict(row)
            for key in ('identity_status', 'ground_status', 'notes', 'shoe_midpoint_x_px',
                        'shoe_midpoint_y_px', 'reading_uncertainty_px'):
                copy[key] = '' if source[key] is None else source[key]
            for key in ('candidate_alignment', 'proxy_floor_alignment'):
                copy[key] = paired[key]
            completed.append(copy)
        temporary = output.with_suffix('.csv.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=reference[0].keys())
            writer.writeheader()
            writer.writerows(completed)
        temporary.replace(output)
    return {'completed_csv': str(output), 'rows': len(completed),
            'strict_metric_approval': False}


@app.get('/s3p34-calibration-review')
def s3p34_calibration_review_page():
    return FileResponse(ROOT / 'web/s3p34_calibration_review.html')


@app.get('/s3p34_calibration_review.js')
def s3p34_calibration_review_js():
    return FileResponse(ROOT / 'web/s3p34_calibration_review.js', media_type='text/javascript')


@app.get('/api/u5/s3p34-calibration-review')
def s3p34_calibration_review_state():
    protocol = s3p34_calibration_protocol()
    frames = []
    for item in protocol['frames']:
        path = S3P34_PACK / item['image']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise HTTPException(409, 'Calibration source image does not match frozen hash')
        frames.append({'frame': item['frame'], 'image_url':
                       f"/api/u5/s3p34-ground-review/source/{item['frame']}",
                       'image_sha256': item['sha256']})
    return {'frames': frames, 'landmarks': protocol['landmarks'],
            'protocol_sha256': hashlib.sha256(
                (S3P34_CALIBRATION_PACK / 'protocol.json').read_bytes()).hexdigest(),
            'draft': s3p34_calibration_draft(),
            'completed_csv_exists': (S3P34_CALIBRATION_PACK / 'completed.csv').exists()}


@app.put('/api/u5/s3p34-calibration-review/{frame}')
def s3p34_calibration_review_save(frame: int, payload: S3P34CalibrationSave, request: Request):
    s3p34_check_origin(request)
    if not payload.reviewer_code.strip():
        raise HTTPException(422, 'Reviewer code cannot be blank')
    protocol = s3p34_calibration_protocol()
    if frame not in {item['frame'] for item in protocol['frames']}:
        raise HTTPException(404, 'Frame is outside frozen calibration review')
    if [row.code for row in payload.rows] != list(S3P34_CALIBRATION_CODES):
        raise HTTPException(422, 'Landmark rows must remain in frozen order')
    for row in payload.rows:
        if row.status == 'marked':
            if (row.x_px is None or row.y_px is None or
                    not all(math.isfinite(value) for value in (row.x_px, row.y_px)) or
                    not 0 <= row.x_px < 1280 or not 0 <= row.y_px < 720):
                raise HTTPException(422, f'Invalid pixel mark for {row.code}')
        elif row.x_px is not None or row.y_px is not None:
            raise HTTPException(422, f'Uncertain landmark {row.code} must have null coordinates')
    with SAVE_LOCK:
        if (S3P34_CALIBRATION_PACK / 'completed.csv').exists():
            raise HTTPException(409, 'Completed calibration form already exists')
        data = s3p34_calibration_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'Another browser tab saved a newer revision; reload before editing')
        before = data['frames'].get(str(frame))
        data['frames'][str(frame)] = {'rows': [row.model_dump() for row in payload.rows],
                                     'saved_at_utc': datetime.now(timezone.utc).isoformat()}
        data['reviewer_code'] = payload.reviewer_code.strip()
        data['revision'] += 1
        s3p34_calibration_save_draft(data, {'frame': frame, 'previous': before,
                                           'current': data['frames'][str(frame)],
                                           'revision': data['revision']})
    return {'draft': data}


@app.post('/api/u5/s3p34-calibration-review/export')
def s3p34_calibration_review_export(request: Request):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        protocol = s3p34_calibration_protocol()
        data = s3p34_calibration_draft()
        if any(str(item['frame']) not in data['frames'] for item in protocol['frames']):
            raise HTTPException(409, 'Save all source landmark reviews first')
        output = S3P34_CALIBRATION_PACK / 'completed.csv'
        if output.exists():
            raise HTTPException(409, 'Completed calibration form already exists')
        rows = []
        for item in protocol['frames']:
            reviewed = data['frames'][str(item['frame'])]['rows']
            for expected, mark in zip(protocol['landmarks'], reviewed, strict=True):
                if mark['code'] != expected['code']:
                    raise HTTPException(409, 'Landmark order changed after save')
                rows.append({'source_frame': item['frame'], 'image': item['image'],
                             'image_sha256': item['sha256'], 'landmark_code': expected['code'],
                             'court_x_m': expected['court_m'][0],
                             'court_y_m': expected['court_m'][1],
                             'status': mark['status'],
                             'x_px': '' if mark['x_px'] is None else mark['x_px'],
                             'y_px': '' if mark['y_px'] is None else mark['y_px'],
                             'note': mark['note']})
        temporary = output.with_suffix('.csv.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(output)
    return {'completed_csv': str(output), 'rows': len(rows),
            'calibration_approved': False}


def s1p6_fixed_manifest():
    return json.loads((S1P6_FIXED_PACK / 'manifest.json').read_text(encoding='utf-8'))


def s1p6_fixed_draft():
    path = S1P6_FIXED_PACK / 'draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'reviewer_code': 'MZ', 'frames': {},
            'scope': 'single_reviewer_source_only_fixed_window_review'}


@app.get('/s1p6-fixed-window-review')
def s1p6_fixed_review_page():
    return FileResponse(ROOT / 'web/s1p6_fixed_window_review.html')


@app.get('/s1p6_fixed_window_review.js')
def s1p6_fixed_review_js():
    return FileResponse(ROOT / 'web/s1p6_fixed_window_review.js', media_type='text/javascript')


@app.get('/api/u5/s1p6-fixed-window-review')
def s1p6_fixed_review_state():
    manifest = s1p6_fixed_manifest()
    frames = []
    for item in manifest['images']:
        path = S1P6_FIXED_PACK / item['image']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise HTTPException(409, 'Source image does not match frozen manifest')
        frames.append({'frame': item['source_frame'], 'image_url':
                       f"/api/u5/s1p6-fixed-window-review/source/{item['source_frame']}",
                       'sha256': item['sha256']})
    return {'frames': frames, 'draft': s1p6_fixed_draft(),
            'completed_csv_exists': (S1P6_FIXED_PACK / 'completed.csv').exists(),
            'window_start': manifest['window_start_frame_inclusive'],
            'window_end_exclusive': manifest['window_end_frame_exclusive']}


@app.get('/api/u5/s1p6-fixed-window-review/source/{frame}')
def s1p6_fixed_source_image(frame: int):
    manifest = s1p6_fixed_manifest()
    item = next((row for row in manifest['images'] if row['source_frame'] == frame), None)
    if item is None:
        raise HTTPException(404, 'Frame is outside frozen packet')
    path = S1P6_FIXED_PACK / item['image']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise HTTPException(409, 'Source image does not match frozen manifest')
    return FileResponse(path, media_type='image/png')


@app.put('/api/u5/s1p6-fixed-window-review/{frame}')
def s1p6_fixed_review_save(frame: int, payload: S1P6FixedSourceSave, request: Request):
    s3p34_check_origin(request)
    if not payload.reviewer_code.strip():
        raise HTTPException(422, 'Reviewer code cannot be blank')
    if frame not in {row['source_frame'] for row in s1p6_fixed_manifest()['images']}:
        raise HTTPException(404, 'Frame is outside frozen packet')
    if [row.slot for row in payload.rows] != [1, 2, 3, 4, 5, 6]:
        raise HTTPException(422, 'Six slot rows must remain in frozen order')
    for row in payload.rows:
        if (row.shoe_x_px is None) != (row.shoe_y_px is None):
            raise HTTPException(422, f'Slot {row.slot} needs both pixel coordinates or neither')
        if row.identity_status == 'absent' and row.ground_status not in ('occluded', 'uncertain'):
            raise HTTPException(422, f'Absent slot {row.slot} cannot have a grounded or airborne verdict')
        if row.shoe_x_px is not None:
            if (row.ground_status != 'grounded' or
                    not all(math.isfinite(v) for v in (row.shoe_x_px, row.shoe_y_px)) or
                    not 0 <= row.shoe_x_px < 1280 or not 0 <= row.shoe_y_px < 720):
                raise HTTPException(422, f'Invalid shoe mark for slot {row.slot}')
    with SAVE_LOCK:
        if (S1P6_FIXED_PACK / 'completed.csv').exists():
            raise HTTPException(409, 'Completed source review already frozen')
        data = s1p6_fixed_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'Another tab saved a newer revision; reload first')
        prior = data['frames'].get(str(frame))
        data['frames'][str(frame)] = {
            'source_phase': payload.source_phase,
            'rows': [row.model_dump() for row in payload.rows],
            'saved_at_utc': datetime.now(timezone.utc).isoformat()}
        data['reviewer_code'] = payload.reviewer_code.strip()
        data['revision'] += 1
        history = S1P6_FIXED_PACK / 'history'
        history.mkdir(exist_ok=True)
        (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps({
            'frame': frame, 'previous': prior, 'current': data['frames'][str(frame)],
            'revision': data['revision']}, indent=2) + '\n', encoding='utf-8')
        temporary = S1P6_FIXED_PACK / 'draft.json.tmp'
        temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        temporary.replace(S1P6_FIXED_PACK / 'draft.json')
    return {'draft': data}


@app.post('/api/u5/s1p6-fixed-window-review/export')
def s1p6_fixed_review_export(request: Request):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        manifest = s1p6_fixed_manifest()
        data = s1p6_fixed_draft()
        if any(str(item['source_frame']) not in data['frames'] for item in manifest['images']):
            raise HTTPException(409, 'Save all five source frames first')
        target = S1P6_FIXED_PACK / 'completed.csv'
        if target.exists():
            raise HTTPException(409, 'Completed source review already frozen')
        output = []
        for item in manifest['images']:
            saved = data['frames'][str(item['source_frame'])]
            for slot, row in enumerate(saved['rows'], start=1):
                if row['slot'] != slot:
                    raise HTTPException(409, 'Slot order changed after save')
                output.append({'source_frame': item['source_frame'],
                               'image_sha256': item['sha256'],
                               'source_phase': saved['source_phase'],
                               'slot': slot, 'identity_status': row['identity_status'],
                               'ground_status': row['ground_status'],
                               'shoe_x_px': '' if row['shoe_x_px'] is None else row['shoe_x_px'],
                               'shoe_y_px': '' if row['shoe_y_px'] is None else row['shoe_y_px'],
                               'note': row['note']})
        temporary = S1P6_FIXED_PACK / 'completed.csv.tmp'
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=output[0].keys())
            writer.writeheader()
            writer.writerows(output)
        temporary.replace(target)
    return {'rows': len(output), 'strict_metric_approval': False}


def s1p6_paired_inputs():
    source = S1P6_FIXED_PACK / 'completed.csv'
    detector = S1P6_FIXED_PACK / 'exact_30fps_candidates.json'
    joined = S1P6_FIXED_PACK / 'joined_diagnostic.json'
    if not all(path.is_file() for path in (source, detector, joined)):
        raise HTTPException(409, 'Freeze source review and run exact-frame diagnostic first')
    detection_data = json.loads(detector.read_text(encoding='utf-8'))
    join_data = json.loads(joined.read_text(encoding='utf-8'))
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if (detection_data['input_sha256']['source_review'] != source_hash or
            join_data['input_sha256']['completed_source_review'] != source_hash or
            join_data['input_sha256']['exact_30fps_candidates'] != hashlib.sha256(detector.read_bytes()).hexdigest()):
        raise HTTPException(409, 'Paired inputs changed after the diagnostic')
    with source.open(newline='', encoding='utf-8') as handle:
        source_rows = list(csv.DictReader(handle))
    return source_rows, detection_data, join_data


def s1p6_paired_draft():
    path = S1P6_FIXED_PACK / 'paired_draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'reviewer_code': '', 'frames': {},
            'scope': 'single_reviewer_after_source_freeze_box_comparison',
            'strict_metric_approval': False}


@app.get('/s1p6-paired-review')
def s1p6_paired_review_page():
    return FileResponse(ROOT / 'web/s1p6_paired_review.html')


@app.get('/s1p6_paired_review.js')
def s1p6_paired_review_js():
    return FileResponse(ROOT / 'web/s1p6_paired_review.js', media_type='text/javascript')


@app.get('/api/u5/s1p6-paired-review')
def s1p6_paired_review_state():
    source_rows, detection_data, join_data = s1p6_paired_inputs()
    detector_by_frame = {row['source_frame']: row for row in detection_data['rows']}
    joined_by_frame = {row['source_frame']: row for row in join_data['rows']}
    frames = []
    for item in s1p6_fixed_manifest()['images']:
        frame = item['source_frame']
        path = S1P6_FIXED_PACK / item['image']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise HTTPException(409, 'Source image changed')
        marks = [row for row in source_rows if int(row['source_frame']) == frame]
        if len(marks) != 6:
            raise HTTPException(409, 'Incomplete frozen source rows')
        frames.append({'frame': frame,
                       'source_image_url': f'/api/u5/s1p6-fixed-window-review/source/{frame}',
                       'source_rows': marks,
                       'detections': detector_by_frame[frame]['detections'],
                       'proximity_pairs': joined_by_frame[frame]['pairings']})
    return {'frames': frames, 'draft': s1p6_paired_draft(),
            'completed_csv_exists': (S1P6_FIXED_PACK / 'paired_completed.csv').exists(),
            'diagnostic_alert_px': join_data['diagnostic_pair_alert_px']}


@app.put('/api/u5/s1p6-paired-review/{frame}')
def s1p6_paired_review_save(frame: int, payload: S1P6PairedSave, request: Request):
    s3p34_check_origin(request)
    if not payload.reviewer_code.strip():
        raise HTTPException(422, 'Reviewer code cannot be blank')
    if not payload.checked_source_and_boxes:
        raise HTTPException(422, 'Confirm that the source and boxes were visually checked')
    if [row.slot for row in payload.rows] != [1, 2, 3, 4, 5, 6]:
        raise HTTPException(422, 'Six slot rows must remain in frozen order')
    source_rows, detection_data, _ = s1p6_paired_inputs()
    detector_row = next((row for row in detection_data['rows'] if row['source_frame'] == frame), None)
    if detector_row is None or frame not in s1p6_fixed_manifest()['five_sample_frames']:
        raise HTTPException(404, 'Frame is outside the paired review')
    valid_ids = {row['raw_track_id'] for row in detector_row['detections']}
    source_by_slot = {int(row['slot']): row for row in source_rows if int(row['source_frame']) == frame}
    same_ids = []
    for row in payload.rows:
        if row.candidate_alignment == 'no_box':
            if row.raw_track_id is not None or row.floor_alignment != 'not_applicable':
                raise HTTPException(422, f'Slot {row.slot}: no box requires no ID or floor claim')
        elif row.raw_track_id not in valid_ids:
            raise HTTPException(422, f'Slot {row.slot}: select an actual detector ID')
        if source_by_slot[row.slot]['ground_status'] != 'grounded' and row.floor_alignment != 'not_applicable':
            raise HTTPException(422, f'Slot {row.slot}: airborne or uncertain source has no floor verdict')
        if row.candidate_alignment != 'same_player' and row.floor_alignment == 'plausible':
            raise HTTPException(422, f'Slot {row.slot}: plausible floor proxy needs the same player')
        if row.candidate_alignment == 'same_player':
            same_ids.append(row.raw_track_id)
    if len(set(same_ids)) != len(same_ids):
        raise HTTPException(422, 'The same box cannot represent two source players')
    with SAVE_LOCK:
        if (S1P6_FIXED_PACK / 'paired_completed.csv').exists():
            raise HTTPException(409, 'Paired review is already frozen')
        data = s1p6_paired_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'Another tab saved a newer revision; reload first')
        prior = data['frames'].get(str(frame))
        data['frames'][str(frame)] = {'rows': [row.model_dump() for row in payload.rows],
                                      'saved_at_utc': datetime.now(timezone.utc).isoformat()}
        data['reviewer_code'] = payload.reviewer_code.strip()
        data['revision'] += 1
        history = S1P6_FIXED_PACK / 'paired_history'
        history.mkdir(exist_ok=True)
        (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps({
            'frame': frame, 'previous': prior, 'current': data['frames'][str(frame)],
            'revision': data['revision']}, indent=2) + '\n', encoding='utf-8')
        target = S1P6_FIXED_PACK / 'paired_draft.json'
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        temporary.replace(target)
    return {'draft': data}


@app.post('/api/u5/s1p6-paired-review/export')
def s1p6_paired_review_export(request: Request):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        source_rows, detection_data, _ = s1p6_paired_inputs()
        data = s1p6_paired_draft()
        frames = s1p6_fixed_manifest()['five_sample_frames']
        if any(str(frame) not in data['frames'] for frame in frames):
            raise HTTPException(409, 'Save every paired frame first')
        target = S1P6_FIXED_PACK / 'paired_completed.csv'
        if target.exists():
            raise HTTPException(409, 'Paired review already frozen')
        output = []
        source_by_key = {(int(row['source_frame']), int(row['slot'])): row for row in source_rows}
        for frame in frames:
            for row in data['frames'][str(frame)]['rows']:
                source_row = source_by_key[(frame, row['slot'])]
                output.append({'source_frame': frame, 'slot': row['slot'],
                               'source_image_sha256': source_row['image_sha256'],
                               'source_review_sha256': hashlib.sha256((S1P6_FIXED_PACK / 'completed.csv').read_bytes()).hexdigest(),
                               'detector_sha256': hashlib.sha256((S1P6_FIXED_PACK / 'exact_30fps_candidates.json').read_bytes()).hexdigest(),
                               'ground_status': source_row['ground_status'],
                               'shoe_x_px': source_row['shoe_x_px'], 'shoe_y_px': source_row['shoe_y_px'],
                               'raw_track_id': '' if row['raw_track_id'] is None else row['raw_track_id'],
                               'candidate_alignment': row['candidate_alignment'],
                               'floor_alignment': row['floor_alignment'], 'note': row['note']})
        temporary = target.with_suffix('.csv.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=output[0].keys())
            writer.writeheader()
            writer.writerows(output)
        temporary.replace(target)
    return {'rows': len(output), 'strict_metric_approval': False}


def s1p6_calibration_protocol():
    return json.loads((S1P6_CALIBRATION_PACK / 'protocol.json').read_text(encoding='utf-8'))


def s1p6_calibration_draft():
    path = S1P6_CALIBRATION_PACK / 'draft.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'revision': 0, 'reviewer_code': '', 'frames': {},
            'scope': 'out_of_point_single_reviewer_source_only_calibration_check',
            'strict_metric_approval': False}


@app.get('/s1p6-calibration-review')
def s1p6_calibration_review_page():
    page = (ROOT / 'web/s3p34_calibration_review.html').read_text(encoding='utf-8')
    page = page.replace('<body>', '<body data-api="/api/u5/s1p6-calibration-review">')
    page = page.replace('<a href="/s3p34-ground-review">Ground review</a>', '')
    page = page.replace('<button id="next" type="button">Next</button>',
                        '<button id="next" type="button">Next</button>'
                        '<button id="copyFirst" type="button" hidden>Use first frame as starting points</button>')
    page = page.replace('S3 P34', 'S1 P6').replace('s3p34_calibration_review.js?v=1',
                                               's3p34_calibration_review.js?v=4')
    return HTMLResponse(page)


@app.get('/api/u5/s1p6-calibration-review')
def s1p6_calibration_review_state():
    protocol = s1p6_calibration_protocol()
    frames = []
    for item in protocol['frames']:
        path = S1P6_FIXED_PACK / item['image']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise HTTPException(409, 'Calibration source image does not match frozen hash')
        frames.append({'frame': item['frame'], 'image_url':
                       f"/api/u5/s1p6-fixed-window-review/source/{item['frame']}",
                       'image_sha256': item['sha256']})
    return {'frames': frames, 'landmarks': protocol['landmarks'],
            'protocol_sha256': hashlib.sha256((S1P6_CALIBRATION_PACK / 'protocol.json').read_bytes()).hexdigest(),
            'draft': s1p6_calibration_draft(),
            'completed_csv_exists': (S1P6_CALIBRATION_PACK / 'completed.csv').exists()}


@app.put('/api/u5/s1p6-calibration-review/{frame}')
def s1p6_calibration_review_save(frame: int, payload: S3P34CalibrationSave, request: Request):
    s3p34_check_origin(request)
    if not payload.reviewer_code.strip():
        raise HTTPException(422, 'Reviewer code cannot be blank')
    protocol = s1p6_calibration_protocol()
    if frame not in {item['frame'] for item in protocol['frames']}:
        raise HTTPException(404, 'Frame is outside frozen calibration check')
    if [row.code for row in payload.rows] != list(S3P34_CALIBRATION_CODES):
        raise HTTPException(422, 'Landmark rows must remain in frozen order')
    for row in payload.rows:
        if row.status == 'marked':
            if (row.x_px is None or row.y_px is None or
                    not all(math.isfinite(value) for value in (row.x_px, row.y_px)) or
                    not 0 <= row.x_px < 1280 or not 0 <= row.y_px < 720):
                raise HTTPException(422, f'Invalid pixel mark for {row.code}')
        elif row.x_px is not None or row.y_px is not None:
            raise HTTPException(422, f'Uncertain landmark {row.code} must have null coordinates')
    with SAVE_LOCK:
        if (S1P6_CALIBRATION_PACK / 'completed.csv').exists():
            raise HTTPException(409, 'Completed calibration check already frozen')
        data = s1p6_calibration_draft()
        if data['revision'] != payload.expected_revision:
            raise HTTPException(409, 'Another tab saved a newer revision; reload first')
        previous = data['frames'].get(str(frame))
        data['frames'][str(frame)] = {'rows': [row.model_dump() for row in payload.rows],
                                      'saved_at_utc': datetime.now(timezone.utc).isoformat()}
        data['reviewer_code'] = payload.reviewer_code.strip()
        data['revision'] += 1
        history = S1P6_CALIBRATION_PACK / 'history'
        history.mkdir(exist_ok=True)
        (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps({
            'frame': frame, 'previous': previous, 'current': data['frames'][str(frame)],
            'revision': data['revision']}, indent=2) + '\n', encoding='utf-8')
        target = S1P6_CALIBRATION_PACK / 'draft.json'
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        temporary.replace(target)
    return {'draft': data}


@app.post('/api/u5/s1p6-calibration-review/export')
def s1p6_calibration_review_export(request: Request):
    s3p34_check_origin(request)
    with SAVE_LOCK:
        protocol = s1p6_calibration_protocol()
        data = s1p6_calibration_draft()
        if any(str(item['frame']) not in data['frames'] for item in protocol['frames']):
            raise HTTPException(409, 'Save both source landmark frames first')
        output = S1P6_CALIBRATION_PACK / 'completed.csv'
        if output.exists():
            raise HTTPException(409, 'Completed calibration check already frozen')
        rows = []
        for item in protocol['frames']:
            for expected, mark in zip(protocol['landmarks'],
                                      data['frames'][str(item['frame'])]['rows'], strict=True):
                if mark['code'] != expected['code']:
                    raise HTTPException(409, 'Landmark order changed after save')
                if str(mark.get('note', '')).startswith('copied_from_frame_1759'):
                    raise HTTPException(409, 'Confirm each copied point by clicking its intersection on the second source image')
                rows.append({'source_frame': item['frame'], 'image': item['image'],
                             'image_sha256': item['sha256'], 'landmark_code': expected['code'],
                             'court_x_m': expected['court_m'][0], 'court_y_m': expected['court_m'][1],
                             'status': mark['status'],
                             'x_px': '' if mark['x_px'] is None else mark['x_px'],
                             'y_px': '' if mark['y_px'] is None else mark['y_px'],
                             'note': mark['note']})
        temporary = output.with_suffix('.csv.tmp')
        with temporary.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(output)
    return {'rows': len(rows), 'calibration_approved': False}


def honours_sample_id(rally_id):
    return bool(re.fullmatch(r'hs_s[1-3]_p[1-9][0-9]*', rally_id))


def load_match(match_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', match_id):
        raise HTTPException(400, 'Invalid match ID')
    directory = (MATCHES / match_id).resolve()
    if not directory.is_relative_to(MATCHES.resolve()):
        raise HTTPException(400, 'Invalid match directory')
    try:
        source = json.loads((directory / 'source_record.json').read_text(encoding='utf-8'))
        selection = json.loads((directory / 'pilot/selection.json').read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise HTTPException(404, 'Pilot selection is not prepared for this match')
    video = (ROOT / source['video_file']).resolve()
    if not video.is_relative_to(directory) or not video.is_file():
        raise HTTPException(404, 'Source video not available')
    return directory, source, selection, video


@app.get('/')
def page():
    return FileResponse(ROOT / 'web/pilot_review.html')


@app.get('/pilot_review.js')
def javascript():
    return FileResponse(ROOT / 'web/pilot_review.js', media_type='text/javascript')


@app.get('/match-score')
def match_score_page():
    return FileResponse(ROOT / 'web/match_score.html')


@app.get('/match_score.js')
def match_score_javascript():
    return FileResponse(ROOT / 'web/match_score.js', media_type='text/javascript')


@app.get('/api/primary-match/score-review')
def primary_match_score_review():
    match_id = 'yt_FqE5pTJqx8g'
    directory, source, _, _ = load_match(match_id)
    queue_path = ROOT / 'data/processed/fqe_rally_review_queue.json'
    if not queue_path.is_file():
        raise HTTPException(404, 'Full-match score review queue is not prepared')
    queue = json.loads(queue_path.read_text(encoding='utf-8'))
    if queue['match_id'] != match_id or queue['source_sha256'] != source['sha256']:
        raise HTTPException(409, 'Score queue does not match the source video')
    saved_path = directory / 'full_match_boundary_review.json'
    saved = json.loads(saved_path.read_text(encoding='utf-8')) if saved_path.exists() else {}
    saved_qc = {}
    for row in queue['rows']:
        key = f"s{row['set']}_p{row['point_number']}"
        record = saved.get(key)
        if record and row.get('score_flip_frame') is not None and record['end_frame_exclusive'] >= row['score_flip_frame']:
            saved_qc[key] = ['saved_end_on_or_after_score_change_recheck_source']
    candidates_path = ROOT / 'data/processed/fqe_boundary_source_candidates.json'
    candidates = json.loads(candidates_path.read_text(encoding='utf-8')) if candidates_path.exists() else None
    if candidates and (candidates['match_id'] != match_id or candidates['source_sha256'] != source['sha256']):
        raise HTTPException(409, 'Source boundary candidates do not match this video')
    if candidates:
        for key, candidate in candidates['candidates'].items():
            record = saved.get(key)
            if record and not (candidate['end_contact_interval_frames'][0]
                               <= record['end_frame_exclusive'] <= candidate['end_contact_interval_frames'][1]):
                saved_qc.setdefault(key, []).append('saved_end_outside_source_screened_range_recheck')
            start_interval = candidate.get('start_contact_interval_frames')
            if record and start_interval and not (record.get('start_frame') is not None
                                                  and start_interval[0] <= record['start_frame'] <= start_interval[1]):
                saved_qc.setdefault(key, []).append('saved_start_outside_source_screened_range_recheck')
    audio_path = ROOT / 'data/processed/fqe_audio_serve_probe.json'
    audio = json.loads(audio_path.read_text(encoding='utf-8')) if audio_path.exists() else None
    if audio and (audio['match_id'] != match_id or audio['source_sha256'] != source['sha256']):
        raise HTTPException(409, 'Audio serve probe does not match this video')
    return {'source': {'match_id': match_id, 'source_title': source['source_title'],
                       'frame_count': source['frame_count'], 'fps': source['camera']['fps']},
            'queue': queue, 'saved': saved, 'saved_qc': saved_qc,
            'source_candidates': candidates['candidates'] if candidates else {},
            'audio_probe': audio}


@app.get('/api/primary-match/score-review/audio-probe/{segment}')
def primary_match_audio_probe(segment: Literal['early', 'next']):
    probe = primary_match_score_review()['audio_probe']
    if not probe or segment not in probe['segments']:
        raise HTTPException(404, 'Audio probe is unavailable')
    file = (ROOT / probe['segments'][segment]['file']).resolve()
    if not file.is_relative_to((ROOT / 'data/processed').resolve()) or not file.is_file():
        raise HTTPException(404, 'Audio excerpt is unavailable')
    return FileResponse(file, media_type='video/mp4')


@app.get('/api/primary-match/score-review/{set_number}/{point_number}/filmstrip/{kind}')
def primary_match_filmstrip(set_number: int, point_number: int,
                            kind: Literal['start', 'end']):
    payload = primary_match_score_review()
    row = next((item for item in payload['queue']['rows']
                if item['set'] == set_number and item['point_number'] == point_number), None)
    if row is None:
        raise HTTPException(404, 'Unknown scored point')
    key = f's{set_number}_p{point_number}'
    saved = payload['saved'].get(key)
    candidate = payload['source_candidates'].get(key)
    if kind == 'end':
        if candidate:
            centre = candidate['suggested_end_frame_exclusive']
            first = candidate['end_contact_interval_frames'][0] - 40
            last = candidate['end_contact_interval_frames'][1] + 40
        else:
            centre = saved['end_frame_exclusive'] if saved else (row['estimated_end_frame_exclusive'] or row['end_frame_exclusive'])
            first = row['end_review_from_frame'] if row['end_review_from_frame'] is not None else centre - 150
            last = row['end_review_to_frame'] if row['end_review_to_frame'] is not None else centre + 150
    else:
        if candidate and candidate.get('start_contact_interval_frames'):
            centre = candidate['suggested_start_frame']
            first = candidate['start_contact_interval_frames'][0] - 16
            last = candidate['start_contact_interval_frames'][1] + 16
        else:
            centre = (saved or {}).get('start_frame') or row['estimated_start_frame'] or row['serve_contact_frame']
            first, last = centre - 250, centre + 250
    first = max(0, first)
    last = min(payload['source']['frame_count'] - 1, last)
    if first >= last:
        raise HTTPException(422, 'No source frames available for this review strip')
    indices = [round(first + (last - first) * index / 8) for index in range(9)]
    canvas = Image.new('RGB', (1440, 846), '#14202e')
    draw = ImageDraw.Draw(canvas)
    video_path = str(MATCHES / 'yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4')
    for index, frame_number in enumerate(indices):
        source_frame = Image.open(io.BytesIO(decode_frame(video_path, frame_number)))
        source_frame.thumbnail((480, 270))
        x, y = (index % 3) * 480, (index // 3) * 282
        canvas.paste(source_frame, (x, y))
        draw.text((x + 8, y + 265), f'Frame {frame_number}  ({frame_number / payload["source"]["fps"]:.2f}s)', fill='white')
    encoded = io.BytesIO()
    canvas.save(encoded, format='JPEG', quality=88)
    return Response(encoded.getvalue(), media_type='image/jpeg',
                    headers={'Cache-Control': 'private, max-age=300',
                             'X-Frame-Indices': ','.join(map(str, indices))})


class FullMatchBoundaryReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start_frame: int | None = Field(default=None, ge=0, strict=True)
    end_frame_exclusive: int = Field(gt=0, strict=True)
    annotator_id: str = Field(min_length=1, max_length=80)
    notes: str = Field(default='', max_length=4000)
    serve_position: Literal['behind_near_end_line', 'behind_far_end_line', 'off_camera', 'uncertain'] = 'uncertain'
    serve_contact_status: Literal['source_visible', 'off_camera', 'uncertain'] = 'source_visible'
    source_frames_checked: bool = Field(default=False, strict=True)


@app.put('/api/primary-match/score-review/{set_number}/{point_number}')
def save_primary_match_score_review(set_number: int, point_number: int,
                                    review: FullMatchBoundaryReview, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin writes are not allowed')
    payload = primary_match_score_review()
    row = next((row for row in payload['queue']['rows']
                if row['set'] == set_number and row['point_number'] == point_number), None)
    if row is None:
        raise HTTPException(404, 'Unknown scored point')
    if row['pilot_rally_id']:
        raise HTTPException(409, 'Pilot boundaries are saved in the pilot review workspace')
    if not review.annotator_id.strip():
        raise HTTPException(422, 'Enter your annotator code')
    if not review.source_frames_checked:
        raise HTTPException(422, 'Check the serve and ending in source frames before saving')
    source = payload['source']
    if review.serve_contact_status == 'source_visible':
        if review.start_frame is None:
            raise HTTPException(422, 'Visible serve contact needs a source frame')
    elif review.start_frame is not None:
        raise HTTPException(422, 'Leave the serve frame empty when contact is not visible')
    if not (0 < review.end_frame_exclusive <= source['frame_count']
            and (review.start_frame is None or review.start_frame < review.end_frame_exclusive)):
        raise HTTPException(422, 'Boundaries must be ordered and inside the source video')
    # The seek window is heuristic. Permit nearby frames while limiting
    # accidental saves from a different point or set break.
    if not ((review.start_frame is None or row['seek_from_frame'] - 750 <= review.start_frame)
            and review.end_frame_exclusive <= row['seek_to_frame_exclusive'] + 500
            and (review.start_frame is None or review.end_frame_exclusive - review.start_frame <= 9000)):
        raise HTTPException(422, 'Boundaries are too far from this point’s score review window')
    if row.get('score_flip_frame') is not None and review.end_frame_exclusive >= row['score_flip_frame']:
        raise HTTPException(422, 'The selected end is on or after the score changed; inspect earlier source frames')
    key = f's{set_number}_p{point_number}'
    record = review.model_dump()
    record.update(annotator_id=review.annotator_id.strip(), set=set_number,
                  point_number=point_number, score_before=row['score_before'],
                  score_after=row['score_after'], source_sha256=payload['queue']['source_sha256'],
                  boundary_status=('checked_by_annotator' if review.start_frame is not None
                                   else 'partial_source_review_serve_unobservable'),
                  independent_review_status='pending',
                  saved_at=datetime.now(timezone.utc).isoformat())
    directory = MATCHES / 'yt_FqE5pTJqx8g'
    path = directory / 'full_match_boundary_review.json'
    with SAVE_LOCK:
        saved = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        history = directory / 'full_match_boundary_history'
        history.mkdir(exist_ok=True)
        event = {'point_key': key, 'previous': saved.get(key), 'current': record}
        (history / f'{uuid.uuid4().hex}.json').write_text(
            json.dumps(event, indent=2) + '\n', encoding='utf-8')
        saved[key] = record
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    return record


@app.get('/players')
def players_page():
    return FileResponse(ROOT / 'web/player_annotation.html')


@app.get('/honours-sample', response_class=HTMLResponse)
def honours_sample_page():
    manifest_path = ROOT / HONOURS_WORKSPACE / 'manifest.json'
    if not manifest_path.exists():
        raise HTTPException(404, 'Prepare the frozen sample review queue first')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    rows = []
    for point in manifest['points']:
        rally_id = point['rally_id']
        pilot = point.get('review_source') == 'existing_pilot'
        saved_path = (ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations' / f'{rally_id}.json'
                      if pilot else ROOT / HONOURS_WORKSPACE / 'player_annotations' / f'{rally_id}.json')
        saved = json.loads(saved_path.read_text(encoding='utf-8')) if saved_path.exists() else {'frames': {}}
        count = len(saved.get('frames', {}))
        total = len(json.loads((ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_drafts' / f'{rally_id}.json').read_text(encoding='utf-8'))['frames']) if pilot else len(point['navigation_frames'])
        link = f"/players?match={html.escape(manifest['match_id'])}&amp;rally={html.escape(rally_id)}"
        rows.append(f"<tr><td><a href='{link}'>Set {point['set']}, point {point['point_number']}</a></td>"
                    f"<td>{html.escape(point['winner'])}</td><td>{count}/{total} saved</td>"
                    f"<td>{html.escape(point['boundary_status'])}</td></tr>")
    body = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Honours sample review</title>'
    body += '<style>body{font:16px system-ui;max-width:960px;margin:2rem auto;padding:0 1rem}'
    body += 'table{border-collapse:collapse;width:100%}td,th{padding:.55rem;border:1px solid #ccc;text-align:left}</style>'
    body += '<h1>Earlier labels and frozen sample</h1><p>You already labelled five pilot rallies. '
    body += 'The later score-selected sample overlaps the pilot only at R2; keep the earlier work. '
    body += 'The 18-point queue is a separate comparison design, not a request to redo pilot labels.</p>'
    pilot_selection = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/selection.json'
    if pilot_selection.exists():
        pilot_rows = []
        for rally in json.loads(pilot_selection.read_text(encoding='utf-8'))['rallies']:
            pilot_id = rally['rally_id']
            pilot_file = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations' / f'{pilot_id}.json'
            saved_frames = json.loads(pilot_file.read_text(encoding='utf-8')).get('frames', {}) if pilot_file.exists() else {}
            score_point = rally.get('rally_index_inferred_from_score', '?')
            overlap = 'Yes' if any(p['rally_id'] == pilot_id for p in manifest['points']) else 'No'
            pilot_rows.append(f"<tr><td><a href='/players?match=yt_FqE5pTJqx8g&amp;rally={html.escape(pilot_id)}'>{html.escape(pilot_id)}</a></td>"
                              f"<td>Set {rally['set_number']}, point {score_point}</td><td>{len(saved_frames)} labelled</td><td>{overlap}</td></tr>")
        body += '<h2>Existing pilot work</h2><table><tr><th>Rally</th><th>Score position</th><th>Saved frames</th><th>In frozen sample?</th></tr>'
        body += ''.join(pilot_rows) + '</table>'
    body += '<h2>Frozen 18-point comparison sample</h2><p>Grey detector boxes are unverified suggestions. '
    body += 'Check the source video, assign only the near-side team, and click visible floor contacts. '
    body += 'A saved frame is not an independently reviewed metric frame. Navigation windows are not rally boundaries.</p>'
    body += '<table><tr><th>Point</th><th>Winner</th><th>Review frames</th><th>Boundary status</th></tr>'
    return HTMLResponse(body + ''.join(rows) + '</table></html>')


@app.get('/player_annotation.js')
def players_javascript():
    return FileResponse(ROOT / 'web/player_annotation.js', media_type='text/javascript')


@app.get('/r1-case-study')
def r1_case_study_page():
    return FileResponse(ROOT / 'web/r1_case_study.html')


@app.get('/d79-case-study')
def d79_case_study_page():
    return FileResponse(ROOT / 'web/d79_case_study.html')


@app.get('/d79_case_study.js')
def d79_case_study_javascript():
    return FileResponse(ROOT / 'web/d79_case_study.js', media_type='text/javascript')


@app.get('/api/case-studies/d79/seeded-holds')
def d79_seeded_holds():
    path = D79_CASE_STUDY / 'seeded_hold_viewer_record.json'
    if not path.is_file():
        raise HTTPException(404, 'D79 seeded hold record is unavailable')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/case-studies')
def case_studies_page():
    return FileResponse(ROOT / 'web/case_studies.html')


@app.get('/case_studies.js')
def case_studies_javascript():
    return FileResponse(ROOT / 'web/case_studies.js', media_type='text/javascript')


@app.get('/api/case-studies/catalog')
def case_studies_catalog():
    if not CASE_STUDY_CATALOG.is_file():
        raise HTTPException(404, 'Case-study catalog is unavailable')
    return FileResponse(CASE_STUDY_CATALOG, media_type='application/json',
                        headers={'Cache-Control': 'no-store'})


@app.get('/api/case-studies/aoep/court-map')
def aoep_case_study_court_map():
    path = AOEP_CASE_STUDY / 'candidate_court_paths_75180_75229_7e8d7ea5cd.jpg'
    if not path.is_file():
        raise HTTPException(404, 'AoEP court map is unavailable')
    return FileResponse(path, media_type='image/jpeg')


@app.get('/r1_case_study.js')
def r1_case_study_javascript():
    return FileResponse(ROOT / 'web/r1_case_study.js', media_type='text/javascript')


@app.get('/api/case-studies/r1/record')
def r1_case_study_record():
    path = R1_CASE_STUDY / 'r1_six_slot_visual_candidate.json'
    if not path.is_file():
        raise HTTPException(404, 'R1 case-study record is unavailable')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/api/case-studies/r1/occlusion-holds')
def r1_occlusion_display_holds():
    path = R1_CASE_STUDY / 'r1_occlusion_display_holds.json'
    if not path.is_file():
        raise HTTPException(404, 'R1 occlusion display holds are unavailable')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/api/case-studies/r1/shoe-cues')
def r1_shoe_cues():
    path = R1_CASE_STUDY / 'r1_p20_body_shoe_contact_trial.json'
    if not path.is_file():
        raise HTTPException(404, 'R1 shoe review cues are unavailable')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/api/case-studies/r1/foot-centre-distance')
def r1_foot_centre_distance():
    path = R1_CASE_STUDY / 'r1_p20_foot_level_center_distance_trial.json'
    if not path.is_file():
        raise HTTPException(404, 'R1 foot-level centre estimate is unavailable')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/api/case-studies/r1/point-summary')
def r1_point_summary():
    path = R1_CASE_STUDY / 'r1_point_summary.json'
    if not path.is_file():
        raise HTTPException(404, 'R1 point summary is unavailable')
    return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})


@app.get('/api/case-studies/r1/net-line')
def r1_case_study_net_line():
    path = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/calibration_manifest.json'
    if not path.is_file():
        raise HTTPException(404, 'R1 held-out net line is unavailable')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    line = manifest['camera_segments']['camera_r1']['heldout_net_line_px']
    if manifest['match_id'] != 'yt_FqE5pTJqx8g' or len(line) != 4 or not all(
            isinstance(value, (int, float)) and math.isfinite(value) for value in line):
        raise HTTPException(500, 'R1 held-out net line is invalid')
    return {'status': 'staged_calibration_line_for_visual_review', 'net_line_px': line,
            'source': 'calibration_manifest.json; median calibration frames',
            'court_position_certified': False}


@app.get('/api/case-studies/r1/preview')
def r1_case_study_preview():
    path = R1_CASE_STUDY / 'r1_visual_candidate_preview.mp4'
    if not path.is_file():
        raise HTTPException(404, 'R1 case-study preview is unavailable')
    return FileResponse(path, media_type='video/mp4', headers={'Cache-Control': 'private, max-age=3600'})


class R1FloorContact(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reviewer_id: str = Field(min_length=1, max_length=80)
    state: Literal['grounded_contact_visible', 'airborne', 'feet_hidden', 'out_of_frame', 'uncertain']
    footpoint_px: list[float] | None = None
    note: str = Field(default='', max_length=2000)


@app.get('/api/case-studies/r1/floor-review')
def r1_floor_review():
    path = R1_CASE_STUDY / 'r1_floor_contact_review.json'
    if path.is_file():
        return FileResponse(path, media_type='application/json', headers={'Cache-Control': 'no-store'})
    return {'status': 'single_reviewer_manual_floor_contact_draft',
            'match_id': 'yt_FqE5pTJqx8g', 'rally_id': 'r1', 'records': {},
            'official_annotations_changed': False, 'production_metric_changed': False}


@app.put('/api/case-studies/r1/floor-review/{frame_index}/{player_id}')
def save_r1_floor_contact(frame_index: int, player_id: str, payload: R1FloorContact, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin writes are not allowed')
    if not 21050 <= frame_index < 21464 or player_id not in {'9', '10', '11', '12', '13', '20'}:
        raise HTTPException(422, 'Frame or player outside the r1 candidate')
    if not payload.reviewer_id.strip():
        raise HTTPException(422, 'A reviewer code is required')
    _, source, _, _ = load_match('yt_FqE5pTJqx8g')
    width, height = source['camera']['width'], source['camera']['height']
    point = payload.footpoint_px
    if payload.state == 'grounded_contact_visible':
        if point is None or len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point):
            raise HTTPException(422, 'A grounded contact needs one finite source-pixel point')
        if not 0 <= point[0] < width or not 0 <= point[1] < height:
            raise HTTPException(422, 'Floor point outside the source frame')
    elif point is not None:
        raise HTTPException(422, 'Only a visible grounded contact may have a floor point')

    path = R1_CASE_STUDY / 'r1_floor_contact_review.json'
    with SAVE_LOCK:
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
            'status': 'single_reviewer_manual_floor_contact_draft',
            'match_id': 'yt_FqE5pTJqx8g', 'rally_id': 'r1', 'records': {},
            'official_annotations_changed': False, 'production_metric_changed': False}
        frame_records = data['records'].setdefault(str(frame_index), {})
        previous = frame_records.get(player_id)
        record = payload.model_dump()
        record['frame_index'] = frame_index
        record['player_id'] = player_id
        record['recorded_at_utc'] = datetime.now(timezone.utc).isoformat()
        frame_records[player_id] = record
        history = R1_CASE_STUDY / 'r1_floor_contact_history'
        history.mkdir(parents=True, exist_ok=True)
        revision = uuid.uuid4().hex
        event = {'revision': revision, 'previous': previous, 'current': record}
        (history / f'{revision}.json').write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
    return {'saved': record, 'revision': revision}


@app.get('/api/{match_id}/pilot')
def pilot(match_id: str):
    directory, source, selection, _ = load_match(match_id)
    saved = directory / 'pilot/boundary_review.json'
    return {'source': source, 'selection': selection,
            'reviews': json.loads(saved.read_text(encoding='utf-8')) if saved.exists() else {}}


@app.get('/api/{match_id}/video')
def video_file(match_id: str):
    return FileResponse(load_match(match_id)[3], media_type='video/mp4')


@lru_cache(maxsize=32)
def decode_frame(video_path, frame_index):
    cap = cv2.VideoCapture(video_path)
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_index + 1:
            raise HTTPException(422, 'Cannot decode the requested frame')
        ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            raise HTTPException(500, 'Frame encoding failed')
        return encoded.tobytes()
    finally:
        cap.release()


@app.get('/api/{match_id}/frame/{frame_index}')
def frame_image(match_id: str, frame_index: int):
    _, source, _, video = load_match(match_id)
    if not 0 <= frame_index < source['frame_count']:
        raise HTTPException(422, 'Frame outside the video')
    return Response(decode_frame(str(video), frame_index), media_type='image/jpeg',
                    headers={'X-Frame-Index': str(frame_index), 'Cache-Control': 'private, max-age=3600'})


class BoundaryReview(BaseModel):
    start_frame: int = Field(ge=0, strict=True)
    end_frame_exclusive: int = Field(gt=0, strict=True)
    annotator_id: str = Field(min_length=1, max_length=80)
    usable: bool
    notes: str = Field(default='', max_length=4000)


@app.put('/api/{match_id}/rallies/{rally_id}')
def save_review(match_id: str, rally_id: str, review: BoundaryReview, request: Request):
    # The application is local-only; reject cross-origin browser writes.
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin writes are not allowed')
    directory, source, selection, _ = load_match(match_id)
    rally = next((r for r in selection['rallies'] if r['rally_id'] == rally_id), None)
    if rally is None:
        raise HTTPException(404, 'Unknown selected rally')
    if not (rally['window_start_frame'] <= review.start_frame < review.end_frame_exclusive
            <= rally['window_end_frame_exclusive'] <= source['frame_count']):
        raise HTTPException(422, 'Boundaries must be ordered and inside the selected review window')
    if not review.annotator_id.strip():
        raise HTTPException(422, 'Enter your annotator code')
    if not review.usable and not review.notes.strip():
        raise HTTPException(422, 'Explain why the rally should be excluded')
    record = review.model_dump()
    record.update(annotator_id=review.annotator_id.strip(),
                  saved_at=datetime.now(timezone.utc).isoformat(),
                  boundary_status='checked_by_annotator', independent_review_status='pending')
    output = directory / 'pilot/boundary_review.json'
    with SAVE_LOCK:
        reviews = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
        history = directory / 'pilot/review_history'
        history.mkdir(exist_ok=True)
        event = dict(match_id=match_id, rally_id=rally_id, previous=reviews.get(rally_id), current=record)
        (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
        reviews[rally_id] = record
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(reviews, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)
    return record


class PlayerLabel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    player_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,60}$')
    team_id: Literal['home', 'away', 'unknown'] = 'unknown'
    bbox: tuple[float, float, float, float] | None = None
    occlusion: Literal['none', 'partial', 'full'] = 'none'
    position_status: Literal['visible', 'occluded', 'airborne', 'out_of_frame', 'uncertain'] = 'uncertain'
    footpoint: tuple[float, float] | None = None
    origin_proposal_id: str | None = None
    notes: str = Field(default='', max_length=1000)


class PlayerFrame(BaseModel):
    model_config = ConfigDict(extra='forbid')
    annotator_id: str = Field(min_length=1, max_length=80)
    all_players_accounted_for: bool = False
    proposal_displayed: bool = False
    notes: str = Field(default='', max_length=4000)
    players: list[PlayerLabel] = Field(max_length=30)


def load_player_draft(match_id, rally_id):
    directory, source, selection, video = load_match(match_id)
    if honours_sample_id(rally_id):
        if match_id != 'yt_FqE5pTJqx8g':
            raise HTTPException(404, 'Unknown honours sample match')
        manifest_path = ROOT / HONOURS_WORKSPACE / 'manifest.json'
        sample_path = ROOT / 'data/processed/honours_rally_sample.json'
        if not manifest_path.is_file() or not sample_path.is_file():
            raise HTTPException(404, 'Frozen sample review queue is not prepared')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('sample_sha256') != hashlib.sha256(sample_path.read_bytes()).hexdigest():
            raise HTTPException(409, 'Review queue does not match the frozen sample')
        if not any(p['rally_id'] == rally_id and p.get('review_source') == 'honours_workspace'
                   for p in manifest['points']):
            raise HTTPException(404, 'Point is not in the frozen sample review queue')
        path = ROOT / HONOURS_WORKSPACE / 'drafts' / f'{rally_id}.json'
        if not path.is_file():
            raise HTTPException(404, 'Point is not in the frozen sample review queue')
        draft = json.loads(path.read_text(encoding='utf-8'))
        if draft.get('source_sha256') != source.get('sha256'):
            raise HTTPException(409, 'Review draft does not match the source video')
        reviews = directory / 'full_match_boundary_review.json'
        point_id = draft['sample_point_id']
        saved_boundary = json.loads(reviews.read_text(encoding='utf-8')).get(point_id) if reviews.exists() else None
        checked = (saved_boundary and saved_boundary.get('boundary_status') == 'checked_by_annotator'
                   and isinstance(saved_boundary.get('start_frame'), int)
                   and isinstance(saved_boundary.get('end_frame_exclusive'), int))
        boundary = saved_boundary if checked else {
            'start_frame': draft['start_frame'], 'end_frame_exclusive': draft['end_frame_exclusive'],
            'boundary_status': 'navigation_window_not_reviewed'}
        stale = bool((checked and any(draft[k] != boundary[k] for k in ('start_frame', 'end_frame_exclusive')))
                     or (draft.get('boundary_status') == 'checked_by_annotator' and not checked))
        return directory, source, draft, boundary, stale
    rally = next((r for r in selection['rallies'] if r['rally_id'] == rally_id), None)
    if rally is None:
        raise HTTPException(404, 'Unknown rally')
    path = directory / 'pilot/player_drafts' / f'{rally_id}.json'
    if not path.exists():
        raise HTTPException(404, 'Player drafts are not prepared for this rally yet')
    draft = json.loads(path.read_text(encoding='utf-8'))
    reviews = directory / 'pilot/boundary_review.json'
    boundary = json.loads(reviews.read_text(encoding='utf-8')).get(rally_id, rally) if reviews.exists() else rally
    stale = (boundary.get('usable') is False or any(draft[k] != boundary[k] for k in ('start_frame', 'end_frame_exclusive')))
    return directory, source, draft, boundary, stale


def annotation_path(directory, rally_id, side):
    suffix = '' if side == 'near' else '_far'
    if honours_sample_id(rally_id):
        return ROOT / HONOURS_WORKSPACE / 'player_annotations' / f'{rally_id}{suffix}.json'
    return directory / 'pilot/player_annotations' / f'{rally_id}{suffix}.json'


def assisted_proposals(directory, rally_id, source, selection):
    path = directory / 'pilot/assisted_proposals' / f'{rally_id}.json'
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    if (payload.get('source_sha256') != source.get('sha256') or
            payload.get('raw_prediction_sha256') != selection.get('raw_prediction_sha256') or
            payload.get('rally_id') != rally_id):
        raise HTTPException(409, 'Assisted suggestions do not match the frozen source')
    return payload


@app.get('/api/{match_id}/players/{rally_id}/proposals/{frame_index}')
def frame_proposals(match_id: str, rally_id: str, frame_index: int):
    directory, source, draft, _, _ = load_player_draft(match_id, rally_id)
    selection = json.loads((directory / 'pilot/selection.json').read_text(encoding='utf-8'))
    proposals = assisted_proposals(directory, rally_id, source, selection)
    if proposals is None:
        raise HTTPException(404, 'No assisted suggestions for this rally')
    if not any(row['frame_index'] == frame_index for row in draft['frames']):
        raise HTTPException(422, 'Frame is not in the review schedule')
    return {'status': proposals['status'], 'proposals': proposals['frames'].get(str(frame_index), [])}


@app.get('/api/{match_id}/players/{rally_id}')
def player_draft(match_id: str, rally_id: str, side: Literal['near', 'far'] = 'near'):
    directory, source, draft, boundary, stale = load_player_draft(match_id, rally_id)
    selection = json.loads((directory / 'pilot/selection.json').read_text(encoding='utf-8'))
    if side == 'far' and draft.get('annotation_mode') != 'independent_manual_no_detector_proposals':
        raise HTTPException(422, 'Far-side review requires a source-only schedule')
    saved = annotation_path(directory, rally_id, side)
    annotations = json.loads(saved.read_text(encoding='utf-8')) if saved.exists() else {'frames': {}}
    review = player_review_attestation(directory, rally_id, side, saved, annotations) if saved.exists() else None
    return {'source': source, 'draft': draft, 'boundary': boundary, 'stale': stale,
            'annotated_side': side,
            'assisted_proposals_available': assisted_proposals(directory, rally_id, source, selection) is not None,
            'dense_review_window': selection.get('dense_review_window'),
            'review_attestation': review, 'saved': annotations}


def regenerate_proposals(directory, rally_id, draft, boundary):
    if draft.get('annotation_mode') == 'independent_manual_no_detector_proposals':
        source = json.loads((directory / 'source_record.json').read_text(encoding='utf-8'))
        start, end = boundary['start_frame'], boundary['end_frame_exclusive']
        fps = source['camera']['fps']
        refreshed = dict(draft)
        refreshed.update(start_frame=start, end_frame_exclusive=end,
                         boundary_status=boundary.get('boundary_status', 'visual_bracket_unverified'),
                         frames=[{'frame_index': frame, 'time_s': round(frame / fps, 6), 'proposals': []}
                                 for frame in range(start, end)])
        path = directory / 'pilot/player_drafts' / f'{rally_id}.json'
        history = path.parent / 'history'
        history.mkdir(exist_ok=True)
        (history / f'{rally_id}_{uuid.uuid4().hex}.json').write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(refreshed, indent=2) + '\n', encoding='utf-8')
        temporary.replace(path)
        return
    from scripts.prepare_player_drafts import prepare
    prepare(directory, rally_id, refresh=True)


@app.post('/api/{match_id}/players/{rally_id}/refresh')
def refresh_proposals(match_id: str, rally_id: str, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin writes are not allowed')
    directory, source, draft, boundary, stale = load_player_draft(match_id, rally_id)
    if honours_sample_id(rally_id):
        raise HTTPException(422, 'Regenerate the frozen sample review queue with scripts/prepare_honours_sample_review.py')
    if boundary.get('usable') is False:
        raise HTTPException(409, 'This rally has been excluded')
    with SAVE_LOCK:
        for side in ('near', 'far'):
            saved = annotation_path(directory, rally_id, side)
            if saved.exists() and json.loads(saved.read_text(encoding='utf-8')).get('frames'):
                raise HTTPException(409, 'Saved player labels must be reconciled before regenerating proposals')
        regenerate_proposals(directory, rally_id, draft, boundary)
    return player_draft(match_id, rally_id)


def player_review_attestation(directory, rally_id, side, annotation_file, saved):
    """Return a review only while it covers these exact saved annotation bytes."""
    folder = ROOT / HONOURS_WORKSPACE / 'player_annotations' if honours_sample_id(rally_id) else directory / 'pilot/player_annotations'
    path = folder / 'reviews' / f'{rally_id}_{side}.json'
    if not path.is_file():
        return None
    try:
        review = json.loads(path.read_text(encoding='utf-8'))
        digest = hashlib.sha256(annotation_file.read_bytes()).hexdigest()
        frames = sorted(map(int, saved['frames']))
        if (review.get('annotation_sha256') != digest or
                review.get('status') != 'reviewed' or
                review.get('side') != side or
                not review.get('reviewer_id') or
                frames != list(range(review['first_frame'], review['last_frame'] + 1))):
            return None
        return review
    except (ValueError, KeyError, TypeError, OSError):
        return None


def player_csv(match_id, rally_id, source, saved, review=None):
    columns = 'match_id,rally_id,frame_index,time_s,object_type,id_type,id,x1,y1,x2,y2,confidence,occlusion,team_id,foot_x_px,foot_y_px,position_status,annotation_source,annotator_id,review_status,reviewer_id,notes,court_side'.split(',')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for frame_index, frame in sorted(saved['frames'].items(), key=lambda pair: int(pair[0])):
        for player in frame['players']:
            box = player['bbox'] or ['', '', '', '']
            foot = player['footpoint'] or ['', '']
            row = dict(zip(columns, [''] * len(columns)))
            row.update(match_id=match_id, rally_id=rally_id, frame_index=int(frame_index),
                       time_s=int(frame_index) / source['camera']['fps'], object_type='player',
                       id_type='player_id', id=player['player_id'], x1=box[0], y1=box[1], x2=box[2], y2=box[3],
                       occlusion=player['occlusion'], team_id=player['team_id'], foot_x_px=foot[0], foot_y_px=foot[1],
                       position_status=player['position_status'], annotation_source='assisted' if frame.get('proposal_displayed') or player['origin_proposal_id'] else 'manual',
                       annotator_id=frame['annotator_id'],
                       review_status='reviewed' if review else 'unreviewed',
                       reviewer_id=review['reviewer_id'] if review else '',
                       notes=player['notes'], court_side=saved.get('annotated_side', 'near'))
            writer.writerow(row)
    return stream.getvalue()


@app.put('/api/{match_id}/players/{rally_id}/frames/{frame_index}')
def save_player_frame(match_id: str, rally_id: str, frame_index: int, payload: PlayerFrame,
                      request: Request, side: Literal['near', 'far'] = 'near'):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Cross-origin writes are not allowed')
    directory, source, draft, boundary, stale = load_player_draft(match_id, rally_id)
    if side == 'far' and draft.get('annotation_mode') != 'independent_manual_no_detector_proposals':
        raise HTTPException(422, 'Far-side review requires a source-only schedule')
    if stale:
        raise HTTPException(409, 'Rally boundaries changed or rally excluded; regenerate the frame schedule before editing')
    frame_draft = next((f for f in draft['frames'] if f['frame_index'] == frame_index), None)
    if frame_draft is None:
        raise HTTPException(422, 'Frame is not in the prepared sparse schedule')
    if not payload.annotator_id.strip():
        raise HTTPException(422, 'Enter your annotator code')
    if payload.all_players_accounted_for and not payload.players and not payload.notes.strip():
        raise HTTPException(422, 'Explain a fully accounted-for frame with no labelled players')
    if (draft.get('annotation_mode') in ('independent_manual_no_detector_proposals',
                                       'honours_sample_unverified_detector_suggestions')
            and payload.all_players_accounted_for and len(payload.players) != 6):
        raise HTTPException(422, 'Account for all six target players before marking this frame complete')
    width, height = source['camera']['width'], source['camera']['height']
    identities = set()
    proposals = {p['proposal_id'] for p in frame_draft['proposals']}
    selection = json.loads((directory / 'pilot/selection.json').read_text(encoding='utf-8'))
    assisted = assisted_proposals(directory, rally_id, source, selection)
    if assisted is not None:
        proposals.update(p['proposal_id'] for p in assisted['frames'].get(str(frame_index), []))
    for player in payload.players:
        if player.player_id in identities:
            raise HTTPException(422, 'Duplicate player ID in this frame')
        identities.add(player.player_id)
        if player.origin_proposal_id and player.origin_proposal_id not in proposals:
            raise HTTPException(422, 'Unknown source proposal for this frame')
        if player.position_status == 'out_of_frame':
            if player.bbox is not None or player.footpoint is not None or player.occlusion != 'none':
                raise HTTPException(422, 'Out-of-frame players have no box, footpoint, or occlusion')
        elif player.occlusion == 'full':
            if player.bbox is not None or player.position_status == 'visible':
                raise HTTPException(422, 'Fully occluded players must not have an inferred box or visible floor position')
        else:
            if player.bbox is None:
                if not (player.occlusion == 'partial' and player.position_status == 'occluded'):
                    raise HTTPException(422, 'Draw a visible-body box, or mark full/partial occlusion with no usable box')
            else:
                x1, y1, x2, y2 = player.bbox
                if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                    raise HTTPException(422, 'Box outside the source frame or unordered')
        if player.position_status == 'visible':
            if player.footpoint is None:
                raise HTTPException(422, 'Mark the visible floor-contact point')
            x, y = player.footpoint
            if not (0 <= x < width and 0 <= y < height):
                raise HTTPException(422, 'Footpoint outside the source frame')
        elif player.footpoint is not None:
            raise HTTPException(422, 'Leave unobservable floor positions empty')
    record = payload.model_dump()
    record['proposal_displayed'] = payload.proposal_displayed or any(p.origin_proposal_id for p in payload.players)
    record.update(annotator_id=payload.annotator_id.strip(), saved_at=datetime.now(timezone.utc).isoformat(),
                  review_status='unreviewed', independent_review_status='pending')
    folder = ROOT / HONOURS_WORKSPACE / 'player_annotations' if honours_sample_id(rally_id) else directory / 'pilot/player_annotations'
    folder.mkdir(exist_ok=True)
    output = annotation_path(directory, rally_id, side)
    with SAVE_LOCK:
        saved = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {
            'match_id': match_id, 'rally_id': rally_id, 'start_frame': draft['start_frame'],
            'end_frame_exclusive': draft['end_frame_exclusive'], 'annotated_side': side, 'frames': {}}
        if saved.get('annotated_side', 'near') != side:
            raise HTTPException(409, 'Saved labels belong to a different court side')
        if any(saved[k] != draft[k] for k in ('start_frame', 'end_frame_exclusive')):
            raise HTTPException(409, 'Saved labels refer to different boundaries; reconcile the existing work first')
        history = folder / 'history'
        history.mkdir(exist_ok=True)
        event = dict(rally_id=rally_id, side=side, frame_index=frame_index,
                     previous=saved['frames'].get(str(frame_index)), current=record)
        (history / f'{uuid.uuid4().hex}.json').write_text(json.dumps(event, indent=2) + '\n', encoding='utf-8')
        saved['frames'][str(frame_index)] = record
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
        temporary.replace(output)
    return record


@app.get('/api/{match_id}/players/{rally_id}/export.csv')
def export_players(match_id: str, rally_id: str, side: Literal['near', 'far'] = 'near'):
    directory, source, draft, boundary, stale = load_player_draft(match_id, rally_id)
    if stale:
        raise HTTPException(409, 'Boundary changes must be reconciled before export')
    path = annotation_path(directory, rally_id, side)
    if not path.exists():
        raise HTTPException(404, 'Save player annotations first')
    saved = json.loads(path.read_text(encoding='utf-8'))
    if any(saved[k] != draft[k] for k in ('start_frame', 'end_frame_exclusive')):
        raise HTTPException(409, 'Saved labels refer to different boundaries')
    if saved.get('annotated_side', 'near') != side:
        raise HTTPException(409, 'Saved labels belong to a different court side')
    review = player_review_attestation(directory, rally_id, side, path, saved)
    status = 'reviewed' if review else 'unreviewed'
    return Response(player_csv(match_id, rally_id, source, saved, review), media_type='text/csv',
                    headers={'Content-Disposition': f'attachment; filename="{match_id}_{rally_id}_{side}_{status}.csv"'})
