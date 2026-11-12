"""Probe fixed-box outcome contrasts with the observed non-anchor shoe discrepancy."""

import hashlib
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_u5_fixed_box_court_proxy import FIELDS, equal_cell_difference
from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
PILOT = BASE / 'fixed_box_court_proxy_pilot.json'
AUDIT = BASE / 'dynamic_shoe_reference_audit.json'
OUT = BASE / 'dynamic_error_sensitivity.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_DYNAMIC_ERROR_SENSITIVITY.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def simulate(rows, radius, draws=1000, seed=20261103):
    rng = random.Random(seed)
    contrasts = {field: [] for field in FIELDS}
    for _ in range(draws):
        perturbed = []
        for row in rows:
            samples = []
            for frame in row['frames']:
                positions = []
                for x, y in frame['court_proxy_m']:
                    angle = rng.uniform(0, 2 * math.pi)
                    distance = radius * math.sqrt(rng.random())
                    positions.append((x + distance * math.cos(angle),
                                      y + distance * math.sin(angle)))
                samples.append(metrics(positions))
            perturbed.append({**row, 'window_median': {
                field: statistics.median(sample[field] for sample in samples)
                for field in FIELDS}})
        for field in FIELDS:
            value, cells = equal_cell_difference(perturbed, field)
            assert cells == 3
            contrasts[field].append(value)
    return {field: {'minimum': round(min(values), 4),
                    'maximum': round(max(values), 4),
                    'fraction_positive': round(sum(value > 0 for value in values) / draws, 4)}
            for field, values in contrasts.items()}


def main():
    pilot = json.loads(PILOT.read_text(encoding='utf-8'))
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    assert audit['source_sha256'] == pilot['source_sha256']
    assert audit['input_sha256']['fixed_box_proxy'] == sha(PILOT)
    assert audit['summary']['single_reviewer_clear_grounded_pairs'] == 11
    assert audit['summary']['complete_six_player_dynamic_reference_frames'] == 0
    assert len(pilot['rows']) == 8
    radius = audit['summary']['maximum_court_position_error_m']
    assert radius > pilot['observed_clear_shoe_error_scenario']['radius_m']
    results = simulate(pilot['rows'], radius)
    out = {
        'status': 'exploratory_position_perturbation_scenario_not_confidence_interval',
        'source_sha256': pilot['source_sha256'],
        'input_sha256': {'fixed_box_proxy': sha(PILOT), 'dynamic_shoe_audit': sha(AUDIT)},
        'radius_m': radius, 'draws': 1000, 'seed': 20261103,
        'perturbation': 'independent uniform court-plane discs for each proxy position',
        'selection': 'eight availability-selected 0.8-second windows; three matched set-phase cells',
        'baseline': {field: pilot['baseline'][field]['equal_cell_win_minus_loss'] for field in FIELDS},
        'previous_static_radius_m': pilot['observed_clear_shoe_error_scenario']['radius_m'],
        'results': results,
        'limitations': ('The radius is the maximum of 11 selected, approximate single-reviewer clear-shoe '
                        'marks at one non-anchor frame per window. Five selected slots were unmarkable, '
                        'manual reading uncertainty is about ±12 source pixels per axis, and this '
                        '16-slot subset contains no full six-player frame. A separate selected '
                        'full-team frame check does not make this an empirical error distribution. '
                        'The disc perturbations are a scenario, '
                        'not an empirical error distribution, upper bound, confidence interval, or '
                        'confirmatory outcome test.')}
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    labels = {'mean_pairwise_spacing_m': 'Mean pairwise spacing (m)',
              'convex_hull_area_m2': 'Convex hull area (m²)',
              'centroid_dispersion_m': 'Centroid dispersion (m)'}
    lines = [
        '# Non-anchor error sensitivity for the fixed-box proxy', '',
        'The [manual non-anchor shoe audit](HONOURS_U5_DYNAMIC_SHOE_REFERENCE.md) found a '
        f'largest mapped proxy-to-shoe discrepancy of **{radius:.3f} m** among 11 clear '
        'pairs at +12 frames across eight points. The earlier static reference maximum was '
        f"{out['previous_static_radius_m']:.3f} m. This observed maximum is not a bound.", '',
        'Using that new radius, 1,000 seeded draws independently move each of the 240 '
        'fixed-box court proxies within a uniform disc. For each draw, the three spatial '
        'metrics are recomputed at all five instants, summarized by the window median, and '
        'compared as an equal-weight win-minus-loss difference across the three matched '
        'set-and-phase cells.', '',
        '| Metric | Original contrast | Scenario range | Fraction positive |',
        '| --- | ---: | ---: | ---: |']
    for field in FIELDS:
        row = results[field]
        lines.append(f"| {labels[field]} | {out['baseline'][field]:+.3f} | "
                     f"{row['minimum']:+.3f} to {row['maximum']:+.3f} | "
                     f"{row['fraction_positive']:.3f} |")
    lines += ['', 'The [machine-readable draws summary](../data/matches/yt_u5HnY2aNW14/'
              'screening/dynamic_error_sensitivity.json) is a sensitivity scenario, not a '
              'confidence interval, empirical error model or confirmatory significance test. '
              'The 11 marks were selected clear contacts, five selected slots were unmarkable, '
              'and this 16-slot subset has no complete six-player frame. A separate '
              '[one-frame team check](HONOURS_U5_DYNAMIC_FULL_TEAM_REFERENCE.md) '
              'reuses two marks and adds four. The manual '
              'midpoints have about ±12 source-pixel reading uncertainty per axis. A larger '
              'error could occur during occlusion, low posture or jumping. The window sample '
              'was also selected by tracker availability.', '',
              'Reproduce with `python scripts/analyze_u5_dynamic_error_sensitivity.py` '
              'after the fixed-box pilot and dynamic shoe-reference audit.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    print({field: results[field] for field in FIELDS})


if __name__ == '__main__':
    main()
