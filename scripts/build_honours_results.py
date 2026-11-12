"""Build a local honours results handoff from source-bound evidence files."""
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTO = Path('data/processed/fqe_auto_score_timeline.json')
AUDIT = Path('data/processed/fqe_auto_score_readings.json')
TEMPLATES = Path('data/processed/fqe_auto_score_templates.npz')
R1 = Path('data/processed/fqe_r1_boundary_recheck/r1_point_summary.json')
D79 = Path('data/processed/d79_new_source/named_near_reviewed_evaluation.json')
D79_REVIEW = Path('data/processed/d79_new_source/reviewed_near_evaluation.json')
MAIN_SOURCE = Path('data/matches/yt_FqE5pTJqx8g/source_record.json')
D79_SOURCE = Path('data/matches/yt_D79JrsJsFgs/source_record.json')
OUTPUT_JSON = ROOT / 'data/processed/honours_results_handoff.json'
OUTPUT_MD = ROOT / 'DELIVERABLES/HONOURS_RESULTS_HANDOFF.md'
OUTPUT_FIGURE = ROOT / 'data/processed/honours_score_progression.png'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def draw_score_progression(points):
    cache = ROOT / 'data/processed/.matplotlib_cache'
    cache.mkdir(exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7), sharey=True)
    for set_number, ax in enumerate(axes, 1):
        subset = [row for row in points if row['set'] == set_number]
        x = [0] + [row['point_number'] for row in subset]
        lead = [0] + [int(row['score_after'].split('-')[0]) - int(row['score_after'].split('-')[1])
                      for row in subset]
        ax.step(x, lead, where='post', color='#176d91', linewidth=2)
        ax.axhline(0, color='#7d8790', linewidth=.8)
        for row in subset:
            if 'inferred' in row['evidence'] or row['evidence'] == 'first_visible_score_only':
                idx = row['point_number']
                ax.scatter([idx], [lead[idx]], facecolors='white', edgecolors='#b74e38',
                           linewidths=1.5, s=46, zorder=3)
        ax.set(title=f'Set {set_number}  ·  {subset[-1]["score_after"]}',
               xlabel='Scored point', xlim=(0, len(subset)), ylim=(-2, 17))
        ax.grid(axis='y', alpha=.2)
    axes[0].set_ylabel('ProVolley lead (points)')
    fig.suptitle('Automatic broadcast-score progression', fontsize=13)
    fig.text(.5, .01, 'Open circles: opening or inferred set-one point', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .045, 1, .92))
    fig.savefig(OUTPUT_FIGURE, dpi=180)
    plt.close(fig)


def main():
    auto, audit, r1, d79, d79_review = [read(path) for path in (AUTO, AUDIT, R1, D79, D79_REVIEW)]
    main_source, d79_source = read(MAIN_SOURCE), read(D79_SOURCE)
    assert auto['match_id'] == audit['match_id'] == r1['match_id'] == main_source['match_id']
    assert auto['source_sha256'] == audit['source_sha256'] == r1['source_sha256'] == main_source['sha256']
    assert d79_source['match_id'] == 'yt_D79JrsJsFgs'
    assert d79_review['source_sha256'] == d79_source['sha256']
    assert d79_review['labels_sha256'] == d79['labels_sha256']
    assert len(auto['points']) == auto['point_count'] == 123
    assert [row['point_count'] for row in auto['set_summaries']] == [40, 41, 42]
    assert sum(row['provolley_points'] for row in auto['set_summaries']) == 75
    assert sum(row['uts_points'] for row in auto['set_summaries']) == 48
    assert audit['reviewed_state_audit']['agreement_count'] == audit['reviewed_state_audit']['count'] == 721
    assert audit['between_sample_audit']['agreement_count'] == audit['between_sample_audit']['count'] == 121
    assert d79['visible_target_boxes'] == d79['matched_boxes'] == d79['correct_identity_matches'] == 232
    assert r1['summary']['total_player_box_slots'] == 2484
    draw_score_progression(auto['points'])
    players = [{'player_id': player['player_id'], 'name': player['display_name'],
                'approximate_distance_m': player['approximate_distance_m'],
                'scope_frames': player['distance_frames_inclusive']}
               for player in r1['players']]
    results = {
        'status': 'local_honours_results_handoff_not_public_release',
        'primary_match': {
            'match_id': auto['match_id'], 'source_sha256': auto['source_sha256'],
            'score_method': 'fixed_layout_automatic_template_reader_after_one_time_manual_calibration',
            'set_scores': [row['final_score'] for row in auto['set_summaries']],
            'scored_points': 123, 'provolley_points': 75, 'uts_points': 48,
            'provolley_point_share': round(75 / 123, 4),
            'reviewed_sample_agreement': [721, 721],
            'between_sample_agreement': [121, 121],
            'opening_point_status': 'first_visible_1_0_score',
            'set_one_winning_point_status': 'inferred_from_set_transition',
            'rally_boundaries_required_for_score_claim': False,
        },
        'r1_primary_match_case_study': {
            'frames_inclusive': r1['frames_inclusive'],
            'valid_named_box_slots': r1['summary']['valid_player_box_slots'],
            'total_named_box_slots': r1['summary']['total_player_box_slots'],
            'all_six_usable_box_frames': r1['summary']['all_six_usable_box_frames'],
            'players': players,
            'distance_status': 'approximate_method_estimates_on_stated_frame_ranges_not_validated_physical_travel',
            'point_end_status': 'provisional',
        },
        'd79_separate_validation_case': {
            'match_id': d79_source['match_id'], 'source_sha256': d79_source['sha256'],
            'frames_inclusive': d79['frame_range_inclusive'],
            'checked_visible_boxes': d79['visible_target_boxes'],
            'matched_named_boxes': d79['matched_boxes'],
            'correct_named_identity_matches': d79['correct_identity_matches'],
            'scope': 'source_seeded_model_assisted_in_sample_regression_check',
            'not_primary_match_statistics': True,
        },
        'release_state': {
            'primary_rights': main_source['rights_status'],
            'primary_privacy': main_source['privacy_review_status'],
            'd79_rights': d79_source['rights_status'],
            'd79_privacy': d79_source['privacy_review_status'],
            'public_release_ready': False,
        },
        'inputs_sha256': {str(path): digest(path) for path in
                          (AUTO, AUDIT, TEMPLATES, R1, D79, D79_REVIEW, MAIN_SOURCE, D79_SOURCE)},
    }
    OUTPUT_JSON.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    summaries = auto['set_summaries']
    table = '\n'.join(f"| {row['set']} | {row['final_score']} | {row['point_count']} | "
                      f"{row['provolley_points']} | {row['uts_points']} | "
                      f"{row['longest_provolley_point_run']} | {row['longest_uts_point_run']} |"
                      for row in summaries)
    player_table = '\n'.join(
        f"| {player['name']} | "
        + (f"{player['approximate_distance_m']:.2f} m | {player['scope_frames'][0]}–{player['scope_frames'][1]} |"
           if player['approximate_distance_m'] is not None else 'Withheld | No supported complete path |')
        for player in players)
    markdown = f"""# Honours results handoff: ProVolley vs UTS

This local handoff is generated by [build_honours_results.py](../scripts/build_honours_results.py) from the hashed [machine-readable record](../data/processed/honours_results_handoff.json). It separates primary-match scores, a bounded primary-match player example, and validation on a different video.

## Primary-match score results

The [automatic score reader](AUTOMATIC_SCORE_READER.md) produced the [point register](../data/processed/fqe_auto_score_timeline.csv) after one-time calibration to this broadcast graphic. The final set scores were **25–15, 25–16, 25–17** for ProVolley. ProVolley won **75/123 points ({75 / 123:.1%})**; UTS won **48/123 ({48 / 123:.1%})**.

| Set | ProVolley–UTS | Points | ProVolley points | UTS points | Longest ProVolley run | Longest UTS run |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

![ProVolley point lead across each set, derived from automatic score readings](../data/processed/honours_score_progression.png)

The reader agrees with **721/721** previously reviewed sampled score states and **121/121** additional frames after known score flips on this same video. These are same-video checks with reviewed calibration templates, not a cross-broadcast accuracy estimate. The opening point is based on the first visible 1–0 score; set one's 25–15 winner is inferred from the set transition because the final score is not shown. One temporary 19–11 display is treated as a broadcast correction, not another point. Score changes occur after play and are not rally-boundary labels. Manual review of every rally is unnecessary for these score statistics.

## Bounded primary-match player example

The [R1 point summary](R1_POINT_SUMMARY.md) covers provisional frames **21050–21463**. It has **2,025/2,484** usable named-box slots, with all six usable on **108/414** frames. The distances below are approximate method estimates on the specified frame ranges; they are not validated physical travel or full-match statistics.

| Player | Approximate path estimate | Frames |
| --- | ---: | --- |
{player_table}

The [method detail](R1_D79_POLICY_TRANSFER.md) records endpoint chords across hidden spans, held positions and sensitivity to box geometry. #11 and #13 have no supportable distance estimate, so no measured six-player total is reported. The optional 65.90 m six-player figure is an assumption-based scenario with a 62.01–82.85 m smoothing range, not a result to present as measured travel.

## Separate validation example

The [D79 near-side evaluation](D79_REVIEWED_NEAR_EVALUATION.md) is from a **different match**. Its source-seeded named-box output matched **232/232** checked visible near-team boxes and identities on frames 240–289. These same frames informed a box-only fix, and the reviewer saw model suggestions, so this is an in-sample regression check rather than blind autonomous tracker accuracy. Far-side identities were outside the chosen scope.

## Scope and release limits

The evidence supports automatic score progression on this specific fixed graphic and bounded, qualified player examples. It does not support exact full-match rally durations, whole-match player distance, cross-broadcast score-reader accuracy or general tracker accuracy. Source-use and privacy decisions for the primary and D79 videos remain pending in their source records. Keep this handoff local until the project owner and institution resolve what may be included in assessment or shared publicly.

## Rebuild

From the project root, run `.\\.venv\\Scripts\\python.exe scripts/build_honours_results.py` to regenerate this handoff and its score figure from the recorded inputs.
"""
    OUTPUT_MD.write_text(markdown, encoding='utf-8')
    print(f'Wrote {OUTPUT_MD} and {OUTPUT_JSON}')


if __name__ == '__main__':
    main()
