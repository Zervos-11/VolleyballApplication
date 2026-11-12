"""Record visual team membership for three high-resolution detector examples."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = SCREEN / 'zero_run_high_res_detection/index.json'
OUT = SCREEN / 'zero_run_high_res_source_qc.json'
SELECTED = {(1, 18): (5371, [1, 2, 3, 4, 5, 6]),
            (2, 14): (16032, [1, 2, 3, 4, 5, 6]),
            (3, 23): (32757, None)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    assert len(index['entries']) == len(SELECTED) == 3
    rows = []
    for entry in index['entries']:
        key = entry['set'], entry['point_number']
        frame, accepted = SELECTED[key]
        sheet = SCREEN / 'zero_run_high_res_detection' / entry['sheet']
        full = SCREEN / 'zero_run_high_res_detection' / f's{key[0]}_p{key[1]:02d}_f{frame}_full.jpg'
        assert sha(sheet) == entry['sheet_sha256']
        assert full.exists()
        proposal = next(row for row in entry['rows'] if row['source_frame'] == frame)
        if accepted is not None:
            assert max(accepted) < len(proposal['broad_person_proposals'])
        rows.append({'set': key[0], 'point_number': key[1], 'source_frame': frame,
                     'source_sheet': entry['sheet'], 'source_sheet_sha256': sha(sheet),
                     'full_resolution_overlay': full.name, 'full_resolution_overlay_sha256': sha(full),
                     'accepted_near_team_proposal_indices': accepted or [],
                     'local_six_box_status': ('six_correct_near_side_boxes_single_instant'
                                              if accepted is not None else 'not_recovered_overlap_duplicates'),
                     'ground_position_validation': 'pending',
                     'run_identity_validation': 'pending'})
    OUT.write_text(json.dumps({
        'status': 'single_reviewer_high_resolution_detector_recovery_not_trajectory_validation',
        'source_sha256': index['source_sha256'], 'detection_index_sha256': sha(INDEX),
        'summary': {'source_visible_detector_zero_wins': 3,
                    'recovered_local_six_box_instants': 2,
                    'remaining_without_correct_six_box_instant': 1,
                    'validated_grounded_trajectories': 0},
        'limitations': 'Two frames have visually distinct near-team boxes after excluding an official. The set-three point-23 overlay still duplicates the server and a front-row player while merging overlapping teammates. Each adjudication is one instant from a changed detector setting, not an independently validated track or floor position.',
        'rows': rows,
    }, indent=2) + '\n', encoding='utf-8')
    print('Recovered 2/3 single-frame six-box instants')


if __name__ == '__main__':
    main()
