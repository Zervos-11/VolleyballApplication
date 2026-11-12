"""Apply a calibrated net-line screen to the U5 saved person proposals.

Boxes whose lower centre is beyond the near-court floor centreline are not
counted as unambiguous near-court proposals. They require source review because
jumps, occlusion and box extent can move a near player's box bottom across it.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
RAW = BASE / 'live_core_box_screen.json'
CALIBRATION = BASE / 'near_court_candidate.json'
QC = BASE / 'live_core_anchor_visual_qc.json'
OUT = BASE / 'net_side_gate_screen.json'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(proposal, net_floor_y_px):
    """Return only a geometry status; this does not identify team membership."""
    return ('near_floor_side_candidate' if proposal['bbox_px'][3] >= net_floor_y_px
            else 'net_boundary_review')


def main():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    net_y_values = [point[1] for point in calibration['points_px'][2:4]]
    if net_y_values[0] != net_y_values[1]:
        raise ValueError('This screen expects the horizontal staged floor centreline')
    net_y = net_y_values[0]
    reviewed = {row['accepted_second']: row for row in qc['rows']
                if row['accepted_second'] is not None}
    rows = []
    for row in raw['rows']:
        proposals = [{**p, 'net_side_status': classify(p, net_y)}
                     for p in row['proposals']]
        near_count = sum(p['net_side_status'] == 'near_floor_side_candidate'
                         for p in proposals)
        rows.append({'set': row['set'], 'point_number': row['point_number'],
                     'source_second': row['source_second'], 'source_frame': row['source_frame'],
                     'raw_proposal_count': len(proposals),
                     'near_floor_side_candidate_count': near_count,
                     'net_boundary_review_count': len(proposals) - near_count,
                     'proposals': proposals})
    audited = [row for row in rows if row['source_second'] in reviewed]
    by_second = {row['source_second']: row for row in rows}
    output = {
        'status': 'net_floor_side_screen_not_validated_team_membership',
        'video_id': raw['video_id'], 'source_sha256': raw['source_sha256'],
        'raw_screen_sha256': sha256(RAW), 'calibration_sha256': sha256(CALIBRATION),
        'visual_qc_sha256': sha256(QC),
        'net_floor_centreline_y_px': net_y,
        'rule': 'Keep only bbox bottom-centre at or below the image floor centreline '
                'as a near-floor-side candidate. Put boxes above it into net_boundary_review. '
                'Both classes still need team and floor-contact review.',
        'summary': {
            'sampled_seconds': len(rows),
            'seconds_with_six_raw_proposals': sum(r['raw_proposal_count'] >= 6 for r in rows),
            'seconds_with_six_near_floor_side_candidates': sum(
                r['near_floor_side_candidate_count'] >= 6 for r in rows),
            'boundary_boxes': sum(r['net_boundary_review_count'] for r in rows),
            'visually_accepted_six_snapshots': len(audited),
            'accepted_snapshots_with_six_after_geometric_screen': sum(
                r['near_floor_side_candidate_count'] >= 6 for r in audited),
            'accepted_snapshots_requiring_boundary_review': [
                r['source_second'] for r in audited
                if r['near_floor_side_candidate_count'] < 6],
            'known_false_six_1192_raw_count': by_second[1192]['raw_proposal_count'],
            'known_false_six_1192_after_screen': by_second[1192]['near_floor_side_candidate_count'],
        },
        'rows': rows,
        'limitations': [
            'The line is a staged calibration from one frame, not a player-side truth label.',
            'Airborne or occluded near-side players can cross the image line and need review.',
            'A far-side player can still pass the box-bottom screen during overlap.',
            'A six-candidate count does not validate six teammates, identities or floor positions.'
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
