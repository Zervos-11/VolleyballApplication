"""Count saved six-player boxes as a separate image-position proxy screen."""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SCAN = ROOT / 'data/processed/honours_saved_game_state_scan.json'
OUT = ROOT / 'data/processed/honours_box_proxy_availability.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_BOX_PROXY_AVAILABILITY.md'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def usable_box(player):
    box = player.get('bbox')
    return (isinstance(box, list) and len(box) == 4 and
            all(isinstance(v, (int, float)) and math.isfinite(v) for v in box) and
            box[0] < box[2] and box[1] < box[3])


def main():
    audit, scan = read(AUDIT), read(SCAN)
    if audit['source_sha256'] != scan['source_sha256'] or scan['completed_audit_sha256'] != sha(AUDIT):
        raise ValueError('Source or audit changed since the game-state scan')
    scan_rows = {(r['set'], r['point_number'], r['frame']): r for r in scan['rows']}
    rows = []
    for point in audit['points']:
        label_path = ROOT / point['label_file']
        if sha(label_path) != point['label_sha256']:
            raise ValueError(f'Labels changed since the completed-sample audit: {label_path}')
        labels = read(label_path)
        for number, frame in labels['frames'].items():
            key = point['set'], point['point_number'], int(number)
            phase = scan_rows[key]
            players = frame['players']
            six = (len(players) == 6 and len({p['player_id'] for p in players}) == 6 and
                   all(usable_box(p) for p in players))
            rows.append({'set': key[0], 'point_number': key[1], 'winner': point['winner'],
                         'frame': key[2], 'usable_player_boxes': sum(usable_box(p) for p in players),
                         'six_usable_boxes': six,
                         'source_review_phase': phase['source_review_phase'],
                         'navigation_play': phase['navigation_play'],
                         'navigation_basis': phase['navigation_basis']})
    if len(rows) != audit['summary']['saved_frames']:
        raise ValueError('Saved-frame count changed')
    by_group = []
    for set_number in (1, 2, 3):
        for winner in ('ProVolley', 'UTS'):
            group = [r for r in rows if r['set'] == set_number and r['winner'] == winner]
            six = [r for r in group if r['six_usable_boxes']]
            navigation = [r for r in six if r['navigation_play']]
            confirmed = [r for r in six if r['source_review_phase'] == 'live_play']
            by_group.append({'set': set_number, 'winner': winner, 'saved_frames': len(group),
                             'six_box_frames': len(six), 'navigation_six_box_frames': len(navigation),
                             'source_confirmed_live_six_box_frames': len(confirmed),
                             'navigation_points': sorted({r['point_number'] for r in navigation})})
    result = {'status': 'box_proxy_availability_screen_not_metric_validation',
              'source_sha256': audit['source_sha256'], 'completed_audit_sha256': sha(AUDIT),
              'game_state_scan_sha256': sha(SCAN), 'saved_frames': len(rows),
              'six_box_frames': sum(r['six_usable_boxes'] for r in rows),
              'six_box_navigation_frames': sum(bool(r['six_usable_boxes'] and r['navigation_play']) for r in rows),
              'six_box_source_confirmed_live_frames': sum(bool(r['six_usable_boxes'] and r['source_review_phase'] == 'live_play') for r in rows),
              'by_set_winner': by_group, 'rows': rows,
              'limitations': ['A box centre is an image coordinate, not a court-floor position.',
                              'Box bottom centre is a possible ground anchor, but posture, clipping and jumping can shift it.',
                              'Model navigation proposals are not source-confirmed live play.',
                              'The six box identities and near-side membership are not independently verified.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(f"| {g['set']} | {g['winner']} | {g['six_box_frames']} | "
                      f"{g['navigation_six_box_frames']} | {g['source_confirmed_live_six_box_frames']} |"
                      for g in by_group)
    REPORT.write_text(f'''# Six-player box proxy availability

The user's proposed body/box movement proxy does not require a separately clicked shoe contact on every frame. This [source-bound screen](../data/processed/honours_box_proxy_availability.json) counts the saved boxes against the existing [phase navigation scan](HONOURS_SAVED_GAME_STATE_SCAN.md). It does not change the source labels or the strict floor-coordinate metric gate.

Of {len(rows)} saved positions, **{result['six_box_frames']}** have six usable boxes, versus {audit['summary']['six_visible_contact_frames']} with six marked visible contacts. **{result['six_box_navigation_frames']}** of the six-box frames are source-confirmed live or model-proposed play; only **{result['six_box_source_confirmed_live_frames']}** are source-confirmed live.

| Set | Winner | Six-box frames | Six-box navigation frames | Source-confirmed live six-box frames |
| ---: | --- | ---: | ---: | ---: |
{table}

This relaxes the need for individual shoe clicks for an **image-plane movement proxy**. A box centre can describe apparent movement on a fixed camera, with results in pixels or a clearly defined normalized image scale. It is elevated above the floor and cannot be sent directly through the court homography to claim metre-valued coverage or spacing. For court coordinates, the box bottom centre can be evaluated as a *ground-anchor estimate* when the player is grounded and fully visible; its error should be checked against a small set of manually reviewed floor contacts. Airborne, clipped and occluded cases remain unknown.

There are no six-box navigation frames for UTS-won points in sets two or three. Relaxing foot-click availability alone therefore does not create the missing outcome groups for the planned set-stratified comparison. More source-backed player positions or an explicitly narrower research question would still be needed.
''', encoding='utf-8')
    print(f"six boxes {result['six_box_frames']}/{len(rows)}; navigation {result['six_box_navigation_frames']}; source-confirmed live {result['six_box_source_confirmed_live_frames']}")


if __name__ == '__main__':
    main()
