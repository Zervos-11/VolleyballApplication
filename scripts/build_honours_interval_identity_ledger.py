"""Join existing evidence into a review ledger without certifying new labels."""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
QUEUE = ROOT / 'data/processed/fqe_rally_review_queue.json'
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
COMPLETION = ROOT / 'data/processed/honours_completion_audit.json'
PHASE = ROOT / 'data/processed/honours_candidate_phase_qc.json'
GAME = ROOT / 'data/processed/honours_saved_game_state_scan.json'
LABELS = ROOT / 'data/processed/honours_sample_annotations_provisional.csv'
OUT = ROOT / 'data/processed/honours_interval_identity_ledger.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_INTERVAL_IDENTITY_LEDGER.md'

# These frames were inspected in source-image reports, not certified trajectories.
SCREENED_IMAGE_SNAPSHOTS = {(3, 5): [155799], (3, 11): [162695],
                            (3, 37): [204263]}
KNOWN_REJECTED_NEAR_SIDE_SAVED_FRAMES = {(3, 27): [187701]}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sample, queue, audit, completion, phase, game = map(
        read, (SAMPLE, QUEUE, AUDIT, COMPLETION, PHASE, GAME))
    source_hash = sample['source_sha256']
    for record in (queue, audit, completion, phase, game):
        if record['source_sha256'] != source_hash:
            raise ValueError('Evidence sources refer to different videos')
    selected = sample['selected_points']
    if len(selected) != 18 or len({(r['set'], r['point_number']) for r in selected}) != 18:
        raise ValueError('Frozen sample does not contain 18 unique points')
    queue_by_key = {(r['set'], r['point_number']): r for r in queue['rows']}
    audit_by_key = {(r['set'], r['point_number']): r for r in audit['points']}
    completion_by_key = {(r['set'], r['point_number']): r for r in completion['points']}
    game_by_key = {(r['set'], r['point_number']): r for r in game['by_point']}
    phase_by_key = defaultdict(list)
    for row in phase['rows']:
        phase_by_key[(row['set'], row['point_number'])].append(row)
    label_by_key = defaultdict(lambda: defaultdict(list))
    with LABELS.open(newline='', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            label_by_key[(int(row['set']), int(row['point_number']))][int(row['frame_index'])].append(row)

    rows = []
    for chosen in selected:
        key = (chosen['set'], chosen['point_number'])
        q, a, c, g = (queue_by_key[key], audit_by_key[key],
                      completion_by_key[key], game_by_key[key])
        checked_path = ROOT / c['player_annotation_file']
        if digest(checked_path) != c['player_annotation_sha256']:
            raise ValueError(f'Completion audit label hash differs at {key}')
        checked_label = read(checked_path) if c['annotator_boundary_complete'] else None
        checked_start = checked_label['start_frame'] if checked_label else None
        checked_end = checked_label['end_frame_exclusive'] if checked_label else None
        if checked_label and (checked_start is None or checked_end is None or checked_start >= checked_end):
            raise ValueError(f'Invalid annotator-checked interval at {key}')
        frames = label_by_key[key]
        if len(frames) != a['saved_frames'] or any(len(v) != 6 for v in frames.values()):
            raise ValueError(f'Saved frame count/roster size differs at {key}')
        roster_sets = [set(p['player_id'] for p in players) for players in frames.values()]
        ids = sorted(set().union(*roster_sets))
        roster_change = any(s != roster_sets[0] for s in roster_sets[1:])
        phase_rows = phase_by_key[key]
        reviewed_live = sorted(r['frame'] for r in phase_rows if r['phase'] == 'live_play')
        reviewed_live_six = sorted(r['frame'] for r in phase_rows if r['phase'] == 'live_play'
                                   and r['frame'] in frames and
                                   any(f['frame'] == r['frame'] and f['projection_in_court']
                                       for f in a['frame_rows']))
        image_snapshots = SCREENED_IMAGE_SNAPSHOTS.get(key, [])
        rejected = KNOWN_REJECTED_NEAR_SIDE_SAVED_FRAMES.get(key, [])
        usable_reviewed_live_six = [f for f in reviewed_live_six if f not in rejected]
        if usable_reviewed_live_six:
            anchor, anchor_basis = usable_reviewed_live_six[0], 'source_phase_checked_saved_six_nominal_positions'
        elif image_snapshots:
            anchor, anchor_basis = image_snapshots[0], 'source_image_screened_six_box_proposal'
        elif any(f not in rejected for f in g['source_or_model_navigation_indices']):
            anchor = next(f for f in g['source_or_model_navigation_indices'] if f not in rejected)
            anchor_basis = 'game_state_navigation_proposal'
        else:
            anchor, anchor_basis = None, 'none'
        row = {
            'set': key[0], 'point_number': key[1], 'winner': chosen['winner'],
            'near_side_team_source_adjudication': 'UTS' if key[0] == 2 else 'ProVolley',
            'seek_from_frame': chosen['seek_from_frame'],
            'seek_to_frame_exclusive': chosen['seek_to_frame_exclusive'],
            'score_flip_frame': chosen['score_flip_frame'],
            'frozen_sample_boundary_status': chosen['boundary_status'],
            'annotator_checked_boundary_status': c['boundary_status'],
            'annotator_checked_serve_contact_frame': checked_start,
            'annotator_checked_end_frame_exclusive': checked_end,
            'boundary_independent_review_complete': c['boundary_independent_review_complete'],
            'heuristic_start_frame': q['estimated_start_frame'],
            'heuristic_end_frame_exclusive': q['estimated_end_frame_exclusive'],
            'source_review_end_range': [q['end_review_from_frame'], q['end_review_to_frame']],
            'saved_player_frames': sorted(frames),
            'six_visible_contact_frames': a['six_visible_contact_frames'],
            'six_nominal_in_court_frames': a['six_projected_in_court_frames'],
            'source_phase_checked_live_frames': reviewed_live,
            'source_phase_checked_live_six_nominal_frames': reviewed_live_six,
            'known_rejected_near_side_saved_frames': rejected,
            'source_image_screened_box_snapshots': image_snapshots,
            'model_play_navigation_frames': g['play_frame_indices'],
            'saved_player_ids_union': ids,
            'saved_player_ids_by_frame': {str(frame): sorted(p['player_id'] for p in players)
                                          for frame, players in sorted(frames.items())},
            'roster_changes_across_saved_frames': roster_change,
            'non_numeric_saved_player_ids': [player_id for player_id in ids if not player_id.isdigit()],
            'frames_with_unknown_or_opposite_team_field': a['team_id_warning_frames'],
            'first_review_anchor': anchor, 'first_review_anchor_basis': anchor_basis,
            'annotator_checked_interval_saved': checked_label is not None,
            'exact_interval_independently_verified': c['boundary_independent_review_complete'],
            'continuous_six_near_side_tracks_verified': False,
        }
        rows.append(row)
    result = {
        'status': 'source_bound_review_ledger_not_final_interval_or_identity_attestation',
        'source_sha256': source_hash,
        'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p)
                         for p in (SAMPLE, QUEUE, AUDIT, COMPLETION, PHASE, GAME, LABELS)},
        'near_side_mapping_basis': 'DELIVERABLES/HONOURS_NEAR_SIDE_SOURCE_ADJUDICATION.md',
        'screened_snapshot_basis': ['DELIVERABLES/HONOURS_SET3_IMAGE_PROXY_DEMO.md',
                                    'DELIVERABLES/HONOURS_MISSING_OUTCOME_VISUAL_SCREEN.md'],
        'summary': {
            'frozen_points': len(rows),
            'annotator_checked_intervals': sum(r['annotator_checked_interval_saved'] for r in rows),
            'independently_reviewed_intervals': sum(r['exact_interval_independently_verified'] for r in rows),
            'points_with_source_phase_checked_live_six_nominal_frame': sum(
                bool(r['source_phase_checked_live_six_nominal_frames']) for r in rows),
            'points_with_saved_roster_changes': sum(r['roster_changes_across_saved_frames'] for r in rows),
            'points_with_non_numeric_player_id': sum(bool(r['non_numeric_saved_player_ids']) for r in rows),
            'points_with_continuous_six_near_side_tracks_verified': 0,
        }, 'points': rows,
        'limits': ['Heuristic boundaries and model phase outputs are navigation only.',
                   'A changed saved ID set may reflect a substitution, relabel, or identity error; video is needed.',
                   'A consistent ID set does not validate each box or prove continuous identity.',
                   'Nominal six-in-court positions are not validated ground coordinates.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Frozen-sample interval and identity review ledger', '',
        'This [source-bound ledger](../data/processed/honours_interval_identity_ledger.json) joins existing score, boundary, saved-label, phase and detector-navigation evidence for all 18 frozen points. It does not change annotations or certify a new rally interval. The near-side team assignment follows the [source adjudication](HONOURS_NEAR_SIDE_SOURCE_ADJUDICATION.md): ProVolley in sets 1 and 3, UTS in set 2.', '',
        f"Annotator-checked intervals: **{result['summary']['annotator_checked_intervals']}/18**; independently reviewed intervals: **{result['summary']['independently_reviewed_intervals']}/18**. Points with at least one source-phase-checked live six-nominal-position saved frame: **{result['summary']['points_with_source_phase_checked_live_six_nominal_frame']}/18**. Points whose saved six-ID sets change between frames: **{result['summary']['points_with_saved_roster_changes']}/18**. Verified continuous six-player trajectories: **0/18**.", '',
        '| Set | Point | Winner | Near team | Saved interval | Live six-nominal frame(s) | Screened image box frame(s) | Saved ID change | First review anchor |',
        '| ---: | ---: | --- | --- | --- | --- | --- | --- | --- |'
    ]
    for r in rows:
        saved = (f"{r['annotator_checked_serve_contact_frame']}–{r['annotator_checked_end_frame_exclusive']}"
                 if r['annotator_checked_interval_saved'] else 'pending')
        fmt = lambda xs: ', '.join(map(str, xs)) or '—'
        lines.append(f"| {r['set']} | {r['point_number']} | {r['winner']} | "
                     f"{r['near_side_team_source_adjudication']} | {saved} | "
                     f"{fmt(r['source_phase_checked_live_six_nominal_frames'])} | "
                     f"{fmt(r['source_image_screened_box_snapshots'])} | "
                     f"{'check' if r['roster_changes_across_saved_frames'] else 'no saved change'} | "
                     f"{r['first_review_anchor'] or '—'} |")
    changes = []
    for r in rows:
        previous = None
        for frame_text, ids in r['saved_player_ids_by_frame'].items():
            current = set(ids)
            if previous is not None and current != previous:
                changes.append(f"S{r['set']} P{r['point_number']} f{frame_text} "
                               f"({', '.join(sorted(previous - current))} → "
                               f"{', '.join(sorted(current - previous))})")
            previous = current
    lines += ['', 'Saved-ID changes to inspect: ' + '; '.join(changes) + '. These are changes in annotation labels across sparse frames; they are not evidence of a real substitution without checking the video. The JSON records the full ID set at each saved frame.', '',
              '## Review order', '',
              '1. Start from the two saved annotator-checked intervals, which still lack independent source review. For the other points, the ledger provides only a heuristic start/end and score-flip search range; verify serve contact and point-ending action in the source video before using a window.',
              '2. At each first review anchor, verify **six distinct near-side players**, their player IDs and the action phase. The screened-image anchors are short source-image checks, not complete tracks. Set-three point 27 frame 187701 is explicitly rejected as a near-side six-player anchor because its saved box includes a far-side opponent. Preserve exclusions and the frozen selection.',
              '3. Resolve changed saved ID sets from the video before temporal matching. In particular, the non-numeric `Hair` identifier is not a jersey number. Unknown or opposite team fields need source reconciliation, but the completed player drawings should be reused.',
              '4. Track only within a verified live interval. Keep occluded/off-screen players missing; bridge a short gap only when the same identity is confirmed on both sides and mark the estimate. Validate grounded box-bottom against an independent floor reference before reporting metres.', '',
              'The [three existing navigation sheets](../data/processed/honours_sample_sheets/) show source stills for every frozen point. The [dense-window check](HONOURS_DENSE_PROXY_WINDOW_VISUAL_REVIEW.md) explains why six raw boxes are insufficient for a team trajectory.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
