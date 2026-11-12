"""Record a single-reviewer source check of the 18 selected hard-cut pairs."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
REGISTER = BASE / 'rally_cut_clip_register.json'
SHEETS = BASE / 'rally_cut_boundary_review/index.json'
OUT = BASE / 'rally_cut_boundary_source_qc.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    register = json.loads(REGISTER.read_text(encoding='utf-8'))
    sheets = json.loads(SHEETS.read_text(encoding='utf-8'))
    if sheets['clip_register_sha256'] != digest(REGISTER):
        raise ValueError('Rendered cut sheets do not match clip register')
    if sheets['source_sha256'] != register['source_sha256']:
        raise ValueError('Different source video')
    for page in sheets['pages']:
        if digest(SHEETS.parent / page['path']) != page['sha256']:
            raise ValueError(f"Cut sheet hash mismatch: {page['path']}")
    keys = {(p['set'], p['point_number']) for page in sheets['pages'] for p in page['points']}
    selected = {(p['set'], p['point_number']) for p in register['selected_clips']}
    if len(keys) != 18 or keys != selected:
        raise ValueError('Cut sheets do not cover exactly the frozen selected clips')
    rows = [
        {'set': p['set'], 'point_number': p['point_number'],
         'clip_start_frame_inclusive': p['clip_start_frame_inclusive'],
         'clip_end_frame_exclusive': p['clip_end_frame_exclusive'],
         'source_review_status': 'hard_cut_visible_at_start_and_end',
         'review_note': 'Adjacent source frames show an abrupt change from the previous point aftermath to a new formation at the start, and from this point aftermath to the next formation/score at the end.'}
        for p in register['selected_clips']]
    result = {
        'status': 'single_reviewer_selected_edit_cut_source_check',
        'source_sha256': register['source_sha256'],
        'cut_register_sha256': digest(REGISTER),
        'cut_sheet_index_sha256': digest(SHEETS),
        'reviewer_count': 1,
        'summary': {'selected_clips': len(rows), 'visually_confirmed_edit_bounds': len(rows),
                    'exact_live_ball_boundaries_confirmed': 0},
        'rows': rows,
        'limitations': [
            'Edit cuts bracket the rally clip but include some preparation and/or post-point footage.',
            'A cut is not a serve-contact or dead-ball annotation.',
            'All selected cut pairs were reviewed by one analyst only.'
        ]
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
