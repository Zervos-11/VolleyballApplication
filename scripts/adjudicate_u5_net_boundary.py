"""Record single-reviewer near/far membership for the 28 flagged U5 boxes.

Labels were read from net_boundary_review/boundary_crops.jpg alongside the
four full-frame sheets. They cover only the saved coarse seconds.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'net_side_gate_screen.json'
SHEET = BASE / 'net_boundary_review/boundary_crops.jpg'
OUT = BASE / 'net_boundary_adjudication.json'

# One entry per red box, in the order shown in the crop sheet.
LABELS = {
    50: ['far', 'far'], 246: ['near', 'near'], 247: ['near'],
    353: ['far'], 354: ['far'], 359: ['near'], 364: ['far'],
    404: ['near'], 412: ['near'], 445: ['far', 'far', 'far'],
    446: ['far'], 447: ['far'], 451: ['near'], 739: ['far'],
    979: ['near'], 996: ['far'], 997: ['far'], 1000: ['far'],
    1135: ['far'], 1137: ['near'], 1192: ['far'], 1193: ['far'],
    1201: ['near'], 1204: ['far'],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    rows = [r for r in screen['rows'] if r['net_boundary_review_count']]
    if set(LABELS) != {r['source_second'] for r in rows}:
        raise ValueError('Labels do not cover exactly the screened boundary frames')
    decisions = []
    for row in rows:
        boxes = [p for p in row['proposals'] if p['net_side_status'] == 'net_boundary_review']
        labels = LABELS[row['source_second']]
        if len(boxes) != len(labels):
            raise ValueError(f"Label count differs at {row['source_second']} s")
        decisions.append({
            'set': row['set'], 'point_number': row['point_number'],
            'source_second': row['source_second'], 'source_frame': row['source_frame'],
            'boxes': [{'crop_box_number': i, 'bbox_px': box['bbox_px'],
                       'visual_team_side': label}
                      for i, (box, label) in enumerate(zip(boxes, labels), 1)]
        })
    near = sum(b['visual_team_side'] == 'near' for r in decisions for b in r['boxes'])
    far = sum(b['visual_team_side'] == 'far' for r in decisions for b in r['boxes'])
    near_by_second = {r['source_second']: sum(b['visual_team_side'] == 'near'
                                             for b in r['boxes']) for r in decisions}
    adjusted_six_seconds = sum(
        row['near_floor_side_candidate_count'] + near_by_second.get(row['source_second'], 0) >= 6
        for row in screen['rows'])
    output = {
        'status': 'single_reviewer_visual_side_adjudication_of_flagged_boxes_only',
        'net_side_screen_sha256': digest(SCREEN),
        'review_crop_sheet_sha256': digest(SHEET),
        'review_basis': '28 red numbered boxes on crop sheet, checked with four full-frame sheets; '
                        'near side blue in sets 1/3, white in set 2, with contrasting liberos',
        'summary': {'reviewed_boxes': near + far, 'visually_near_boxes': near,
                    'visually_far_boxes': far, 'reviewed_source_seconds': len(decisions),
                    'seconds_with_six_geometry_plus_review_candidates': adjusted_six_seconds,
                    'known_near_boundary_recovered_at_seconds': [404, 1137]},
        'decisions': decisions,
        'limitations': [
            'Single-reviewer labels are only for team side in these frames.',
            'Two boxes can show the same player; labels do not establish six distinct players.',
            'Ground contact, tracking identity and later/earlier frames are not adjudicated.',
            'A geometric candidate below the line is not automatically a near teammate.'
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
