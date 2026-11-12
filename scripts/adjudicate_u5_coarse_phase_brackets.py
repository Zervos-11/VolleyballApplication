"""Record conservative, source-visible phase navigation brackets for 18 clips.

Offsets refer to the 1 Hz source sheets. Offsets ending in .9 identify the
last frame of a clip when its rounded time label is the next whole second.
These are NOT exact serve/dead frames.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'frozen_clip_phase_review/index.json'
FOCUS = BASE / 'focus_phase_sequence/index.json'
OUT = BASE / 'coarse_phase_brackets.json'

# (set, point): (last visibly pre-play offset, first visibly active offset,
#                last visibly active offset, first visibly post-play offset).
# Seconds are relative to the edited clip's first source frame. A None means
# that one-second stills cannot support that phase decision.
DECISIONS = {
    (1, 5): (1, 3, 5, 7), (1, 6): (2, 3, 9, 11),
    (1, 18): (2, 3, 4, 5), (1, 27): (1, 3, 5, 7),
    (1, 34): (2, 3, 9, 11), (1, 37): (2, 3, 19, 21),
    (2, 2): (2, 3, 12, 14), (2, 6): (2, 3, 20, 22),
    (2, 14): (2, None, None, 6), (2, 26): (2, 3, 11, 13),
    (2, 28): (2, 3, 4, 5), (2, 37): (2, 3, 6, 8),
    (3, 11): (2, 3, 5, 8), (3, 13): (2, 3, 7, 9),
    (3, 23): (2, None, None, 5), (3, 27): (2, 3, 9, 10.9),
    (3, 33): (2, 3, 8, 9.9), (3, 34): (2, 3, 7, 9),
}

# The two short serves have finer 5 Hz source sheets. These identify a narrow
# active-looking interval, but still do not attest the exact contact/dead frame.
FINE_ACTIVE_MARKS = {(2, 14): (16032, 16056), (3, 23): (32742, 32760)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    focus = json.loads(FOCUS.read_text(encoding='utf-8'))
    keys = {(c['set'], c['point_number']) for c in index['clips']}
    if keys != set(DECISIONS) or len(keys) != 18:
        raise ValueError('Coarse decisions must cover the frozen 18 clips')
    if index['source_sha256'] != focus['source_sha256']:
        raise ValueError('Navigation and focus images use different source videos')
    rows = []
    for clip in index['clips']:
        key = clip['set'], clip['point_number']
        start, end = clip['clip_start_frame_inclusive'], clip['clip_end_frame_exclusive']
        offsets = DECISIONS[key]
        marked = [start + int(offset * 30) if offset is not None else None for offset in offsets]
        if key in FINE_ACTIVE_MARKS:
            marked[1:3] = FINE_ACTIVE_MARKS[key]
        if any(frame is not None and not start <= frame < end for frame in marked):
            raise ValueError(f'Mark outside clip: {key}')
        if any(marked[i] is not None and marked[i + 1] is not None and
               marked[i] >= marked[i + 1] for i in range(3)):
            raise ValueError(f'Phase marks out of order: {key}')
        pages = clip['pages']
        for page in pages:
            if digest(INDEX.parent / page['path']) != page['sha256']:
                raise ValueError(f"Source review image changed: {page['path']}")
        fine_sheets = [s for s in focus['sheets'] if (s['set'], s['point_number']) == key]
        if key in FINE_ACTIVE_MARKS and not fine_sheets:
            raise ValueError(f'Missing 5 Hz focus evidence: {key}')
        for sheet in fine_sheets:
            focus_path = BASE / 'focus_phase_sequence' / sheet['path']
            if digest(focus_path) != sheet['sha256']:
                raise ValueError(f"Focus review image changed: {sheet['path']}")
        rows.append({'set': key[0], 'point_number': key[1],
                     'clip_start_frame_inclusive': start, 'clip_end_frame_exclusive': end,
                     'last_obvious_pre_play_frame': marked[0],
                     'first_obvious_active_frame': marked[1],
                     'last_obvious_active_frame': marked[2],
                     'first_obvious_post_play_frame': marked[3],
                     'phase_status': ('five_hz_short_point_navigation_bracket' if key in FINE_ACTIVE_MARKS
                                      else 'one_hz_navigation_bracket_only'),
                     'evidence_sheet_paths': [p['path'] for p in pages],
                     'evidence_sheet_sha256': [p['sha256'] for p in pages],
                     'focus_sheet_paths': [s['path'] for s in fine_sheets],
                     'focus_sheet_sha256': [s['sha256'] for s in fine_sheets]})
    result = {
        'status': 'single_reviewer_coarse_source_navigation_not_exact_live_intervals',
        'source_sha256': index['source_sha256'],
        'review_index_sha256': digest(INDEX), 'focus_index_sha256': digest(FOCUS),
        'summary': {'frozen_clips': len(rows),
                    'clips_with_navigation_active_marks': sum(r['first_obvious_active_frame'] is not None for r in rows),
                    'short_clips_with_five_hz_marks': len(FINE_ACTIVE_MARKS),
                    'clips_without_active_marks': sum(r['first_obvious_active_frame'] is None for r in rows)},
        'interpretation': 'A mark identifies a source still that looks pre-play, active or post-play. The unobserved frames between marks are not adjudicated. No serve-contact or dead-ball frame is certified; do not use this register as a final metric gate.',
        'points': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(result['summary'])


if __name__ == '__main__':
    main()
