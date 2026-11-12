"""Find exact-ID six-candidate runs containing source-reviewed live anchors.

This is an availability diagnostic. A raw ID does not establish a jersey identity,
and only the anchor instant has a local source-phase decision.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
SELECTED = BASE / 'phase_six_candidate_review/selected.json'
QC = BASE / 'selected_phase_source_qc.json'
OUT = BASE / 'anchor_live_window_availability.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    selected = json.loads(SELECTED.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    anchors = {(r['set'], r['point_number']): r for r in selected['selected']}
    phases = {(r['set'], r['point_number']): r['local_phase_status'] for r in qc['rows']}
    if set(anchors) != set(phases) or len(anchors) != 18:
        raise ValueError('Selection and phase register point keys differ')
    rows = []
    for point in tracks['points']:
        key = point['set'], point['point_number']
        anchor = anchors[key]
        ids = set(anchor['raw_track_ids'])
        if len(ids) != 6:
            raise ValueError(f'Anchor has other than six IDs: {key}')
        frames = point['rows']
        frame_to_index = {r['source_frame']: i for i, r in enumerate(frames)}
        if anchor['source_frame'] not in frame_to_index:
            raise ValueError(f'Anchor not sampled in dense tracks: {key}')
        def six_present(row):
            found = {p['raw_track_id'] for p in row['proposals']
                     if p['net_side_status'] == 'near_floor_side_candidate'}
            return ids <= found
        middle = frame_to_index[anchor['source_frame']]
        if not six_present(frames[middle]):
            raise ValueError(f'Anchor six IDs not all geometric candidates: {key}')
        first = last = middle
        step = point['frame_step']
        while first > 0 and frames[first]['source_frame'] - frames[first - 1]['source_frame'] == step and six_present(frames[first - 1]):
            first -= 1
        while last + 1 < len(frames) and frames[last + 1]['source_frame'] - frames[last]['source_frame'] == step and six_present(frames[last + 1]):
            last += 1
        span = frames[last]['source_frame'] - frames[first]['source_frame']
        rows.append({'set': key[0], 'point_number': key[1], 'anchor_frame': anchor['source_frame'],
                     'anchor_second': anchor['source_second'], 'anchor_phase': phases[key],
                     'first_sampled_frame': frames[first]['source_frame'],
                     'last_sampled_frame': frames[last]['source_frame'],
                     'sampled_frames_in_run': last - first + 1,
                     'observed_span_seconds': round(span / 30, 3),
                     'raw_track_ids': sorted(ids)})
    live = [r for r in rows if r['anchor_phase'] == 'visible_live_play']
    summary = {'points': len(rows), 'locally_live_anchors': len(live),
               'live_anchor_runs_at_least_five_frames': sum(r['sampled_frames_in_run'] >= 5 for r in live),
               'live_anchor_runs_one_frame_only': sum(r['sampled_frames_in_run'] == 1 for r in live),
               'total_sampled_frames_in_live_anchor_runs': sum(r['sampled_frames_in_run'] for r in live)}
    result = {'status': 'raw_id_availability_not_validated_six_player_live_trajectory',
              'source_sha256': tracks['source_sha256'],
              'dense_tracks_sha256': digest(TRACKS), 'selected_frame_sha256': digest(SELECTED),
              'source_phase_qc_sha256': digest(QC), 'sample_period_seconds': tracks['frame_step'] / 30,
              'summary': summary, 'rows': rows,
              'limitations': ['Only the anchor instant has a local source-phase review.',
                              'Raw tracker IDs are not source-verified jersey identities.',
                              'The observed span excludes the unknown duration before the first and after the last sampled frame.',
                              'Missing boxes are not filled with stationary assumptions.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(summary)
    for r in rows:
        print(f"S{r['set']} P{r['point_number']}: {r['sampled_frames_in_run']} frames, {r['anchor_phase']}")


if __name__ == '__main__':
    main()
