"""Audit saved sample labels and calculate clearly provisional spatial summaries."""
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
WORKSPACE = ROOT / 'data/processed/honours_annotation_workspace'
PILOT = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot'
CALIBRATIONS = {1: PILOT / 'calibration/camera_r1.json',
                2: PILOT / 'calibration/camera_r2_r5.json',
                3: PILOT / 'calibration/camera_r2_r5.json'}
OUTPUT = ROOT / 'data/processed/honours_completed_sample_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_COMPLETED_SAMPLE_AUDIT.md'
METRIC_NAMES = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    sample = read(SAMPLE)
    manifest = read(WORKSPACE / 'manifest.json')
    if manifest['sample_sha256'] != sha(SAMPLE) or manifest['source_sha256'] != sample['source_sha256']:
        raise ValueError('Review manifest does not match the frozen sample')
    matrices = {}
    for set_number, path in CALIBRATIONS.items():
        c = read(path)
        matrices[set_number] = cv2.getPerspectiveTransform(
            np.asarray(c['points_px'], np.float32), np.asarray(c['points_court_m'], np.float32))
    manifest_points = {(p['set'], p['point_number']): p for p in manifest['points']}
    points = []
    for selected in sample['selected_points']:
        key = selected['set'], selected['point_number']
        item = manifest_points[key]
        label_path = (PILOT / 'player_annotations' / f"{item['rally_id']}.json"
                      if item['review_source'] == 'existing_pilot' else
                      WORKSPACE / 'player_annotations' / f"{item['rally_id']}.json")
        draft_path = (PILOT / 'player_drafts' / f"{item['rally_id']}.json"
                      if item['review_source'] == 'existing_pilot' else
                      WORKSPACE / 'drafts' / f"{item['rally_id']}.json")
        draft = read(draft_path)
        saved = read(label_path) if label_path.exists() else {'frames': {}}
        scheduled = {str(f['frame_index']) for f in draft['frames']}
        present = set(saved['frames'])
        if not present <= scheduled:
            raise ValueError(f'{item["rally_id"]} has annotations outside its draft')
        record = {'set': key[0], 'point_number': key[1], 'winner': selected['winner'],
                  'rally_id': item['rally_id'], 'label_file': str(label_path.relative_to(ROOT)).replace('\\', '/'),
                  'label_sha256': sha(label_path) if label_path.exists() else None,
                  'scheduled_frames': len(scheduled), 'saved_frames': len(present),
                  'annotator_complete_frames': 0, 'six_visible_contact_frames': 0,
                  'six_projected_in_court_frames': 0, 'team_id_warning_frames': 0,
                  'statuses': {}, 'team_ids': {},
                  'frame_rows': [], 'provisional_medians': {name: None for name in METRIC_NAMES}}
        statuses, teams = Counter(), Counter()
        eligible = []
        for frame_key, frame in sorted(saved['frames'].items(), key=lambda kv: int(kv[0])):
            players = frame['players']
            ids = [p['player_id'] for p in players]
            statuses.update(p['position_status'] for p in players)
            teams.update(p['team_id'] for p in players)
            complete = bool(frame.get('all_players_accounted_for')) and len(players) == 6 and len(set(ids)) == 6
            six_visible = complete and all(p['position_status'] == 'visible' and p['footpoint'] is not None for p in players)
            expected_team_id = 'away' if key[0] == 2 else 'home'
            team_ids_consistent = all(p['team_id'] == expected_team_id for p in players)
            row = {'frame': int(frame_key), 'annotator_complete': complete, 'six_visible_contacts': six_visible,
                   'team_ids_consistent_with_provisional_side_map': team_ids_consistent,
                   'projection_in_court': False, 'metric_candidate': None,
                   'review_status': frame.get('review_status', 'unknown')}
            record['annotator_complete_frames'] += int(complete)
            record['six_visible_contact_frames'] += int(six_visible)
            record['team_id_warning_frames'] += int(not team_ids_consistent)
            if six_visible:
                feet = np.asarray([[p['footpoint']] for p in players], np.float32)
                projected = cv2.perspectiveTransform(feet, matrices[key[0]])[:, 0, :]
                if np.isfinite(projected).all() and ((projected >= 0) & (projected <= 9)).all():
                    row['projection_in_court'] = True
                    row['metric_candidate'] = {k: round(v, 4) for k, v in metrics([tuple(map(float, xy)) for xy in projected]).items()}
                    record['six_projected_in_court_frames'] += 1
                    eligible.append(row['metric_candidate'])
            record['frame_rows'].append(row)
        record['statuses'] = dict(statuses)
        record['team_ids'] = dict(teams)
        if eligible:
            record['provisional_medians'] = {name: round(statistics.median(r[name] for r in eligible), 4)
                                             for name in METRIC_NAMES}
        points.append(record)
    summary = {'points': len(points), 'points_with_saved_frames': sum(p['saved_frames'] > 0 for p in points),
               'saved_frames': sum(p['saved_frames'] for p in points),
               'annotator_complete_frames': sum(p['annotator_complete_frames'] for p in points),
               'six_visible_contact_frames': sum(p['six_visible_contact_frames'] for p in points),
               'six_projected_in_court_frames': sum(p['six_projected_in_court_frames'] for p in points),
               'points_with_projected_metric_candidate': sum(p['six_projected_in_court_frames'] > 0 for p in points),
               'frames_with_team_id_warning': sum(p['team_id_warning_frames'] for p in points),
               'projected_frames_with_consistent_team_ids': sum(
                   r['projection_in_court'] and r['team_ids_consistent_with_provisional_side_map']
                   for p in points for r in p['frame_rows'])}
    by_set_winner = []
    for set_number in (1, 2, 3):
        for winner in ('ProVolley', 'UTS'):
            group = [p for p in points if p['set'] == set_number and p['winner'] == winner]
            by_set_winner.append({'set': set_number, 'winner': winner, 'sampled_points': len(group),
                                  'points_with_nominal_six_in_court': sum(p['six_projected_in_court_frames'] > 0 for p in group),
                                  'nominal_six_in_court_frames': sum(p['six_projected_in_court_frames'] for p in group),
                                  'team_field_consistent_nominal_frames': sum(
                                      r['projection_in_court'] and r['team_ids_consistent_with_provisional_side_map']
                                      for p in group for r in p['frame_rows'])})
    candidate_values = [r['metric_candidate'] for p in points for r in p['frame_rows']
                        if r['projection_in_court']]
    ranges = {name: [round(min(c[name] for c in candidate_values), 3),
                     round(max(c[name] for c in candidate_values), 3)]
              for name in METRIC_NAMES} if candidate_values else {}
    result = {'status': 'annotator_complete_sparse_frame_audit_provisional_geometry_not_final_metrics',
              'source_sha256': sample['source_sha256'], 'sample_sha256': sha(SAMPLE),
              'calibration_sha256': {str(k): sha(v) for k, v in CALIBRATIONS.items()},
              'limitations': ['Navigation frames are sparse and some fall outside live play.',
                              'Saved annotator-complete flags do not independently validate floor clicks.',
                              'Court transforms are staged, not validated for final metric use across all sets.',
                              'Near-side team mapping and team-id fields require source reconciliation.',
                              'No provisional median is a rally-level outcome observation.'],
              'summary': summary, 'provisional_frame_metric_ranges': ranges,
              'by_set_winner': by_set_winner, 'points': points}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    lines = '\n'.join(f"| {p['set']} | {p['point_number']} | {p['winner']} | {p['saved_frames']}/{p['scheduled_frames']} | "
                      f"{p['six_visible_contact_frames']} | {p['six_projected_in_court_frames']} |"
                      for p in points)
    group_lines = '\n'.join(f"| {g['set']} | {g['winner']} | {g['points_with_nominal_six_in_court']}/{g['sampled_points']} | "
                            f"{g['nominal_six_in_court_frames']} | {g['team_field_consistent_nominal_frames']} |"
                            for g in by_set_winner)
    player_rows = sum(len(read(ROOT / p['label_file'])['frames'][str(r['frame'])]['players'])
                      for p in points for r in p['frame_rows'])
    REPORT.write_text(f'''# Completed sample annotation audit

The [combined CSV export](../data/processed/honours_sample_annotations_provisional.csv) contains all {player_rows} saved player rows over {summary['saved_frames']} frames. Its [manifest](../data/processed/honours_sample_annotations_export.json) records input and output hashes. Court coordinates in that CSV are nominal projections through staged transforms, not validated physical measurements.

The [source-bound JSON](../data/processed/honours_completed_sample_audit.json) confirms that all **{summary['saved_frames']}** scheduled frames across the frozen 18-point sample are saved and marked annotator-complete. This includes the 12 existing R2 frames and 49 newly labelled navigation frames. The labels are preserved; this audit does not edit them.

Only **{summary['six_visible_contact_frames']}** frames have six marked visible contacts. Of those, **{summary['six_projected_in_court_frames']}** project all six points inside the nominal 9 m square under the staged calibration, across **{summary['points_with_projected_metric_candidate']}** points. The JSON gives formula outputs for these bounded candidates. They are provisional: source-floor click accuracy, set-wide calibration and near-side team identity are not independently validated, and the frames are too sparse to stand for whole rallies.

The saved home/away fields disagree with the provisional set-level near-side map or remain unknown on **{summary['frames_with_team_id_warning']}** frames. Only **{summary['projected_frames_with_consistent_team_ids']}** projected six-player candidates have all six team fields consistent with that provisional map. This is a data-quality flag, not proof that the other boxes are opponents; the map itself is unverified for final outcome assignment.

Across the 13 nominal projected frames, the provisional formula ranges are **{ranges['mean_pairwise_spacing_m'][0]:.3f}–{ranges['mean_pairwise_spacing_m'][1]:.3f} m** for mean pairwise spacing, **{ranges['convex_hull_area_m2'][0]:.3f}–{ranges['convex_hull_area_m2'][1]:.3f} m²** for formation hull area, and **{ranges['centroid_dispersion_m'][0]:.3f}–{ranges['centroid_dispersion_m'][1]:.3f} m** for centroid dispersion. These ranges describe where the formulas produced nominal values; they are not accuracy bounds or outcome effects.

| Set | Point | Winner | Saved/scheduled | Six visible contacts | Six nominal in-court projections |
| ---: | ---: | --- | ---: | ---: | ---: |
{lines}

| Set | Point winner | Points with a nominal six-player projection | Nominal frames | Frames with consistent team fields |
| ---: | --- | ---: | ---: | ---: |
{group_lines}

Set 3 has no nominal six-player projected frame for a UTS-won point. This outcome-dependent missingness alone blocks a balanced within-set spatial comparison, even before phase and calibration checks.

**Interpretation:** The user's annotation task is complete for this schedule. Further manual redrawing is not the next automatic requirement. The remaining work is evidence validation and a decision about whether sparse navigation frames support the planned rally-level comparison. Do not report these provisional medians as final outcome metrics.
''', encoding='utf-8')
    print(summary)
    return result


if __name__ == '__main__':
    audit()
