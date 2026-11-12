"""Record source-visible roster evidence for three detector-zero winning points."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = SCREEN / 'zero_run_source_review/index.json'
OUT = SCREEN / 'zero_run_source_qc.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    assert index['status'] == 'source_only_full_image_stills_no_detector_boxes'
    observations = {
        (1, 18): ('UCLA', 'five blue uniforms and white libero #28; the right-side blue player is close to the sideline',
                  'all_six_visible_but_not_all_grounded_court_positions_certified'),
        (2, 14): ('Concordia', 'five white uniforms and dark libero #7; three front-row players partially overlap',
                  'all_six_visible_but_server_airborne_in_early_stills'),
        (3, 23): ('UCLA', 'five blue uniforms and white libero #28; the back-left server is airborne early',
                  'all_six_visible_but_server_airborne_in_early_stills'),
    }
    rows = []
    for e in index['entries']:
        key = e['set'], e['point_number']
        assert key in observations
        sheet = SCREEN / 'zero_run_source_review' / e['sheet']
        assert sha(sheet) == e['sha256']
        team, evidence, limitation = observations[key]
        rows.append({**e, 'near_team': team,
                     'visual_team_membership': 'six_distinct_near_side_teammates_visible_in_source_stills',
                     'visual_evidence': evidence,
                     'ground_position_status': limitation,
                     'detector_six_id_run': False})
    assert len(rows) == 3
    OUT.write_text(json.dumps({
        'status': 'single_reviewer_source_visibility_not_ground_position_validation',
        'source_sha256': index['source_sha256'], 'review_index_sha256': sha(INDEX),
        'summary': {'winning_points_without_six_id_run': 3,
                    'source_stills_reviewed': sum(len(e['source_frames']) for e in rows),
                    'points_with_six_visible_teammates_in_source': 3,
                    'validated_grounded_trajectories': 0},
        'limitations': 'Source stills at approximately 5-frame spacing show team membership, not detector-box correctness, identity continuity, serve-contact timing, or shoe-floor coordinates. Overlap and airborne serving remain unresolved.',
        'rows': rows,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Adjudicated {len(rows)} detector-zero winning points')


if __name__ == '__main__':
    main()
