"""Record one-reviewer source adjudication of the set-three matched-window pilot."""
import hashlib
import json
import statistics
from pathlib import Path

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
VIDEO = BASE.parent / 'source_720p.mp4'
MOTION = BASE / 'long_run_proxy_motion_diagnostic.json'
OLD_TRACKS = BASE / 'dense_live_track_screen.json'
NEW_TRACKS = BASE / 'highres_winning_run_screen.json'
ORIGINAL = BASE / 'matched_window_pilot/index.json'
REVISED = BASE / 'matched_window_pilot_phase/index.json'
OUT = BASE / 'matched_window_pilot_source_qc.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_MATCHED_WINDOW_PILOT.md'
METRICS = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    motion = json.loads(MOTION.read_text(encoding='utf-8'))
    old_tracks = json.loads(OLD_TRACKS.read_text(encoding='utf-8'))
    new_tracks = json.loads(NEW_TRACKS.read_text(encoding='utf-8'))
    packs = {'initial': json.loads(ORIGINAL.read_text(encoding='utf-8')),
             'revised_phase': json.loads(REVISED.read_text(encoding='utf-8'))}
    source = sha(VIDEO)
    assert motion['source_sha256'] == old_tracks['source_sha256'] == new_tracks['source_sha256'] == source
    assert all(pack['source_sha256'] == source for pack in packs.values())
    runs = {(r['set'], r['point_number']): {f['source_frame']: f for f in r['frames']}
            for r in motion['runs']}
    win_track = next(p for p in new_tracks['points'] if (p['set'], p['point_number']) == (3, 13))
    loss_track = next(p for p in old_tracks['points'] if (p['set'], p['point_number']) == (3, 34))
    screen_boxes = {
        13: {r['source_frame']: r['near_floor_side_proposals'] for r in win_track['rows']},
        34: {r['source_frame']: [p for p in r['proposals']
                                if p['net_side_status'] == 'near_floor_side_candidate']
             for r in loss_track['rows']},
    }
    decisions = {
        ('initial', 13): {
            'phase': 'near_side_attack_followed_by_far_side_scramble',
            'ground': 'failed',
            'notes': {29881: 'UCLA raw ID 2 has both shoes visibly above the floor.',
                      29887: 'Raw ID 2 is landing or striding; box bottom is not a checked contact.',
                      29893: 'Raw ID 2 is moving rapidly; box bottom is not a checked contact.',
                      29899: 'Raw ID 2 is in a fast lateral step with uncertain support foot.',
                      29905: 'One shoe of raw ID 2 appears planted, but six ground anchors are not certified.'},
        },
        ('initial', 34): {
            'phase': 'opponent_attack_setup',
            'ground': 'not_certified',
            'notes': {f: 'Six near-side boxes are visible; plausible shoe contact does not validate each box-bottom anchor.'
                      for f in (36054, 36060, 36066, 36072, 36078)},
        },
        ('revised_phase', 13): {
            'phase': 'opponent_attack_setup_candidate',
            'ground': 'uncertain',
            'notes': {f: 'All six near-side boxes appear; fast lateral footwork or overlap leaves box-bottom ground contact unverified.'
                      for f in (29917, 29923, 29929, 29935, 29941)},
        },
        ('revised_phase', 34): {
            'phase': 'opponent_attack_setup_candidate',
            'ground': 'not_certified',
            'notes': {f: 'Six near-side boxes are visible; plausible shoe contact does not validate each box-bottom anchor.'
                      for f in (36054, 36060, 36066, 36072, 36078)},
        },
    }
    windows = []
    for name, pack in packs.items():
        assert len(pack['rows']) == 10
        for point in (13, 34):
            rows = [r for r in pack['rows'] if r['point_number'] == point]
            frames = [r['source_frame'] for r in rows]
            assert len(frames) == 5 and all(b - a == 6 for a, b in zip(frames, frames[1:]))
            assert (name, point) in decisions and set(decisions[name, point]['notes']) == set(frames)
            for row in rows:
                for kind, file in row['files'].items():
                    path = (BASE / ('matched_window_pilot_phase' if name == 'revised_phase'
                                    else 'matched_window_pilot') / file)
                    assert sha(path) == row['sha256'][kind]
            diagnostic = [runs[3, point][f]['proxy_metrics'] for f in frames]
            screen_values = []
            for frame in frames:
                proposals = screen_boxes[point][frame]
                assert len(proposals) == 6 and len({p['raw_track_id'] for p in proposals}) == 6
                centres = [((p['bbox_px'][0] + p['bbox_px'][2]) / 2,
                            (p['bbox_px'][1] + p['bbox_px'][3]) / 2)
                           for p in sorted(proposals, key=lambda p: p['raw_track_id'])]
                screen_values.append(metrics(centres))
            windows.append({'pilot': name, 'set': 3, 'point_number': point,
                            'near_team_won': point == 13, 'source_frames': frames,
                            'duration_s': round((frames[-1] - frames[0]) / 30, 1),
                            'source_team_membership': 'six_correct_near_side_teammates_each_sampled_frame',
                            'phase_review': decisions[name, point]['phase'],
                            'ground_contact_gate': decisions[name, point]['ground'],
                            'frame_notes': [{'source_frame': f, 'note': decisions[name, point]['notes'][f]}
                                            for f in frames],
                            'provisional_box_bottom_medians': {
                                k: round(statistics.median(v[k] for v in diagnostic), 3)
                                for k in METRICS},
                            'image_plane_box_centre_candidate_frames': 5,
                            'image_plane_box_centre_medians': {
                                'mean_pairwise_spacing_px': round(statistics.median(
                                    v['mean_pairwise_spacing_m'] for v in screen_values), 1),
                                'convex_hull_area_px2': round(statistics.median(
                                    v['convex_hull_area_m2'] for v in screen_values), 1),
                                'centroid_dispersion_px': round(statistics.median(
                                    v['centroid_dispersion_m'] for v in screen_values), 1),
                            },
                            'strict_eligible_metric_frames': 0,
                            'source_pack': ('matched_window_pilot_phase' if name == 'revised_phase'
                                            else 'matched_window_pilot') + '/index.json'})
    assert len(windows) == 4
    output = {'status': 'one_reviewer_matched_window_pilot_not_final_outcome_analysis',
              'source_sha256': source,
              'input_sha256': {'motion': sha(MOTION), 'original_tracks': sha(OLD_TRACKS),
                               'highres_tracks': sha(NEW_TRACKS), 'initial_pack': sha(ORIGINAL),
                               'revised_pack': sha(REVISED)},
              'primary_selection_rule': packs['initial']['selection_rule'],
              'revised_selection_rule': packs['revised_phase']['selection_rule'],
              'summary': {'primary_windows': 2, 'revised_windows': 2,
                          'samples_per_window': 5, 'duration_s': 0.8,
                          'image_plane_box_centre_candidate_frames_per_window': 5,
                          'strict_eligible_windows': 0,
                          'strict_eligible_metric_frames': 0},
              'windows': windows,
              'decision': ('Airborne frames remain usable as image-plane box-centre candidates; '
                           'height and pose still affect pixel centres. The initially fixed '
                           'windows are not phase matched. The revised opponent-attack candidates '
                           'are exploratory, with one point per outcome. Neither selection '
                           'supports a winner association, and neither supplies certified '
                           'court-floor positions for metre-valued metrics.')}
    OUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    lines = [
        '# Set-three matched-window pilot', '',
        'This pilot used one UCLA win (point 13) and one UCLA loss (point 34). '
        'The [source-bound review record](../data/matches/yt_u5HnY2aNW14/screening/matched_window_pilot_source_qc.json) '
        'retains both attempts and their frame notes. Each candidate window spans five '
        '5 Hz samples over 0.8 s. Team membership at the sampled instants was checked '
        'against the source video by one reviewer.', '',
        '**Measurement distinction:** Airborne players can still be tracked by the '
        'centre of their image boxes. That gives pixel-space motion and geometry; '
        'it does not require a visible shoe contact. This camera is elevated and '
        'oblique rather than exactly overhead, and a body-box centre changes with '
        'pose and height. Projecting that centre through the floor homography would '
        'not yield a verified court-floor position.', '',
        '## Fixed first-run window', '',
        'The rule was the **first five consecutive samples** of each point’s longest '
        'six-ID run, chosen before this frame-level ground review. The win frames are '
        '29881–29905; the loss frames are 36054–36078. The [winning source pack]'
        '(../data/matches/yt_u5HnY2aNW14/screening/matched_window_pilot/) '
        'shows raw ID 2 with both shoes above the floor at frame 29881. Its subsequent '
        'rapid footwork makes box-bottom support uncertain. The win shows a near-side '
        'attack followed by a far-side scramble; the loss shows the opponent preparing '
        'an attack. These are different phases. The fixed-window pilot therefore '
        'fails the **matched-phase outcome comparison**. Its box centres remain '
        'usable as image-plane candidates; its box bottoms do not pass the '
        'metre-valued court-position gate.', '',
        '## Revised phase candidate', '',
        'After that failure, a second exploratory candidate used win frames 29917–29941 '
        'and the same loss frames. The [revised source pack]'
        '(../data/matches/yt_u5HnY2aNW14/screening/matched_window_pilot_phase/) '
        'shows both teams near an opponent attack setup. This was selected after '
        'inspecting phase images, so it is a method-development pilot rather than a '
        'prespecified outcome window. The winning player’s fast lateral footwork and '
        'overlap still prevent certification of six grounded box-bottom anchors on '
        'every sample for the floor-homography method. Exact ball contact and the '
        'full live window are not certified.', '',
        '| Candidate | Point | Result | Frames | Median proxy spacing (m) | '
        'Median proxy hull (m²) | Median proxy dispersion (m) | Strict eligible frames |',
        '| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |',
    ]
    for row in windows:
        m = row['provisional_box_bottom_medians']
        lines.append(f"| {row['pilot']} | {row['point_number']} | "
                     f"{'Won' if row['near_team_won'] else 'Lost'} | "
                     f"{row['source_frames'][0]}–{row['source_frames'][-1]} | "
                     f"{m['mean_pairwise_spacing_m']:.3f} | {m['convex_hull_area_m2']:.3f} | "
                     f"{m['centroid_dispersion_m']:.3f} | 0 |")
    lines += ['', 'The same 20 displayed frame instances also have six image-plane '
              'box-centre coordinates each. Their per-window median pixel-space '
              'geometry is recorded in the JSON; the repeated loss window means '
              'there are 15 distinct source frames. Airborne status alone does '
              'not exclude these screen-space candidates.', '',
              '| Candidate | Point | Image spacing (px) | Image hull (px²) | '
              'Image dispersion (px) |',
              '| --- | ---: | ---: | ---: | ---: |']
    for row in windows:
        m = row['image_plane_box_centre_medians']
        lines.append(f"| {row['pilot']} | {row['point_number']} | "
                     f"{m['mean_pairwise_spacing_px']:.1f} | {m['convex_hull_area_px2']:.1f} | "
                     f"{m['centroid_dispersion_px']:.1f} |")
    lines += ['',
              'The metre-valued numbers above are **box-bottom implementation diagnostics**. The loss '
              'window is repeated in the two attempts, and there is one point per '
              'outcome. No winner effect size or significance test is justified.', '',
              '**Decision:** The initial windows are not phase matched. The revised '
              'windows are exploratory and have only one point per outcome. Pixel-space '
              'box-centre tracking is feasible in these frames, including airborne '
              'ones, but neither attempt supplies a validated six-player court-metric '
              'window or a defensible winner comparison. A final court-coordinate '
              'analysis still needs a common phase rule, checked floor-position '
              'proxy and enough eligible points in both outcome groups.', '',
              'Reproduce with `python scripts/render_u5_matched_window_pilot.py`, '
              '`python scripts/render_u5_matched_window_pilot.py --phase-aligned`, '
              'then `python scripts/adjudicate_u5_matched_window_pilot.py`.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print(output['summary'])


if __name__ == '__main__':
    main()
