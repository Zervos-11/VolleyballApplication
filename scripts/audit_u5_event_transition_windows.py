"""Bind conservative live interiors to the reviewed 5 Hz transition sheets.

These intervals are navigation evidence, not exact serve/dead-ball events and
cannot satisfy the strict metric calculator's boundary-review gate.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
BRACKETS = BASE / 'coarse_phase_brackets.json'
INDEX = BASE / 'event_transition_review/index.json'
OUTPUT = BASE / 'event_transition_source_qc.json'
# Single-reviewer visual observation of the rendered transition sheets. This
# identifies whether the server's action is in view, not an exact contact.
SERVER_ACTION_IN_VIEW = {
    (1, 6), (1, 34), (1, 37),
    (2, 14), (2, 26),
    (3, 13), (3, 23), (3, 27), (3, 34),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    brackets = json.loads(BRACKETS.read_text(encoding='utf-8'))
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    assert index['source_sha256'] == brackets['source_sha256']
    assert index['coarse_brackets_sha256'] == sha(BRACKETS)
    entries = {(r['set'], r['point_number'], r['event']): r for r in index['entries']}
    assert len(entries) == 36 and len(brackets['points']) == 18
    assert SERVER_ACTION_IN_VIEW <= {(p['set'], p['point_number']) for p in brackets['points']}
    points = []
    for p in brackets['points']:
        key = (p['set'], p['point_number'])
        related = [entries[key + (event,)] for event in ('serve', 'dead')]
        for entry in related:
            for page in entry['pages']:
                assert sha(INDEX.parent / page['path']) == page['sha256']
        first, last = p['first_obvious_active_frame'], p['last_obvious_active_frame']
        assert p['clip_start_frame_inclusive'] <= first <= last < p['clip_end_frame_exclusive']
        points.append({
            'set': key[0], 'point_number': key[1],
            'conservative_interior_start_frame_inclusive': first,
            'conservative_interior_end_frame_exclusive': last + 1,
            'interior_duration_s': round((last + 1 - first) / 30, 3),
            'serve_transition_sample_span': [min(related[0]['sampled_source_frames']),
                                             max(related[0]['sampled_source_frames'])],
            'dead_transition_sample_span': [min(related[1]['sampled_source_frames']),
                                            max(related[1]['sampled_source_frames'])],
            'serve_sheet_paths': [page['path'] for page in related[0]['pages']],
            'dead_sheet_paths': [page['path'] for page in related[1]['pages']],
            'server_action_visibility': ('server_action_in_view_contact_not_frame_certified'
                                         if key in SERVER_ACTION_IN_VIEW else
                                         'server_action_outside_view_or_not_confirmed'),
            'event_boundary_status': 'uncertain_not_exact',
            'metric_boundary_status': 'not_source_reviewed',
        })
    result = {
        'status': 'single_reviewer_five_hz_transition_navigation_not_final_boundary_review',
        'source_sha256': brackets['source_sha256'],
        'coarse_brackets_sha256': sha(BRACKETS),
        'event_transition_index_sha256': sha(INDEX),
        'summary': {'frozen_points': len(points), 'reviewed_transition_sheets': 36,
                    'points_with_conservative_live_interiors': len(points),
                    'points_with_server_action_in_view': len(SERVER_ACTION_IN_VIEW)},
        'interpretation': 'The interval runs from the first to the last clearly active navigation still. It excludes the ambiguous transition regions. Neither endpoint is claimed to be serve contact or dead ball. Serves can be offscreen; all intervals remain ineligible for final metrics until ground positions, roster continuity, and calibration are validated.',
        'points': points,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {OUTPUT}: {len(points)} conservative interiors; no exact event claims')


if __name__ == '__main__':
    main()
