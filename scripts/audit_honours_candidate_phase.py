"""Record visual source-phase QC for the 13 nominal metric candidate frames."""
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
CONTEXT = ROOT / 'data/processed/honours_annotation_workspace/qc_context/manifest.json'
OUT = ROOT / 'data/processed/honours_candidate_phase_qc.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_CANDIDATE_PHASE_QC.md'

# Visual judgments from exact source frames at -75, -25, 0, +25 and +75.
# "live_play" means the ball/action supports play at the candidate instant;
# it does not certify a floor click, team ID, court calibration or full rally.
JUDGMENTS = {
    8643: ('live_play', 'Ball travels above the court through adjacent frames.'),
    15252: ('pre_serve', 'Both sides remain in starting positions; near-right player prepares the serve.'),
    15505: ('live_play', 'Ball and near-side reception/return movement continue across adjacent frames.'),
    19345: ('live_play', 'Ball crosses near the net and the near side makes a defensive play.'),
    19854: ('uncertain_end_phase', 'Far-side player is already on the floor; adjacent frames do not establish whether the point ended before this instant.'),
    36366: ('live_play', 'Ball is in flight above the net with continuing play on both sides.'),
    65656: ('pre_serve', 'Near-side formation stays largely fixed while the far side prepares with the ball.'),
    78050: ('live_play', 'Ball and both teams move through a continuing exchange.'),
    78100: ('live_play', 'Ball is airborne over the court during continuing exchange.'),
    78400: ('live_play', 'Ball is airborne over the court during continuing exchange.'),
    90335: ('between_points', 'Earlier ball drops near the near-side baseline, then a player handles it and both teams disperse; no live exchange at this instant.'),
    102259: ('pre_serve', 'Receiving posture remains fixed; ball enters the court only in later context frames.'),
    187701: ('live_play', 'Net attack/block and subsequent ball trajectory show continuing play.'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    context = json.loads(CONTEXT.read_text(encoding='utf-8'))
    if context['audit_sha256'] != sha(AUDIT) or context['source_sha256'] != audit['source_sha256']:
        raise ValueError('Context sheets are not bound to the current audit/source')
    candidate = {(p['set'], p['point_number'], r['frame']): (p, r)
                 for p in audit['points'] for r in p['frame_rows'] if r['projection_in_court']}
    if {key[2] for key in candidate} != set(JUDGMENTS):
        raise ValueError('Every current candidate must have exactly one visual judgment')
    rows = []
    for item in context['rows']:
        key = item['set'], item['point_number'], item['candidate_frame']
        point, frame = candidate[key]
        status, evidence = JUDGMENTS[key[2]]
        sheet = ROOT / item['sheet']
        saved = json.loads((ROOT / point['label_file']).read_text(encoding='utf-8'))['frames'][str(key[2])]
        expected_field = 'away' if key[0] == 2 else 'home'
        unknown_ids = [p['player_id'] for p in saved['players'] if p['team_id'] == 'unknown']
        opposite_ids = [p['player_id'] for p in saved['players']
                        if p['team_id'] not in (expected_field, 'unknown')]
        rows.append({'set': key[0], 'point_number': key[1], 'winner': point['winner'],
                     'frame': key[2], 'phase': status, 'visual_evidence': evidence,
                     'context_frames': item['context_frames'], 'context_sheet': item['sheet'],
                     'context_sheet_sha256': sha(sheet),
                     'team_fields_consistent_with_provisional_side_map':
                         frame['team_ids_consistent_with_provisional_side_map'],
                     'saved_unknown_team_player_ids': unknown_ids,
                     'saved_opposite_team_player_ids': opposite_ids,
                     'nominal_metrics': frame['metric_candidate']})
    if len(rows) != len(candidate):
        raise ValueError('Context manifest does not cover all candidates')
    counts = Counter(r['phase'] for r in rows)
    live = [r for r in rows if r['phase'] == 'live_play']
    if any(r['saved_opposite_team_player_ids'] for r in rows):
        raise ValueError('Candidate contains an opposite-team field; inspect before reporting')
    by_set = []
    for set_number in (1, 2, 3):
        for winner in ('ProVolley', 'UTS'):
            group = [r for r in live if r['set'] == set_number and r['winner'] == winner]
            by_set.append({'set': set_number, 'winner': winner, 'live_candidate_frames': len(group),
                           'points': len({r['point_number'] for r in group})})
    result = {'status': 'visual_phase_qc_of_nominal_candidates_not_validated_metric_dataset',
              'source_sha256': audit['source_sha256'], 'completed_audit_sha256': sha(AUDIT),
              'context_manifest_sha256': sha(CONTEXT), 'review_method':
              'Visual inspection of five exact source frames per candidate, at offsets -75,-25,0,+25,+75 frames (50 fps).',
              'phase_counts': dict(counts), 'live_candidate_points': len({(r['set'], r['point_number']) for r in live}),
              'live_candidate_frames_with_consistent_team_fields': sum(
                  r['team_fields_consistent_with_provisional_side_map'] for r in live),
              'live_candidate_unknown_team_fields': sum(len(r['saved_unknown_team_player_ids']) for r in live),
              'by_set_winner': by_set, 'rows': rows,
              'limitations': ['Temporal stills show ball/action phase only; no exact serve or whistle time is certified.',
                              'Four live frames have an unknown team_id for one or two near-side players.',
                              'Foot clicks and set-wide 9 m calibration are not independently validated.',
                              'At most one sampled point survives in three of six set-by-winner cells; two cells have zero.',
                              'No winner association or final metre metric is supported by this audit.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(
        f"| {r['set']} | {r['point_number']} | {r['frame']} | {r['phase']} | "
        f"{'yes' if r['team_fields_consistent_with_provisional_side_map'] else 'unknown field(s)'} | "
        f"[{r['visual_evidence']}]({Path('../' + r['context_sheet']).as_posix()}) |"
        for r in rows)
    groups = '\n'.join(f"| {r['set']} | {r['winner']} | {r['points']}/3 | {r['live_candidate_frames']} |"
                       for r in by_set)
    REPORT.write_text(f'''# Candidate frame phase check

The [source-bound audit](../data/processed/honours_candidate_phase_qc.json) checks the 13 nominal six-player court candidates against five exact video frames around each candidate (up to 1.5 s either side at the recorded 50 fps). Linked sheets are visual evidence, and the original labels are untouched.

**Result:** {counts['live_play']} show live play, {counts['pre_serve']} are before the serve, {counts['between_points']} is between points, and {counts['uncertain_end_phase']} is uncertain at the end of play. The live snapshots cover {result['live_candidate_points']} of the 18 frozen sampled points. Only {result['live_candidate_frames_with_consistent_team_fields']} live snapshots have all six saved team fields consistent with the provisional side map. The other four live snapshots have {result['live_candidate_unknown_team_fields']} unknown fields between them, with no explicitly opposite-team fields. The source sheets show those boxes on the near side, but the provisional team-name mapping and player identity still need independent confirmation.

| Set | Point | Frame | Phase | Saved team fields | Source context and observation |
| ---: | ---: | ---: | --- | --- | --- |
{table}

| Set | Winner | Points with live candidate / 3 sampled | Live candidate frames |
| ---: | --- | ---: | ---: |
{groups}

These phase judgments remove pre-serve, between-point and uncertain-end frames from a rally-action analysis. The remaining nominal formula values are retained in the JSON solely for reproducibility. Camera calibration, exact floor contacts, team identity and comparable rally phases remain unvalidated. In sets 2 and 3 there are no UTS-won points with a live six-player candidate, so a set-stratified winner comparison cannot be estimated. Do not infer an outcome effect from the surviving snapshots or report their metre values as validated.
''', encoding='utf-8')
    print(dict(counts), 'live points', result['live_candidate_points'])


if __name__ == '__main__':
    main()
