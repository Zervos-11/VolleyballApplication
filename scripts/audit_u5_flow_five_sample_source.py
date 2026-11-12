"""Verify and report the conservative five-instant source-image screen."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
INDEX = BASE / 'flow_window_five_sample_review/index.json'
QC = BASE / 'flow_window_five_sample_source_qc.json'
GEOMETRY = BASE / 'flow_window_image_geometry.json'
OUT = BASE / 'flow_window_five_sample_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FIVE_SAMPLE_SOURCE_REVIEW.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    geometry = json.loads(GEOMETRY.read_text(encoding='utf-8'))
    assert qc['review_sheet_index_sha256'] == sha(INDEX)
    assert index['source_sha256'] == geometry['source_sha256']
    assert index['pilot_sha256'] == geometry['input_sha256']['pilot']
    assert index['window_sha256'] == sha(GEOMETRY)
    by_key = {(r['set'], r['point_number']): r for r in qc['rows']}
    assert len(by_key) == len(qc['rows']) == len(index['rows']) == len(geometry['rows']) == 8
    geometry_keys = {(r['set'], r['point_number']) for r in geometry['rows']}
    rows = []
    for row in index['rows']:
        key = row['set'], row['point_number']
        assert key in geometry_keys
        assert sha(BASE / 'flow_window_five_sample_review' / row['sheet']) == row['sha256']
        assert row['source_frames'] == next(g['source_window_frames'] for g in geometry['rows']
                                             if (g['set'], g['point_number']) == key)
        status = by_key[key]['status']
        assert status in ('no_obvious_wrong_person_transfer_at_five_samples',
                          'uncertain_transfer_at_five_samples')
        rows.append({'set': key[0], 'point_number': key[1],
                     'near_team_won': row['near_team_won'],
                     'source_frames': row['source_frames'], 'sheet': row['sheet'],
                     'sheet_sha256': row['sha256'], 'visual_status': status,
                     'note': by_key[key]['note']})
    clear = sum(r['visual_status'] == 'no_obvious_wrong_person_transfer_at_five_samples'
                for r in rows)
    summary = {'candidate_windows': len(rows), 'sample_instants_per_window': 5,
               'source_frame_instances_screened': len(rows) * 5,
               'no_obvious_transfer_at_five_displayed_instants': clear,
               'uncertain_transfer_at_five_displayed_instants': len(rows)-clear,
               'independently_labelled_player_centres': 0,
               'validated_court_trajectory_windows': 0}
    out = {'status': 'coarse_visual_sample_screen_not_tracking_accuracy_validation',
           'source_sha256': index['source_sha256'],
           'input_sha256': {'review_index': sha(INDEX), 'manual_source_qc': sha(QC),
                            'image_geometry': sha(GEOMETRY)},
           'summary': summary, 'rows': rows,
           'interpretation': ('A single reviewer saw no obvious wrong-person transfer in '
                              'the displayed five instants of all eight selected windows. '
                              'This screen cannot verify intermediate source frames, box-centre '
                              'accuracy, named identity, ground contact, or court coordinates. '
                              'One window contains a player beyond the sideline and another '
                              'contains a low posture near the net.')}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Five-sample source-image review', '',
             'I inspected the [five-frame overlay sheets](../data/matches/yt_u5HnY2aNW14/screening/flow_window_five_sample_review/) '
             'for each of the eight screened 0.8 s candidate windows. The [review record](../data/matches/yt_u5HnY2aNW14/screening/flow_window_five_sample_source_qc.json) '
             'is bound to the sheet index and every image hash is checked by the '
             '[audit](../data/matches/yt_u5HnY2aNW14/screening/flow_window_five_sample_audit.json). '
             'At the five displayed instants, all eight have six boxes that appear to remain '
             'with the same near-side people. This is a coarse transfer screen, not a '
             'position-error measurement or certified player identity.', '',
             '| Point | Screen result | Qualification |', '| --- | --- | --- |']
    for row in rows:
        lines.append(f"| S{row['set']} P{row['point_number']} | No obvious transfer at five instants | "
                     f"{row['note']} |")
    lines += ['', 'The source frames between displayed instants, box-centre error, floor '
              'contact and court positions are not manually labelled. S1 P18 includes a '
              'player beyond the sideline; S2 P28 includes a low posture near the net. '
              'The earlier [pixel-space geometry](HONOURS_U5_FLOW_WINDOW_GEOMETRY.md) remains '
              'a method diagnostic. This review leaves **zero validated court trajectory '
              'windows**, so the signed court-metric outcome comparison remains incomplete.', '',
              'Reproduce the audit with `python scripts/audit_u5_flow_five_sample_source.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
