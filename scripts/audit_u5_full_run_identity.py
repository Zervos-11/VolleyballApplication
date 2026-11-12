"""Bind every-sample visual jersey review to the two long raw-ID runs."""

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SCREEN = BASE / 'full_clip_track_screen.json'
TRACKLETS = BASE / 'full_clip_tracklet_audit.json'
ATLAS = BASE / 'full_clip_run_spotcheck/all_samples_crop_manifest.json'
QC = BASE / 'full_run_identity_qc.json'
OUT = BASE / 'full_run_identity_audit.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_FULL_RUN_IDENTITY_AUDIT.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    screen = json.loads(SCREEN.read_text(encoding='utf-8'))
    tracklets = json.loads(TRACKLETS.read_text(encoding='utf-8'))
    atlas = json.loads(ATLAS.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    assert tracklets['input_sha256']['full_clip_screen'] == sha(SCREEN)
    assert atlas['source_sha256'] == screen['source_sha256']
    assert atlas['screen_sha256'] == sha(SCREEN)
    assert atlas['tracklet_audit_sha256'] == sha(TRACKLETS)
    by_screen = {(p['set'], p['point_number']): p for p in screen['points']}
    by_tracklet = {(p['set'], p['point_number']): p for p in tracklets['points']}
    by_atlas = {}
    for page in atlas['rows']:
        key = page['set'], page['point_number']
        assert sha(ROOT / 'data/matches/yt_u5HnY2aNW14' / page['image']) == page['image_sha256']
        by_atlas.setdefault(key, []).append(page)
    assert len(qc['rows']) == len(by_atlas) == 2
    rows_out = []
    for review in qc['rows']:
        key = review['set'], review['point_number']
        run = by_tracklet[key]['longest_same_six_raw_id_run_full_clip']
        assert run['sampled_frames'] == review['sampled_frames_reviewed'] == 18
        assert (run['first_frame'], run['last_frame']) == (
            review['first_source_frame'], review['last_source_frame'])
        assert set(map(str, run['raw_track_ids'])) == set(review['raw_id_to_jersey_number'])
        pages = sorted(by_atlas[key], key=lambda r: r['page'])
        assert [p['page'] for p in pages] == [1, 2, 3]
        assert all(p['raw_track_ids'] == run['raw_track_ids'] for p in pages)
        frames = [frame for page in pages for frame in page['frames']]
        assert frames == list(range(run['first_frame'], run['last_frame'] + 1, 6))
        assert review['sampled_identity_status'] == 'six_same_visible_jerseys_at_all_eighteen_samples'
        assert review['obvious_sampled_identity_switches'] == 0
        assert review['court_floor_position_status'] == 'not_validated_by_identity_crop_review'
        screen_rows = {r['source_frame']: r for r in by_screen[key]['rows']}
        player_rows = []
        for raw_id in run['raw_track_ids']:
            positions = []
            for frame in frames:
                matches = [p for p in screen_rows[frame]['proposals']
                           if p['raw_track_id'] == raw_id and
                           p['net_side_status'] == 'near_floor_side_candidate']
                assert len(matches) == 1
                positions.append(matches[0]['box_bottom_court_m'])
            steps = [math.dist(a, b) for a, b in zip(positions, positions[1:])]
            player_rows.append({'raw_track_id': raw_id,
                                'reviewed_visible_jersey_number': review['raw_id_to_jersey_number'][str(raw_id)],
                                'sampled_frames': len(positions),
                                'max_successive_box_bottom_proxy_change_m': round(max(steps), 3),
                                'sampled_box_bottom_proxy_polyline_m': round(sum(steps), 3),
                                'first_to_last_box_bottom_proxy_chord_m': round(math.dist(positions[0], positions[-1]), 3)})
        rows_out.append({'set': key[0], 'point_number': key[1],
                         'near_team': review['near_team'],
                         'sampled_source_frames': frames,
                         'sampled_identity_status': review['sampled_identity_status'],
                         'obvious_sampled_identity_switches': 0,
                         'exact_live_play_interval_status': review['exact_live_play_interval_status'],
                         'court_floor_position_status': review['court_floor_position_status'],
                         'atlas_pages': [p['image'] for p in pages],
                         'players': player_rows})
    out = {'status': 'two_selected_runs_identity_checked_at_all_five_hz_samples_only',
           'source_sha256': screen['source_sha256'],
           'input_sha256': {'full_clip_screen': sha(SCREEN),
                            'full_clip_tracklets': sha(TRACKLETS),
                            'atlas_manifest': sha(ATLAS), 'manual_qc': sha(QC)},
           'summary': {'runs_reviewed': 2, 'sampled_team_frames_reviewed': 36,
                       'sampled_person_boxes_reviewed': 216,
                       'obvious_sampled_identity_switches': 0,
                       'runs_with_certified_inter_sample_identity': 0,
                       'runs_with_validated_court_floor_trajectory': 0,
                       'validated_full_rallies': 0},
           'rows': rows_out, 'limitations': qc['limitations']}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    lines = ['# Every-sample identity review of two selected raw runs', '',
             'The [source-bound audit](../data/matches/yt_u5HnY2aNW14/screening/full_run_identity_audit.json) '
             'reviews all 18 five-Hz source frames in each of the two longest same-six-ID '
             'candidate runs: **36 team frames and 216 person crops**. Six distinct UCLA '
             'jerseys remain associated with the same raw IDs at every displayed sample. '
             'White #28 is UCLA’s near-side libero. This is a single-reviewer visual '
             'continuity check, not a review of the five 30-fps frames between each pair '
             'of samples.', '',
             '| Point | Source frames | Visible jersey numbers by raw ID | Obvious sampled switches |',
             '| --- | --- | --- | ---: |']
    for row in rows_out:
        mapping = ', '.join(f"{p['raw_track_id']}→#{p['reviewed_visible_jersey_number']}"
                            for p in row['players'])
        lines.append(f"| S{row['set']} P{row['point_number']} | "
                     f"{row['sampled_source_frames'][0]}–{row['sampled_source_frames'][-1]} "
                     f"(18 at 5 Hz) | {mapping} | 0 |")
    lines += ['', 'The six [S1 P5 crop pages](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s1_p05_all_samples_crops_1.png) '
              'and [S3 P34 crop pages](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/s3_p34_all_samples_crops_1.png) '
              'are indexed with hashes in the [atlas manifest](../data/matches/yt_u5HnY2aNW14/screening/full_clip_run_spotcheck/all_samples_crop_manifest.json). '
              'Each point has three six-frame pages. The audit records box-bottom '
              'court-proxy changes per ID as a motion diagnostic, not physical travel.', '',
              '**Remaining accuracy limits:** exact serve-to-point-end intervals are '
              'not certified for these runs; the frames between 5 Hz samples could '
              'contain an unobserved swap or jump; and no manual shoe contact points '
              'were supplied for all 216 boxes. Prior [manual position checks]'
              '(HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) quantify selected proxy error '
              'elsewhere but do not validate these entire paths. The strict full-rally '
              'court-trajectory count remains **zero**.', '',
              'Reproduce with `python scripts/render_u5_full_run_identity_atlas.py` '
              'and `python scripts/audit_u5_full_run_identity.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(out['summary'])


if __name__ == '__main__':
    main()
