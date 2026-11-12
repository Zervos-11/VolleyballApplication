"""Prepare editable, unverified detector suggestions for the frozen honours sample."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
SCREEN = ROOT / 'data/processed/honours_sample_detector_feasibility.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
BOUNDARIES = ROOT / 'data/matches/yt_FqE5pTJqx8g/full_match_boundary_review.json'
WORKSPACE = ROOT / 'data/processed/honours_annotation_workspace'


def prepare():
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    boundaries = json.loads(BOUNDARIES.read_text(encoding='utf-8')) if BOUNDARIES.exists() else {}
    if sample['source_sha256'] != source['sha256'] or screen['source_sha256'] != source['sha256']:
        raise ValueError('Frozen sample, detector screen, and source video do not match')
    detected = {(p['set'], p['point_number']): p for p in screen['points']}
    selected = {(p['set'], p['point_number']) for p in sample['selected_points']}
    if selected != set(detected):
        raise ValueError('Detector screen does not cover exactly the frozen sample')
    drafts = WORKSPACE / 'drafts'
    drafts.mkdir(parents=True, exist_ok=True)
    manifest = {'status': 'unverified_navigation_frame_review_queue',
                'match_id': sample['match_id'], 'source_sha256': source['sha256'],
                'sample_sha256': hashlib.sha256(SAMPLE.read_bytes()).hexdigest(),
                'detector_screen_sha256': hashlib.sha256(SCREEN.read_bytes()).hexdigest(),
                'points': []}
    for point in sample['selected_points']:
        key = (point['set'], point['point_number'])
        point_id = f"s{key[0]}_p{key[1]}"
        if point.get('pilot_rally_id'):
            manifest['points'].append({'set': key[0], 'point_number': key[1], 'winner': point['winner'],
                                       'rally_id': point['pilot_rally_id'], 'review_source': 'existing_pilot',
                                       'boundary_status': 'checked_by_annotator',
                                       'navigation_frames': [f['frame'] for f in detected[key]['frames']]})
            continue
        rally_id = f'hs_{point_id}'
        saved_boundary = boundaries.get(point_id)
        checked = (saved_boundary and saved_boundary.get('boundary_status') == 'checked_by_annotator'
                   and isinstance(saved_boundary.get('start_frame'), int)
                   and isinstance(saved_boundary.get('end_frame_exclusive'), int))
        start = saved_boundary['start_frame'] if checked else point['seek_from_frame']
        end = saved_boundary['end_frame_exclusive'] if checked else point['seek_to_frame_exclusive']
        frames = []
        for row in detected[key]['frames']:
            frame = row['frame']
            if not start <= frame < end:
                continue
            frames.append({'frame_index': frame, 'time_s': round(frame / source['camera']['fps'], 6),
                           'proposals': [
                               {'proposal_id': f'f{frame}_det{i:02d}', 'bbox': candidate['bbox_px'],
                                'confidence': candidate['confidence']}
                               for i, candidate in enumerate(row['candidates'], 1)]})
        if not frames:
            raise ValueError(f'No navigation frame inside review interval for {point_id}')
        draft = {'match_id': sample['match_id'], 'rally_id': rally_id, 'sample_point_id': point_id,
                 'start_frame': start, 'end_frame_exclusive': end,
                 'boundary_status': 'checked_by_annotator' if checked else 'navigation_window_not_reviewed',
                 'source_sha256': source['sha256'], 'model_sha256': screen['model_sha256'],
                 'detector_screen_sha256': manifest['detector_screen_sha256'],
                 'annotation_mode': 'honours_sample_unverified_detector_suggestions',
                 'frames': frames}
        path = drafts / f'{rally_id}.json'
        annotation = WORKSPACE / 'player_annotations' / f'{rally_id}.json'
        if annotation.exists():
            if not path.exists() or json.loads(path.read_text(encoding='utf-8')) != draft:
                raise ValueError(f'{rally_id} has saved labels; reconcile before changing its draft')
        else:
            path.write_text(json.dumps(draft, indent=2) + '\n', encoding='utf-8')
        manifest['points'].append({'set': key[0], 'point_number': key[1], 'winner': point['winner'],
                                   'rally_id': rally_id, 'boundary_status': draft['boundary_status'],
                                   'review_source': 'honours_workspace',
                                   'navigation_frames': [f['frame_index'] for f in frames],
                                   'saved_annotation_exists': annotation.exists()})
    (WORKSPACE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Prepared {len(manifest['points'])} frozen points; detector boxes remain unverified.")


if __name__ == '__main__':
    prepare()
