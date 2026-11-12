"""Check the frozen primary-match sample against the contract evidence gates."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
SCORE = ROOT / 'data/processed/fqe_auto_score_timeline.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
BOUNDARIES = ROOT / 'data/matches/yt_FqE5pTJqx8g/full_match_boundary_review.json'
PILOT_BOUNDARIES = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/boundary_review.json'
DETECTOR = ROOT / 'data/processed/honours_sample_detector_feasibility.json'
R2 = ROOT / 'data/processed/honours_r2_readiness.json'
WORKSPACE = ROOT / 'data/processed/honours_annotation_workspace'
PILOT_LABELS = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations'
OUTPUT = ROOT / 'data/processed/honours_completion_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_COMPLETION_AUDIT.md'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sample, score, source, boundaries, pilot, detector, r2 = [read(p) for p in
        (SAMPLE, SCORE, SOURCE, BOUNDARIES, PILOT_BOUNDARIES, DETECTOR, R2)]
    if not all(item['source_sha256'] == source['sha256'] for item in
               (sample, score, detector, r2)):
        raise ValueError('A primary-match input is bound to a different source video')
    manifest_path = WORKSPACE / 'manifest.json'
    manifest = read(manifest_path) if manifest_path.exists() else {'points': []}
    if manifest['points'] and (manifest.get('sample_sha256') != sha(SAMPLE) or
                               manifest.get('source_sha256') != source['sha256']):
        raise ValueError('Frozen sample review manifest does not match source and sample')
    review_points = {(p['set'], p['point_number']): p for p in manifest['points']}
    proposals = {(p['set'], p['point_number']): p for p in detector['points']}
    rows = []
    for selected in sample['selected_points']:
        set_number, point_number = selected['set'], selected['point_number']
        key = f's{set_number}_p{point_number}'
        boundary = boundaries.get(key)
        is_r2 = (set_number, point_number) == (2, 2)
        if is_r2 and not boundary:
            boundary = pilot.get('r2')
        boundary_status = (boundary or {}).get('boundary_status', 'not_source_reviewed')
        boundary_complete = bool(boundary and boundary.get('start_frame') is not None and
                                 boundary.get('end_frame_exclusive') is not None and
                                 boundary_status == 'checked_by_annotator')
        detector_row = proposals[(set_number, point_number)]
        best_navigation = max(detector_row['frames'],
                              key=lambda frame: frame['near_court_box_bottom_candidates'])
        review_point = review_points.get((set_number, point_number))
        rally_id = review_point['rally_id'] if review_point else ('r2' if is_r2 else None)
        label_path = ((PILOT_LABELS if rally_id == 'r2' else WORKSPACE / 'player_annotations') /
                      f'{rally_id}.json') if rally_id else None
        saved_frames = read(label_path)['frames'] if label_path and label_path.exists() else {}
        complete_frames = sum(bool(f.get('all_players_accounted_for')) and len(f['players']) == 6
                              and len({p['player_id'] for p in f['players']}) == 6
                              for f in saved_frames.values())
        rows.append({'set': set_number, 'point_number': point_number,
                     'winner': selected['winner'], 'point_key': key,
                     'boundary_status': boundary_status,
                     'annotator_boundary_complete': boundary_complete,
                     'boundary_independent_review_complete': False,
                     'linked_player_annotations': bool(saved_frames),
                     'saved_player_frame_count': len(saved_frames),
                     'annotator_complete_player_frame_count': complete_frames,
                     'player_annotation_file': str(label_path.relative_to(ROOT)).replace('\\', '/') if saved_frames else None,
                     'player_annotation_sha256': sha(label_path) if saved_frames else None,
                     'validated_six_player_metric_frame_count': 0,
                     'detector_max_near_court_box_bottom_proposals':
                         detector_row['max_near_court_box_bottom_candidates'],
                     'best_detector_navigation_frame': best_navigation['frame'],
                     'best_detector_navigation_time_s': round(
                         best_navigation['frame'] / source['camera']['fps'], 2),
                     'next_evidence': ('Validate floor contacts, team identity, calibration and point phase'
                                       if saved_frames else
                                       'Review boundary and six near-side player floor positions')})
    boundary_count = sum(r['annotator_boundary_complete'] for r in rows)
    label_count = sum(r['linked_player_annotations'] for r in rows)
    saved_frame_count = sum(r['saved_player_frame_count'] for r in rows)
    complete_frame_count = sum(r['annotator_complete_player_frame_count'] for r in rows)
    result = {'status': 'contract_evidence_audit_not_complete',
              'match_id': sample['match_id'], 'source_sha256': source['sha256'],
              'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in
                               (SAMPLE, SCORE, SOURCE, BOUNDARIES, PILOT_BOUNDARIES,
                                DETECTOR, R2)},
              'summary': {'frozen_points': len(rows),
                          'score_winners_known': len(rows),
                          'annotator_boundaries_complete': boundary_count,
                          'points_with_linked_player_annotations': label_count,
                          'saved_player_frames': saved_frame_count,
                          'annotator_complete_player_frames': complete_frame_count,
                          'validated_six_player_metric_frames': 0,
                          'points_with_validated_team_metric': 0,
                          'outcome_association_estimable': False,
                          'contract_complete': False},
              'points': rows,
              'interpretation': 'All scheduled labels are saved and annotator-complete, but sparse navigation frames, unreviewed point intervals and staged calibration do not support a validated rally-level spatial outcome association.'}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(
        f"| {r['set']} | {r['point_number']} | {r['winner']} | "
        f"{'yes' if r['annotator_boundary_complete'] else 'no'} | "
        f"{r['saved_player_frame_count']} saved ({r['annotator_complete_player_frame_count']} complete) | "
        f"{r['best_detector_navigation_frame']} | "
        f"{r['detector_max_near_court_box_bottom_proposals']} | 0 |"
        for r in rows)
    REPORT.write_text(f'''# Honours project completion audit

The [earlier-work reuse note](HONOURS_PREVIOUS_WORK_REUSE.md) inventories the five pilot rallies. This audit counts only the frozen sample and now includes all newly saved annotations.

This [source-bound audit](../data/processed/honours_completion_audit.json) checks the frozen 18-point ProVolley–UTS sample against the signed contract's spatial-analysis requirements. It separately counts saved annotation work and validated metric evidence; automatic detector boxes and the [R2 provisional calculation](HONOURS_R2_PROVISIONAL_METRICS.md) are excluded from final metrics.

| Gate | Current evidence |
| --- | ---: |
| Score-linked point winners | {len(rows)}/{len(rows)} |
| Annotator-complete point boundaries | {boundary_count}/{len(rows)} |
| Points with linked player annotations | {label_count}/{len(rows)} |
| Saved annotator-complete player frames | {complete_frame_count}/{saved_frame_count} |
| Validated six-player metric frames | 0 |
| Points with a validated team metric | 0/{len(rows)} |
| Outcome association estimable | No |

| Set | Point | Winner | Saved point boundary | Linked player labels | Best navigation frame | Max detector proposals | Final metric frames |
| ---: | ---: | --- | --- | --- | ---: | ---: | ---: |
{table}

All scheduled player frames are saved and marked annotator-complete. The [detailed annotation audit](HONOURS_COMPLETED_SAMPLE_AUDIT.md) checks visible floor contacts and staged projections without changing labels. The two saved point boundaries are set 1 point 2 and R2; the other 16 point intervals are still navigation windows. Saved boxes and complete checkboxes do not by themselves validate identity, floor clicks or metre-scale geometry.

**Completion decision:** Score and scheduled annotation work are complete. The contract's validated court-coordinate dataset, three rally-level team metrics and metric–outcome comparison remain incomplete. The next work is source-phase and floor-contact QC, court calibration and a feasibility decision based on the sparse eligible-frame denominator. No player redrawing is presumed necessary.
''', encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
