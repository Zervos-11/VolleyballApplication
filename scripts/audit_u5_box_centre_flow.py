"""Join short optical-flow pilot with source endpoint review and missingness."""

import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PILOT = BASE / 'box_centre_flow_pilot.json'
QC = BASE / 'box_centre_flow_source_qc.json'
SNAPSHOT = BASE / 'image_plane_snapshot_screen.json'
OUT = BASE / 'box_centre_flow_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_BOX_CENTRE_FLOW_PILOT.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    pilot = json.loads(PILOT.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    snapshots = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    assert qc['pilot_sha256'] == sha(PILOT)
    assert pilot['source_sha256'] == qc['source_sha256'] == snapshots['source_sha256']
    assert pilot['input_sha256']['snapshot'] == sha(SNAPSHOT)
    reviewed = {(r['set'], r['point_number']): r for r in qc['rows']}
    assert len(reviewed) == len(pilot['rows']) == 17
    rows = []
    disagreements = []
    for row in pilot['rows']:
        key = row['set'], row['point_number']
        assert key in reviewed
        assert row['review_sheet_sha256'] == sha(BASE / 'box_centre_flow_pilot' / row['review_sheet'])
        assert row['all_six_tracked_at_all_five_samples']
        status = reviewed[key]['endpoint_status']
        assert status in ('no_obvious_wrong_person_transfer', 'uncertain_overlap')
        assert len(row['players']) == 6
        for player in row['players']:
            for frame in player['frames'].values():
                if 'same_raw_id_detector_disagreement_px' in frame:
                    disagreements.append(frame['same_raw_id_detector_disagreement_px'])
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': row['near_team_won'],
                     'phase_at_anchor': row['phase'],
                     'anchor_frame': row['anchor_frame'],
                     'detector_pass': row['detector_pass'],
                     'endpoint_visual_status': status,
                     'note': reviewed[key]['note'],
                     'all_six_flow_candidates_at_five_samples': True,
                     'review_sheet': row['review_sheet'],
                     'review_sheet_sha256': row['review_sheet_sha256']})
    assert len(disagreements) == pilot['summary']['same_raw_id_detector_comparisons'] == 334
    ordered = sorted(disagreements)
    open_clear = [r for r in rows if r['endpoint_visual_status'] == 'no_obvious_wrong_person_transfer'
                  and r['phase_at_anchor'] != 'serve_or_reset']
    groups = defaultdict(lambda: {'wins': [], 'losses': []})
    for row in open_clear:
        groups[(row['set'], row['phase_at_anchor'])]['wins' if row['near_team_won'] else 'losses'].append(row)
    matched = [r for r in open_clear if groups[(r['set'], r['phase_at_anchor'])]['wins']
               and groups[(r['set'], r['phase_at_anchor'])]['losses']]
    summary = {'frozen_points': 18,
               'reviewed_anchor_snapshots': 17,
               'six_algorithmic_flow_candidates_at_all_five_samples': 17,
               'no_obvious_wrong_person_transfer_at_displayed_endpoints': len(rows) -
               sum(r['endpoint_visual_status'] == 'uncertain_overlap' for r in rows),
               'uncertain_overlap_at_displayed_endpoints': sum(r['endpoint_visual_status'] == 'uncertain_overlap'
                                                               for r in rows),
               'visually_clear_open_play_anchor_windows': len(open_clear),
               'visually_clear_open_play_set_phase_matched_windows': len(matched),
               'same_raw_id_detector_comparisons': len(ordered),
               'median_same_raw_id_detector_disagreement_px': round(statistics.median(ordered), 2),
               'p95_same_raw_id_detector_disagreement_px': ordered[round(.95*(len(ordered)-1))],
               'maximum_same_raw_id_detector_disagreement_px': ordered[-1],
               'manually_validated_five_sample_player_identities': 0,
               'validated_court_trajectory_windows': 0}
    assert summary['no_obvious_wrong_person_transfer_at_displayed_endpoints'] == 13
    assert summary['visually_clear_open_play_anchor_windows'] == 11
    assert summary['visually_clear_open_play_set_phase_matched_windows'] == 8
    out = {'status': 'single_reviewer_short_flow_endpoint_audit_not_full_trajectory_validation',
           'source_sha256': pilot['source_sha256'],
           'input_sha256': {'pilot': sha(PILOT), 'source_qc': sha(QC), 'snapshot': sha(SNAPSHOT)},
           'summary': summary, 'rows': rows,
           'interpretation': ('The 17 algorithmically complete five-sample windows contain '
                              'four visually uncertain overlaps at the two displayed endpoints. '
                              'Intermediate samples, named player identities and all six floor '
                              'positions are not independently validated. Same-raw-ID detector '
                              'agreement is a correlated pipeline check, not ground truth.')}
    OUT.write_text(json.dumps(out, indent=2)+'\n', encoding='utf-8')
    lines = ['# Short box-centre optical-flow pilot', '',
             'The [source-bound pilot](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_pilot.json) '
             'starts from each of the 17 locally reviewed six-player boxes. It tracks torso '
             'features through every source frame over 0.4 s before and after the anchor, '
             'then translates each player box to five 5 Hz sample times. The method works '
             'in image pixels and retains airborne players as screen-space candidates.', '',
             'The [endpoint source review](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_source_qc.json) '
             'checks the unboxed source and translated boxes at the first, anchor and last '
             'sample for all 17 windows. All 17 have six *algorithmic* candidates at five '
             'sample times. Thirteen have no obvious wrong-person transfer at the displayed '
             'endpoints; four remain uncertain due to crossings or net overlap. After removing '
             'two serve/reset windows and set-and-phase groups without both outcomes, only '
             '**8/18** frozen points remain as short candidate comparison windows. '
             'These eight are not fully validated trajectories.', '',
             '| Check | Result |', '| --- | ---: |',
             '| Frozen point denominator | 18 |',
             '| Correct six-box anchors | 17 |',
             '| Six flow candidates at all five samples | 17 |',
             '| No obvious transfer at displayed endpoints | 13 |',
             '| Uncertain overlap at displayed endpoints | 4 |',
             '| Clear endpoint, open-play anchor | 11 |',
             '| Clear endpoint, open-play and set-phase matched | 8 |',
             f"| Same-raw-ID detector comparisons | {len(ordered)} |",
             f"| Median / 95th-percentile / maximum detector disagreement (px) | "
             f"{summary['median_same_raw_id_detector_disagreement_px']:.2f} / "
             f"{summary['p95_same_raw_id_detector_disagreement_px']:.2f} / "
             f"{summary['maximum_same_raw_id_detector_disagreement_px']:.2f} |",
             '| Validated court-trajectory windows | 0 |', '',
             'The detector comparison uses the same video and raw IDs, so it is **not an '
             'independent manual accuracy reference**. A translated rigid box cannot adjust '
             'to pose or height changes. The two ±0.4 s endpoints were visually screened, '
             'but the intermediate samples were not adjudicated for named identity; none of '
             'the floor positions has passed the court-metric gate. The four uncertain '
             'windows stay unresolved. The 18th frozen point remains missing six correct '
             'anchor boxes. This pilot improves short image-plane coverage but does not '
             'unlock a statistical court-metric outcome analysis.', '',
             'The [row-level audit](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_audit.json) '
             'and [review sheets](../data/matches/yt_u5HnY2aNW14/screening/box_centre_flow_pilot/) '
             'retain every point and overlay. Reproduce with '
             '`python scripts/pilot_u5_box_centre_flow.py` followed by '
             '`python scripts/audit_u5_box_centre_flow.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
