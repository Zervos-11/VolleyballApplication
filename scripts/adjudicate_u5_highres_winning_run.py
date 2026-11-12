"""Record source review of the newly found set-three winning six-ID run."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
RUNS = SCREEN / 'highres_winning_run_screen.json'
INDEX = SCREEN / 'highres_winning_run_review/index.json'
OUT = SCREEN / 'highres_winning_run_source_qc.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs = json.loads(RUNS.read_text(encoding='utf-8'))
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    assert index['run_audit_sha256'] == sha(RUNS)
    point = next(p for p in runs['points'] if (p['set'], p['point_number']) == (3, 13))
    frames = point['longest_exact_six_same_raw_id_run']
    assert len(frames) == 13
    shown = []
    for entry in index['entries']:
        sheet = SCREEN / 'highres_winning_run_review' / entry['sheet']
        assert sha(sheet) == entry['sha256']
        shown.extend(entry['source_frames'])
    assert shown == frames
    rows = {r['source_frame']: r for r in point['rows']}
    ids = {p['raw_track_id'] for p in rows[frames[0]]['near_floor_side_proposals']}
    assert ids == {2, 4, 6, 7, 10, 14}
    assert all({p['raw_track_id'] for p in rows[f]['near_floor_side_proposals']} == ids for f in frames)
    output = {
        'status': 'single_reviewer_short_winning_run_team_identity_not_ground_validation',
        'source_sha256': runs['source_sha256'], 'run_audit_sha256': sha(RUNS),
        'review_index_sha256': sha(INDEX),
        'set': 3, 'point_number': 13, 'near_team': 'UCLA', 'near_team_won': True,
        'source_frames': frames,
        'raw_id_to_jersey': {'2': 'UCLA_12', '4': 'UCLA_1', '6': 'UCLA_19',
                             '7': 'UCLA_libero_28', '10': 'UCLA_7', '14': 'UCLA_21'},
        'source_team_membership_status': 'six_correct_near_side_teammates_all_13_sampled_frames',
        'earliest_five_active_looking_frames': frames[:5],
        'active_looking_span_s': round((frames[4] - frames[0]) / 30, 3),
        'later_phase_status': 'uncertain_after_far_side_dive_point_end_not_exactly_frame_certified',
        'ground_position_validation': 'pending',
        'validated_metric_frames': 0,
        'limitations': 'The first five samples show active-looking far-side defense; this is not an exact serve-to-dead-ball interval. Later frames may include point-end/recovery movement. Jerseys and boxes were checked in the rendered source sheets by one reviewer. The six box bottoms remain unvalidated floor anchors, and unsampled source frames remain unobserved.',
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print('Source checked 13-frame winning run; first five active-looking, zero grounded metrics')


if __name__ == '__main__':
    main()
