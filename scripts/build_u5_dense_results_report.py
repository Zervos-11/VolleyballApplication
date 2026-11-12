"""Build the UCLA-Concordia dense screening and metric-feasibility report."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
FILES = {
    'sample': BASE / 'rally_sample_score_only.json',
    'cuts': BASE / 'rally_cut_clip_register.json',
    'cut_qc': BASE / 'rally_cut_boundary_source_qc.json',
    'tracks': BASE / 'dense_live_track_screen.json',
    'continuity': BASE / 'dense_live_continuity_audit.json',
    'phase': BASE / 'selected_phase_source_qc.json',
    'roster': BASE / 'seeded_roster_coverage.json',
    'windows': BASE / 'anchor_live_window_availability.json',
    'floor': BASE / 'floor_proxy_reference_audit.json',
    'heldout_floor': BASE / 'heldout_box_floor_error.json',
    'metrics': BASE / 'provisional_live_snapshot_metrics.json',
    'core': BASE / 'cut_bounded_provisional_rally_metrics.json',
    'core_phase_audit': BASE / 'provisional_core_phase_counterexamples.json',
    'phase_review_index': BASE / 'frozen_clip_phase_review/index.json',
    'coarse_phase': BASE / 'coarse_phase_brackets.json',
    'event_transition_index': BASE / 'event_transition_review/index.json',
    'event_transition_qc': BASE / 'event_transition_source_qc.json',
    'coarse_coverage': BASE / 'coarse_phase_candidate_coverage.json',
    'bracketed_qc_index': BASE / 'bracketed_candidate_qc/index.json',
    'bracketed_source_qc': BASE / 'bracketed_candidate_source_qc.json',
    'selected_floor_qc_index': BASE / 'selected_floor_qc/index.json',
    's1p37_identity_run': BASE / 's1p37_short_identity_run.json',
    'interior_runs': BASE / 'interior_identity_run_availability.json',
    'interior_run_review_index': BASE / 'interior_run_review/index.json',
    'interior_run_anchor_qc': BASE / 'interior_run_source_qc.json',
    'winning_short_review_index': BASE / 'winning_short_run_review/index.json',
    'winning_short_source_qc': BASE / 'winning_short_run_source_qc.json',
    'zero_run_source_index': BASE / 'zero_run_source_review/index.json',
    'zero_run_source_qc': BASE / 'zero_run_source_qc.json',
    'zero_run_high_res_qc': BASE / 'zero_run_high_res_source_qc.json',
    'zero_run_high_res_index': BASE / 'zero_run_high_res_detection/index.json',
    'highres_winning_runs': BASE / 'highres_winning_run_screen.json',
    'highres_winning_run_qc': BASE / 'highres_winning_run_source_qc.json',
    'visibility_ledger': BASE / 'source_visibility_ledger.json',
    'selected_proxy_sensitivity': BASE / 'selected_proxy_sensitivity.json',
    'camera_registration': BASE / 'selected_camera_registration.json',
    'boundary': BASE / 'net_boundary_adjudication.json',
}
OUT = ROOT / 'DELIVERABLES/HONOURS_U5_DENSE_RESULTS_AND_READINESS.md'
MANIFEST = BASE / 'dense_results_report_manifest.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = {key: json.loads(path.read_text(encoding='utf-8')) for key, path in FILES.items()}
    tracks = data['tracks']
    continuity = data['continuity']
    phase = data['phase']
    roster = data['roster']
    windows = data['windows']
    floor = data['floor']
    heldout_floor = data['heldout_floor']
    result = data['metrics']
    boundary = data['boundary']
    sample = data['sample']
    cuts = data['cuts']
    cut_qc = data['cut_qc']
    core = data['core']
    core_phase_audit = data['core_phase_audit']
    phase_review_index = data['phase_review_index']
    coarse_phase = data['coarse_phase']
    event_transition_index = data['event_transition_index']
    event_transition_qc = data['event_transition_qc']
    coarse_coverage = data['coarse_coverage']
    bracketed_qc_index = data['bracketed_qc_index']
    bracketed_source_qc = data['bracketed_source_qc']
    selected_floor_qc_index = data['selected_floor_qc_index']
    s1p37_identity_run = data['s1p37_identity_run']
    interior_runs = data['interior_runs']
    interior_run_review_index = data['interior_run_review_index']
    interior_run_anchor_qc = data['interior_run_anchor_qc']
    winning_short_review_index = data['winning_short_review_index']
    winning_short_source_qc = data['winning_short_source_qc']
    zero_run_source_index = data['zero_run_source_index']
    zero_run_source_qc = data['zero_run_source_qc']
    zero_run_high_res_qc = data['zero_run_high_res_qc']
    highres_winning_run_qc = data['highres_winning_run_qc']
    visibility_ledger = data['visibility_ledger']
    selected_proxy_sensitivity = data['selected_proxy_sensitivity']
    camera_registration = data['camera_registration']
    if not (tracks['source_sha256'] == result['source_sha256'] == floor['source_sha256']):
        raise ValueError('Different source videos')
    if sample['source_sha256'] != tracks['source_sha256']:
        raise ValueError('Frozen sample and track source videos differ')
    if cuts['source_sha256'] != tracks['source_sha256'] or cuts['frozen_sample_sha256'] != sha(FILES['sample']):
        raise ValueError('Edit-cut register does not match source video or frozen sample')
    if cut_qc['cut_register_sha256'] != sha(FILES['cuts']) or cut_qc['summary']['visually_confirmed_edit_bounds'] != 18:
        raise ValueError('Selected edit cuts are not all source reviewed')
    if (core['dense_tracks_sha256'] != sha(FILES['tracks']) or
            core['cut_register_sha256'] != sha(FILES['cuts']) or
            core_phase_audit['candidate_screen_sha256'] != sha(FILES['core'])):
        raise ValueError('Core phase audit is not bound to the current tracker and cut register')
    if core_phase_audit['confirmed_non_live_candidate_frames'] < 1:
        raise ValueError('Expected source-visible non-live counterexamples')
    if (phase_review_index['cut_register_sha256'] != sha(FILES['cuts']) or
            phase_review_index['source_sha256'] != tracks['source_sha256'] or
            phase_review_index['point_count'] != 18):
        raise ValueError('Clip phase review pack differs from current source and cuts')
    if (coarse_phase['review_index_sha256'] != sha(FILES['phase_review_index']) or
            coarse_coverage['coarse_brackets_sha256'] != sha(FILES['coarse_phase']) or
            coarse_coverage['candidate_screen_sha256'] != sha(FILES['core']) or
            coarse_coverage['counterexample_audit_sha256'] != sha(FILES['core_phase_audit'])):
        raise ValueError('Coarse phase bracket or coverage screen differs from reviewed sources')
    if (event_transition_index['coarse_brackets_sha256'] != sha(FILES['coarse_phase']) or
            event_transition_qc['event_transition_index_sha256'] != sha(FILES['event_transition_index']) or
            event_transition_qc['summary']['points_with_conservative_live_interiors'] != 18):
        raise ValueError('Event transition review differs from current source brackets')
    if (bracketed_qc_index['candidate_screen_sha256'] != sha(FILES['core']) or
            bracketed_qc_index['coarse_brackets_sha256'] != sha(FILES['coarse_phase']) or
            bracketed_source_qc['review_index_sha256'] != sha(FILES['bracketed_qc_index']) or
            bracketed_source_qc['summary']['validated_metric_frames'] != 0):
        raise ValueError('Bracketed candidate source QC differs from current screen')
    if (selected_floor_qc_index['bracketed_source_qc_sha256'] != sha(FILES['bracketed_source_qc']) or
            len(selected_floor_qc_index['entries']) != 15):
        raise ValueError('Shoe-level review pack differs from current local source adjudication')
    if (s1p37_identity_run['bracketed_qc_sha256'] != sha(FILES['bracketed_source_qc']) or
            s1p37_identity_run['tracks_sha256'] != sha(FILES['tracks']) or
            len(s1p37_identity_run['sampled_source_frames']) != 10):
        raise ValueError('Source-reviewed short identity run differs from current local QC')
    if (interior_runs['candidate_screen_sha256'] != sha(FILES['core']) or
            interior_runs['live_interior_sha256'] != sha(FILES['event_transition_qc']) or
            interior_runs['short_identity_audit_sha256'] != sha(FILES['s1p37_identity_run']) or
            interior_runs['summary']['frozen_points'] != 18):
        raise ValueError('Interior identity availability differs from current candidate screen')
    if (interior_run_review_index['run_audit_sha256'] != sha(FILES['interior_runs']) or
            interior_run_anchor_qc['review_index_sha256'] != sha(FILES['interior_run_review_index']) or
            interior_run_anchor_qc['summary']['runs_with_correct_team_at_all_sampled_frames'] != 7):
        raise ValueError('Interior run source anchor check differs from current run review')
    if (winning_short_review_index['run_audit_sha256'] != sha(FILES['interior_runs']) or
            winning_short_source_qc['review_index_sha256'] != sha(FILES['winning_short_review_index']) or
            winning_short_source_qc['summary']['frozen_near_team_wins'] != 9):
        raise ValueError('Winning short-run source QC differs from current run review')
    if (zero_run_source_index['runs_sha256'] != sha(FILES['interior_runs']) or
            zero_run_source_index['intervals_sha256'] != sha(FILES['event_transition_qc']) or
            zero_run_source_qc['review_index_sha256'] != sha(FILES['zero_run_source_index']) or
            zero_run_source_qc['summary']['points_with_six_visible_teammates_in_source'] != 3):
        raise ValueError('Detector-zero source QC differs from current run or interval review')
    if (zero_run_high_res_qc['summary']['recovered_local_six_box_instants'] != 2 or
            zero_run_high_res_qc['detection_index_sha256'] != sha(FILES['zero_run_high_res_index']) or
            zero_run_high_res_qc['source_sha256'] != tracks['source_sha256']):
        raise ValueError('High-resolution recovery QC differs from current source evidence')
    if (highres_winning_run_qc['run_audit_sha256'] != sha(FILES['highres_winning_runs']) or
            len(highres_winning_run_qc['source_frames']) != 13 or
            highres_winning_run_qc['source_sha256'] != tracks['source_sha256']):
        raise ValueError('High-resolution winning run QC differs from current source evidence')
    if (visibility_ledger['input_sha256']['local_boxes'] != sha(FILES['bracketed_source_qc']) or
            visibility_ledger['input_sha256']['zero_run_source'] != sha(FILES['zero_run_source_qc']) or
            visibility_ledger['summary']['points_with_six_source_visible_teammates'] != 18 or
            visibility_ledger['summary']['validated_six_player_metric_frames'] != 0):
        raise ValueError('Source visibility ledger differs from reviewed source evidence')
    if (selected_proxy_sensitivity['input_sha256']['review'] != sha(FILES['bracketed_source_qc']) or
            selected_proxy_sensitivity['input_sha256']['crops'] != sha(FILES['selected_floor_qc_index']) or
            selected_proxy_sensitivity['input_sha256']['floor_reference'] != sha(FILES['floor']) or
            selected_proxy_sensitivity['input_sha256']['heldout_reference'] != sha(FILES['heldout_floor']) or
            selected_proxy_sensitivity['summary']['validated_grounded_metric_frames'] != 0):
        raise ValueError('Selected-frame proxy sensitivity differs from current source evidence')
    if (heldout_floor['input_sha256']['earlier_reference'] != sha(FILES['floor']) or
            heldout_floor['summary']['reviewed_clear_grounded_shoe_pairs'] != 21):
        raise ValueError('Held-out shoe reference differs from earlier source evidence')
    if (camera_registration['input_sha256']['selected_qc'] != sha(FILES['bracketed_source_qc']) or
            camera_registration['input_sha256']['zero_run_review'] != sha(FILES['zero_run_source_index']) or
            camera_registration['input_sha256']['calibration'] != sha(BASE / 'near_court_candidate.json') or
            camera_registration['summary']['frozen_points_covered'] != 18):
        raise ValueError('Court-image registration differs from current source evidence')
    if continuity['frozen_sample_sha256'] != sha(FILES['sample']) or result['frozen_sample_sha256'] != sha(FILES['sample']):
        raise ValueError('Audit or provisional values do not match the frozen sample')
    if continuity['dense_track_screen_sha256'] != sha(FILES['tracks']):
        raise ValueError('Continuity audit does not match dense tracks')
    if roster['dense_tracks_sha256'] != sha(FILES['tracks']):
        raise ValueError('Roster audit does not match dense tracks')
    if result['source_phase_qc_sha256'] != sha(FILES['phase']):
        raise ValueError('Metric demonstration does not match phase review')
    if roster['source_phase_qc_sha256'] != sha(FILES['phase']):
        raise ValueError('Roster diagnostic does not match phase review')
    if windows['source_phase_qc_sha256'] != sha(FILES['phase']) or windows['dense_tracks_sha256'] != sha(FILES['tracks']):
        raise ValueError('Anchor-run audit does not match tracks or phase review')
    selected = {(r['set'], r['point_number']) for r in sample['selected_events']}
    clip_by_key = {(r['set'], r['point_number']): r for r in cuts['selected_clips']}
    if set(clip_by_key) != selected:
        raise ValueError('Edit-cut clips differ from frozen selection')
    for point in tracks['points']:
        clip = clip_by_key[point['set'], point['point_number']]
        if any(not clip['clip_start_frame_inclusive'] <= row['source_frame'] < clip['clip_end_frame_exclusive']
               for row in point['rows']):
            raise ValueError('Dense tracker frame crosses an edited rally clip boundary')
    for label, rows in [('continuity', continuity['points']), ('phase', phase['rows']), ('roster', roster['rows']), ('windows', windows['rows'])]:
        keys = [(r['set'], r['point_number']) for r in rows]
        if len(keys) != len(selected) or set(keys) != selected:
            raise ValueError(f'{label} point keys differ from frozen selection')
    live = {(r['set'], r['point_number']) for r in phase['rows'] if r['local_phase_status'] == 'visible_live_play'}
    if not {(r['set'], r['point_number']) for r in result['rows']} <= live:
        raise ValueError('Provisional metrics contain a non-live selected frame')
    clip_table = '\n'.join(
        f"| {r['set']} | {r['point_number']} | {r['clip_start_second']:.3f} | "
        f"{r['clip_end_second']:.3f} | {r['clip_duration_seconds']:.3f} |"
        for r in cuts['selected_clips'])
    point_table = '\n'.join(
        f"| {p['set']} | {p['point_number']} | "
        f"{p['six_geometric_candidate_frames']}/{p['sampled_frames']} | "
        f"{p['longest_consecutive_exact_six_same_raw_ids']['frames']} | "
        f"{next(r['frames_with_all_six_anchor_ids'] for r in roster['rows'] if r['set'] == p['set'] and r['point_number'] == p['point_number'])} | "
        f"{next(r['sampled_frames_in_run'] for r in windows['rows'] if r['set'] == p['set'] and r['point_number'] == p['point_number'])} | "
        f"{next(r['source_second'] for r in phase['rows'] if r['set'] == p['set'] and r['point_number'] == p['point_number']):.1f} | "
        f"{next(r['local_phase_status'] for r in phase['rows'] if r['set'] == p['set'] and r['point_number'] == p['point_number'])} |"
        for p in continuity['points'])
    metric_table = '\n'.join(
        f"| {r['set']} | {r['point_number']} | {'win' if r['near_team_won'] else 'loss'} | "
        f"{r['provisional_snapshot_metrics']['mean_pairwise_spacing_m']:.3f} | "
        f"{r['provisional_snapshot_metrics']['convex_hull_area_m2']:.3f} | "
        f"{r['provisional_snapshot_metrics']['centroid_dispersion_m']:.3f} |"
        for r in result['rows'])
    coverage_by_key = {(r['set'], r['point_number']): r for r in coarse_coverage['points']}
    availability_table = '\n'.join(
        f"| {set_number} | {side} | "
        + ', '.join(str(r['point_number']) for r in sample['selected_events']
                    if r['set'] == set_number and r['winner_scoreboard_side'] == side) + ' | '
        + str(sum(coverage_by_key[r['set'], r['point_number']]['within_coarse_bracket_candidate_frames'] > 0
                  for r in sample['selected_events']
                  if r['set'] == set_number and r['winner_scoreboard_side'] == side)) + '/3 |'
        for set_number in (1, 2, 3) for side in ('left', 'right'))
    groups = '\n'.join(
        f"| {g['set']} | {'win' if g['near_team_won'] else 'loss'} | {g['snapshots']} | "
        + ' | '.join('—' if g['median_of_provisional_snapshots'][name] is None else
                     f"{g['median_of_provisional_snapshots'][name]:.3f}"
                     for name in ('mean_pairwise_spacing_m', 'convex_hull_area_m2',
                                  'centroid_dispersion_m')) + ' |'
        for g in result['groups'])
    report = f'''# UCLA–Concordia dense tracking and metric readiness

This is the new primary-source feasibility result for the [18-point score-only frozen sample](../data/matches/yt_u5HnY2aNW14/screening/rally_sample_score_only.json). The full local video is SHA-256 `{tracks['source_sha256']}`. The earlier ProVolley–UTS outputs remain a separate development dataset.

## Edited rally clip boundaries

The recording already has hard edits between points. The [cut scanner](../scripts/scan_u5_rally_cuts.py) found **{cuts['summary']['detected_cuts']} cuts**: exactly **{cuts['summary']['point_change_cuts']}** align one-to-one with all visible +1 scoreboard changes and the other **{cuts['summary']['set_reset_cuts']}** align with set resets. On [source before/after sheets](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_boundary_review/), a [single-reviewer check](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_boundary_source_qc.json) confirms the edit bounds for all **18** frozen point clips. Every previously sampled dense tracking frame falls within its corresponding clip. The [full clip register](../data/matches/yt_u5HnY2aNW14/screening/rally_cut_clip_register.json) supplies exact source-frame bounds for all 122 visible points.

| Set | Point | Clip start (s, inclusive) | Clip end (s, exclusive) | Duration (s) |
| ---: | ---: | ---: | ---: | ---: |
{clip_table}

These are edited **clip** boundaries, not serve-contact or dead-ball frames. The first and last portions of a clip may contain formation setup or celebration. The clip bounds should constrain tracking and review; only source-confirmed live frames should enter court metrics.

## Cut-bounded phase contamination check

The [anonymous six-box screen](../data/matches/yt_u5HnY2aNW14/screening/cut_bounded_provisional_rally_metrics.json) found **{core['summary']['provisional_candidate_frames']}** geometrically plausible candidate frames in **{core['summary']['points_with_provisional_core_median']}** points, all within the edited clips. Source-image [review sheets](../data/matches/yt_u5HnY2aNW14/screening/provisional_core_review/) exposed **{core_phase_audit['confirmed_non_live_candidate_frames']} confirmed non-live candidates** in **{core_phase_audit['distinct_affected_points']} points**: set-two point 28 includes a pre-serve frame and a post-point frame; set-two point 26 and set-three point 34 include post-point frames. The [counterexample register](../data/matches/yt_u5HnY2aNW14/screening/provisional_core_phase_counterexamples.json) records exact source frames and sheet hashes. This review covered only the illustrated examples, so the other candidate frames have not been cleared. The screen's per-point and winner-stratified medians are **quarantined** and must not be interpreted as rally metrics or outcome evidence.

The [18-clip phase review pack](../data/matches/yt_u5HnY2aNW14/screening/frozen_clip_phase_review/) now provides **{sum(len(c['sampled_source_frames']) for c in phase_review_index['clips'])} source navigation frames** at one-second spacing, including the exact first and last source frames of each edited clip. This makes the pre-serve and post-point portions visible for interval review. One-second stills are navigation evidence; serve contact and dead ball still need closer source-frame or video review before an interval is certified.

A [single-reviewer phase bracket register](../data/matches/yt_u5HnY2aNW14/screening/coarse_phase_brackets.json) records pre-play, active-looking and post-play source marks for all **18** clips. The two shortest points use existing 5 Hz [focus sequences](../data/matches/yt_u5HnY2aNW14/screening/focus_phase_sequence/) to locate their brief exchange; both previously selected six-box navigation frames occur after the point. These marks are **coarse navigation brackets**, not exact serve/dead-ball decisions or continuous live-frame review. The [availability check](../data/matches/yt_u5HnY2aNW14/screening/coarse_phase_candidate_coverage.json) retains **{coarse_coverage['summary']['within_coarse_bracket_candidate_frames']}/{coarse_coverage['summary']['clip_candidate_frames']}** geometric candidates across **{coarse_coverage['summary']['points_with_bracketed_candidates']}/18** points. It excludes all four documented non-live counterexamples. Within the narrow 5 Hz spans of the two short points, the existing dense screen has **{coarse_coverage['summary']['short_clip_dense_exact_six_frames']}** frames with exactly six geometric near-side candidates. None of these retained candidates is a validated metric frame; frame-by-frame phase, team membership and ground positions remain open.

For one bracketed candidate per available point, the [unboxed source and detector overlay sheets](../data/matches/yt_u5HnY2aNW14/screening/bracketed_candidate_qc/) and [shoe-level crops](../data/matches/yt_u5HnY2aNW14/screening/selected_floor_qc/) were visually compared. The [corrected single-reviewer local QC](../data/matches/yt_u5HnY2aNW14/screening/bracketed_candidate_source_qc.json) records **{bracketed_source_qc['summary']['six_distinct_near_side_teammates_visible']}/{bracketed_source_qc['summary']['reviewed_local_frames']}** selected instants with six correct near-side teammates. The original set-one point 37 frame 10722 included far-side white raw box 87; it was rejected after a [22-frame source review](../data/matches/yt_u5HnY2aNW14/screening/s1p37_replacement_review/) and replaced by live frame 10488, showing five blue UCLA players and white UCLA libero #28. This is a local membership check, not an independent reference or whole-rally identity trace. It does not validate box-bottom court positions or promote the 126 candidate frames to final results.

A [source-bound short identity audit](../data/matches/yt_u5HnY2aNW14/screening/s1p37_short_identity_run.json) now follows UCLA #1, #7, #12, #19, #21 and libero #28 through ten consecutive 5 Hz samples in set-one point 37 (1.8 s between first and last), with a largest same-ID box-bottom step of **{s1p37_identity_run['maximum_consecutive_box_bottom_displacement_m']:.3f} m**. This confirms a short local six-player identity run; it does not validate floor-contact coordinates or the rest of that rally.

Across all 18 conservative live interiors, the [run availability audit](../data/matches/yt_u5HnY2aNW14/screening/interior_identity_run_availability.json) finds at least five consecutive six-ID samples in **{interior_runs['summary']['points_with_at_least_five_samples']}/18** points. Only the set-one point-37 short run has been source-checked for named jersey continuity; the other runs are detector proposals. None yet has validated grounded positions throughout.

All seven longer six-ID runs in the **original pass** are near-team losses ({interior_runs['summary']['long_run_near_team_wins']} wins, {interior_runs['summary']['long_run_near_team_losses']} losses). That pass alone cannot support the contract's winner comparison. The separate higher-resolution winning-point pass is evaluated below.

The [full 5 Hz source sheets](../data/matches/yt_u5HnY2aNW14/screening/all_interior_run_frames/) were checked for those seven runs. The [run source audit](../data/matches/yt_u5HnY2aNW14/screening/interior_run_source_qc.json) finds six correct near-side teammates at all **{interior_run_anchor_qc['summary']['sampled_frames_source_reviewed']}** displayed instants across **7/7** candidate runs. The frames between 5 Hz samples remain unobserved, named jersey continuity is certified only for set-one point 37, and no run has validated grounded coordinates.

The [winning-point short-run source review](../data/matches/yt_u5HnY2aNW14/screening/winning_short_run_source_qc.json) finds six correct near-side teammates in **{winning_short_source_qc['summary']['correct_win_candidate_frames_source_reviewed']}** sampled instants across **{winning_short_source_qc['summary']['wins_with_correct_six_candidate_run']}/9** near-team wins. Three wins have no same-six candidate run in the conservative interior. The one-frame run at set-three point 33 is rejected: raw box 40 follows a far-side white player while a near-side blue player is missing. The separate selected frame 35844 for that point remains a locally correct six-box snapshot, but it does not repair this run. These short and unequal windows cannot be treated as a balanced rally-level comparison.

The [full-image source stills](../data/matches/yt_u5HnY2aNW14/screening/zero_run_source_review/) for those three detector-zero wins show all six near-side teammates in each point. The [source visibility audit](../data/matches/yt_u5HnY2aNW14/screening/zero_run_source_qc.json) covers **{zero_run_source_qc['summary']['source_stills_reviewed']}** stills. Set-one point 18 has a player near the right sideline; the servers in set-two point 14 and set-three point 23 are airborne in early stills. These are recoverable detector gaps, but no continuous six-player track or grounded position is established for them. Counting visible players as measured court coordinates would overstate the evidence.

A [higher-resolution, lower-threshold detector pass](../data/matches/yt_u5HnY2aNW14/screening/zero_run_high_res_source_qc.json) recovers one locally correct six-box instant in each of set-one point 18 and set-two point 14. It leaves set-three point 23 unresolved because near-net overlap creates duplicate and merged boxes. Across tested detector settings, **17/18** frozen points now have at least one locally correct six-box instant. This is single-frame availability, not a six-player trajectory or validated ground measurement.

A separate [higher-resolution winning-point tracking screen](../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_screen.json) finds a 13-sample exact-six-ID run in set-three point 13. The [all-frame source check](../data/matches/yt_u5HnY2aNW14/screening/highres_winning_run_source_qc.json) identifies the same six UCLA teammates in all **{len(highres_winning_run_qc['source_frames'])}** displayed frames. Its first five samples span **{highres_winning_run_qc['active_looking_span_s']:.1f} s** of active-looking play; later samples may include point-end movement. Across tested settings, eight points have at least five six-ID samples (one near-team win, seven losses). No grounded floor positions or exact fixed analysis interval is certified for this new run.

The [joined visibility ledger](../data/matches/yt_u5HnY2aNW14/screening/source_visibility_ledger.json) accounts for **all 18 frozen points in the original pass**: 15 have one locally correct six-box instant and the other three show six teammates in source-only stills. The higher-resolution recovery above updates local box availability to 17/18. Both nine-point outcome groups have visible players. The missing final results stem from short or interrupted identity runs, unverified ground positions and uncertain exact intervals. The strict metric-frame count remains **zero**.

The [held-out shoe-reference audit](../data/matches/yt_u5HnY2aNW14/screening/heldout_box_floor_error.json) adds **{heldout_floor['summary']['reviewed_clear_grounded_shoe_pairs']}** clear grounded shoe-pair midpoints on four source frames across three sets, separate from the earlier nine reference boxes. Three unclear pairs were excluded. The median box-bottom discrepancy is **{heldout_floor['summary']['median_box_to_shoe_distance_m']:.3f} m**, with a maximum of **{heldout_floor['summary']['maximum_box_to_shoe_distance_m']:.3f} m**. These are approximate single-reviewer readings with about ±8 px visual uncertainty; clear shoe pairs underrepresent jumps and occlusions. The larger maximum shows that the earlier nine-box sample did not bound this proxy's error.

The [selected-frame proxy sensitivity audit](../data/matches/yt_u5HnY2aNW14/screening/selected_proxy_sensitivity.json) applies the three formulas to the **15** locally correct single-frame six-box snapshots (six near-team wins, nine losses). A deterministic perturbation probe moves each box-bottom court point by at most **{selected_proxy_sensitivity['summary']['perturbation_radius_m']:.3f} m**, the largest discrepancy in the combined 30-box clear-shoe reference. Across snapshots, the median width between the 5th and 95th percentile perturbation values is **{selected_proxy_sensitivity['summary']['median_perturbation_p05_p95_width_mean_pairwise_spacing_m']:.3f} m** for spacing, **{selected_proxy_sensitivity['summary']['median_perturbation_p05_p95_width_convex_hull_area_m2']:.3f} m²** for hull area and **{selected_proxy_sensitivity['summary']['median_perturbation_p05_p95_width_centroid_dispersion_m']:.3f} m** for dispersion. This is a method-sensitivity demonstration, not a statistical confidence interval or a validated error bound. The snapshots were selected by box availability, three wins lack a locally correct six-box snapshot, and no full analysis window has passed ground and identity validation. The illustrative winner medians in the JSON must not be read as an outcome association.

The [source-image court registration audit](../data/matches/yt_u5HnY2aNW14/screening/selected_camera_registration.json) compares static floor features from the staged calibration excerpt with **{camera_registration['summary']['reviewed_selected_frames']}** source frames covering **{camera_registration['summary']['frozen_points_covered']}/18** frozen points. All **{camera_registration['summary']['frames_registered']}** register, and the fitted displacement at six calibration/held-out landmarks is at most **{camera_registration['summary']['maximum_static_landmark_shift_px']:.3f} px**. This supports reusing the fixed image coordinate system across those reviewed instants. It does not independently validate the four manually placed court corners, the held-out attack-line mark, or any player-floor anchor. Those distinct accuracy gates remain open.

The [5 Hz transition sheets](../data/matches/yt_u5HnY2aNW14/screening/event_transition_review/) cover serve and point-ending windows for all 18 frozen points (36 sheets). The [source-bound transition register](../data/matches/yt_u5HnY2aNW14/screening/event_transition_source_qc.json) records a conservative active-looking interior for each point. The server's action is in view for **{event_transition_qc['summary']['points_with_server_action_in_view']}/18** points; exact contact is not frame-certified even there. Other serve contacts are outside the image or visually uncertain. These interiors exclude ambiguous starts and ends; they are not exact serve/dead-ball labels and do not pass the final boundary gate.

Geometric six-box candidate availability remains present in both frozen winner groups in every set, but coverage is uneven. The table is a review queue, not an outcome comparison. Winner side is the scoreboard side, and these counts are not validated metric frames.

| Set | Winner scoreboard side | Frozen points | Points with at least one bracketed six-box candidate |
| ---: | --- | --- | ---: |
{availability_table}

## Reproducible screening

The [dense tracker](../scripts/screen_u5_dense_live_tracks.py) sampled the 18 source-reviewed coarse live cores at 5 Hz. YOLOv8n proposed people; ByteTrack supplied point-local raw IDs. A staged 9×9 m homography gated box bottoms, and the floor centreline under the net separated geometric near-side candidates from boundary cases. The [dense screen](../data/matches/yt_u5HnY2aNW14/screening/dense_live_track_screen.json) has **{continuity['summary']['sampled_frames']} sampled frames**, of which **{continuity['summary']['six_geometric_candidate_frames']}** have six or more geometric candidates. Net-boundary review is needed in **{sum(p['frames_with_any_net_boundary_review'] for p in tracks['points'])}** dense frames. On the earlier one-frame-per-second screen, [source review](../data/matches/yt_u5HnY2aNW14/screening/net_boundary_adjudication.json) classified **{boundary['summary']['visually_far_boxes']} far-side** and **{boundary['summary']['visually_near_boxes']} near-side** boundary boxes; a hard line alone would lose real blockers.

The [continuity audit](../data/matches/yt_u5HnY2aNW14/screening/dense_live_continuity_audit.json) finds a same-six-raw-ID run of at least five sampled frames in **{continuity['summary']['points_with_at_least_one_second_same_six_raw_ids']}/18** points. The [selected-frame roster diagnostic](../data/matches/yt_u5HnY2aNW14/screening/seeded_roster_coverage.json) finds those six selected raw IDs together in **{roster['summary']['frames_with_all_six_anchor_ids']}/{roster['summary']['sampled_frames']}** sampled frames. Those raw IDs are not independently established jersey identities. Missing boxes remain missing; no stationary hold has been counted as measured position.

The [anchor-run audit](../data/matches/yt_u5HnY2aNW14/screening/anchor_live_window_availability.json) looks for an uninterrupted six-ID run containing each locally live selected frame. **{windows['summary']['live_anchor_runs_at_least_five_frames']}/{windows['summary']['locally_live_anchors']}** local live anchors have at least five adjacent 5 Hz samples with the same six raw IDs, while **{windows['summary']['live_anchor_runs_one_frame_only']}** have only the anchor sample. This is availability around a reviewed instant; the other samples and identities have not been source-validated.

| Set | Point | Six geometric candidate frames | Longest same-six raw-ID run (5 Hz frames) | All selected raw IDs present | Anchor run frames | Selected time (s) | Selected-frame phase |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{point_table}

The [source-image and motion review](../data/matches/yt_u5HnY2aNW14/screening/phase_six_candidate_review/) checked one six-box navigation frame per point. Seven [5 Hz focus sequences](../data/matches/yt_u5HnY2aNW14/screening/focus_phase_sequence/) resolved the three formerly uncertain instants and exposed a second after-point candidate at set-two point 14. The [phase register](../data/matches/yt_u5HnY2aNW14/screening/selected_phase_source_qc.json) marks **{phase['summary']['visible_live_play']} locally visible live**, **{phase['summary']['uncertain_phase']} uncertain** and **{phase['summary']['after_point']} after the point**. Set-three point 23's six-box frame is also after its short serve. Neither after-point frame can become a rally metric frame. These local decisions do not give exact serve-contact or dead-ball boundaries.

## Box-bottom court-position diagnostic

On [unboxed source crops](../data/matches/yt_u5HnY2aNW14/screening/floor_reference_crops/), one reviewer estimated the midpoint of two visible grounded shoes for **{floor['summary']['reviewed_grounded_boxes']}** clear player boxes from two frames, including both near-side team colours. The [audit](../data/matches/yt_u5HnY2aNW14/screening/floor_proxy_reference_audit.json) finds median projected box-bottom disagreement **{floor['summary']['median_box_bottom_to_shoe_midpoint_m']:.3f} m** and maximum **{floor['summary']['maximum_box_bottom_to_shoe_midpoint_m']:.3f} m**. Pixel marks have roughly ±8 px reading uncertainty. Net jumps, clipping and occlusion were excluded from this small check. It is a local proxy diagnostic, not independent calibration validation or a declared acceptable-error threshold.

## Three metric formulas executed, with strict status retained

The [calculator](../scripts/compute_honours_team_metrics.py) implements mean pairwise spacing, convex-hull formation area and centroid dispersion. It now accepts either frozen match sample through `--sample` while still requiring reviewed boundaries, six named near-side players, validated calibration and reviewed ground positions. No U5 point currently passes that final gate.

As a method demonstration, [provisional snapshot values](../data/matches/yt_u5HnY2aNW14/screening/provisional_live_snapshot_metrics.json) were calculated from the six box-bottom projections in **{result['summary']['source_screened_live_snapshots_with_six_nominal_in_court_boxes']}** locally screened live frames. One further locally live frame was excluded because a candidate projected outside the strict 9 m court. Each value is one availability-selected frame, not a rally median or phase-matched outcome observation.

| Set | Point | Near team result | Pairwise spacing (m) | Hull area (m²) | Centroid dispersion (m) |
| ---: | ---: | --- | ---: | ---: | ---: |
{metric_table}

Descriptive medians of these **provisional snapshots only**:

| Set | Near team result | Snapshots | Spacing (m) | Hull area (m²) | Dispersion (m) |
| ---: | --- | ---: | ---: | ---: | ---: |
{groups}

The values cannot establish that spacing or coverage predicts winning. The navigation frame was selected using box availability, selected phases differ, ground positions are proxies, and each set-by-result group has only two or three snapshots. No significance test is warranted. Rotation and transition movement were not measured by these three static formulas.

## Contract-level completion decision

**Validated six-player metric frames: 0. Validated rally summaries: 0. Outcome comparison from validated court metrics: unavailable.** The scoreboard result and method prototype are complete, but the signed spatial-outcome study is not yet empirically complete. The remaining source work is exact live interval review, six jersey identities through those intervals, player-ground proxy validation across net actions, and enough eligible frames in both winner groups. A reduced feasibility-only thesis would require an explicit academic scope decision; this report does not assume one.

## Focused source review queue

The table's selected times are direct navigation points in the local source video. Set-one point 18 is locally live but one of its six projected box bottoms falls outside the strict 9 m metric court. Set-two point 14 and set-three point 23 have after-point selected frames; both need a different live anchor or an explicit availability exclusion. For every retained point, establish the serve contact and dead ball from the video, confirm six near-side jersey identities across that interval, then review grounded box bottoms at the frames used for metrics. The existing raw IDs and provisional numbers are navigation aids; they do not substitute for those checks.

## Reproduce

From the project root, run these in order with `.\\.venv\\Scripts\\python.exe`:

```text
scripts/scan_u5_rally_cuts.py
scripts/render_u5_cut_boundary_pairs.py
scripts/adjudicate_u5_cut_boundaries.py
scripts/screen_u5_dense_live_tracks.py
scripts/audit_u5_dense_continuity.py
scripts/render_u5_dense_continuity_review.py
scripts/screen_u5_six_candidate_phase.py
scripts/render_u5_phase_six_candidates.py
scripts/render_u5_phase_context.py
scripts/render_u5_uncertain_phase_context.py
scripts/render_u5_focus_phase_sequence.py
scripts/adjudicate_u5_selected_phase.py
scripts/audit_u5_seeded_roster_coverage.py
scripts/audit_u5_anchor_live_windows.py
scripts/render_u5_floor_reference_crops.py
scripts/audit_u5_floor_proxy_reference.py
scripts/build_u5_provisional_snapshot_metrics.py
scripts/build_u5_cut_bounded_provisional_rally_metrics.py
scripts/render_u5_provisional_core_review.py
scripts/audit_u5_provisional_core_phase.py
scripts/render_u5_frozen_clip_phase_review.py
scripts/adjudicate_u5_coarse_phase_brackets.py
scripts/render_u5_event_transition_sheets.py
scripts/audit_u5_event_transition_windows.py
scripts/screen_u5_coarse_phase_coverage.py
scripts/render_u5_bracketed_candidate_qc.py
scripts/adjudicate_u5_bracketed_candidate_qc.py
scripts/render_u5_selected_floor_qc.py
scripts/render_u5_s1p37_replacement_candidates.py
scripts/audit_u5_s1p37_identity_run.py
scripts/audit_u5_interior_identity_runs.py
scripts/render_u5_interior_run_review.py
scripts/render_u5_all_interior_run_frames.py
scripts/adjudicate_u5_interior_run_anchors.py
scripts/render_u5_winning_short_runs.py
scripts/adjudicate_u5_winning_short_runs.py
scripts/render_u5_zero_run_source.py
scripts/adjudicate_u5_zero_run_source.py
scripts/recover_u5_zero_run_detections.py
scripts/adjudicate_u5_zero_run_high_res.py
scripts/screen_u5_highres_winning_runs.py
scripts/render_u5_highres_winning_run_review.py
scripts/adjudicate_u5_highres_winning_run.py
scripts/build_u5_source_visibility_ledger.py
scripts/audit_u5_selected_proxy_sensitivity.py
scripts/render_u5_heldout_shoe_reference.py
scripts/audit_u5_heldout_box_floor_error.py
scripts/audit_u5_selected_camera_registration.py
scripts/build_u5_dense_results_report.py
```

The phase and shoe-reference scripts include explicit single-reviewer decisions. Re-running them reproduces the saved decisions; it does not create independent human validation.
'''
    OUT.write_text(report, encoding='utf-8')
    MANIFEST.write_text(json.dumps({
        'status': 'dense_results_report_source_hash_manifest',
        'report_sha256': sha(OUT),
        'inputs_sha256': {key: sha(path) for key, path in FILES.items()},
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
