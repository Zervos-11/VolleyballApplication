"""Calculate a bounded R2 metric demonstration from unreviewed saved points.

This intentionally bypasses the strict final-input gate. Its output must never be
used as a validated rally or outcome observation.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from compute_honours_team_metrics import metrics


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
LABELS = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json'
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
SCREEN = ROOT / 'data/processed/honours_r2_candidate_source_review.json'
OUTPUT = ROOT / 'data/processed/honours_r2_provisional_metric_demo.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_R2_PROVISIONAL_METRICS.md'
FRAMES = (78050, 78100, 78400)
N_SCENARIOS = 2000
SEED = 20261102
PERTURBATION_RADIUS_M = .2
NAMES = ('mean_pairwise_spacing_m', 'convex_hull_area_m2', 'centroid_dispersion_m')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, labels, calibration, sample, screen = [read(p) for p in
                                                    (SOURCE, LABELS, CALIBRATION, SAMPLE, SCREEN)]
    if not (source['sha256'] == sample['source_sha256'] == screen['source_sha256']):
        raise ValueError('Source records do not match')
    selected = next(p for p in sample['selected_points']
                    if p['set'] == 2 and p['point_number'] == 2)
    transform = cv2.getPerspectiveTransform(np.asarray(calibration['points_px'], np.float32),
                                             np.asarray(calibration['points_court_m'], np.float32))
    rng = np.random.default_rng(SEED)
    rows = []
    for frame_number in FRAMES:
        saved = labels['frames'][str(frame_number)]
        if saved['review_status'] != 'unreviewed':
            raise ValueError(f'Expected historical unreviewed frame {frame_number}')
        players = saved['players']
        if len(players) != 6 or any(p['position_status'] != 'visible' or p['footpoint'] is None for p in players):
            raise ValueError(f'Frame {frame_number} is not a six-point candidate')
        positions = cv2.perspectiveTransform(
            np.asarray([[p['footpoint']] for p in players], np.float32), transform)[:, 0, :]
        if not np.all((positions >= 0) & (positions <= 9)):
            raise ValueError(f'Frame {frame_number} has a projected out-of-court point')
        nominal = metrics([tuple(map(float, p)) for p in positions])
        scenarios = {name: [] for name in NAMES}
        accepted = 0
        for _ in range(N_SCENARIOS):
            angles = rng.uniform(0, 2 * np.pi, 6)
            radii = PERTURBATION_RADIUS_M * np.sqrt(rng.uniform(0, 1, 6))
            offsets = np.column_stack((radii * np.cos(angles), radii * np.sin(angles)))
            trial = positions + offsets
            if not np.all((trial >= 0) & (trial <= 9)):
                continue
            accepted += 1
            measured = metrics([tuple(map(float, p)) for p in trial])
            for name in NAMES:
                scenarios[name].append(measured[name])
        rows.append({'frame': frame_number,
                     'saved_review_status': saved['review_status'],
                     'player_ids': [p['player_id'] for p in players],
                     'saved_projected_court_positions_m': [list(map(lambda x: round(float(x), 3), p))
                                                           for p in positions],
                     'nominal_candidate_metrics': {k: round(v, 3) for k, v in nominal.items()},
                     'hypothetical_0_2m_perturbation': {
                         'accepted_scenarios': accepted,
                         'quantiles_05_95': {name: [round(float(np.quantile(scenarios[name], q)), 3)
                                                   for q in (.05, .95)]
                                             for name in NAMES}}})
    result = {'status': 'unreviewed_candidate_metric_demonstration_not_final_outcome_data',
              'source_sha256': source['sha256'], 'saved_labels_sha256': sha(LABELS),
              'calibration_sha256': sha(CALIBRATION), 'frozen_sample_sha256': sha(SAMPLE),
              'source_screen_sha256': sha(SCREEN), 'set': 2, 'point_number': 2,
              'winner': selected['winner'], 'near_team': 'UTS',
              'saved_interval_frames': labels['end_frame_exclusive'] - labels['start_frame'],
              'candidate_frame_count': len(rows),
              'candidate_fraction_of_saved_interval': len(rows) / (labels['end_frame_exclusive'] - labels['start_frame']),
              'hypothetical_perturbation': {'radius_m': PERTURBATION_RADIUS_M,
                                           'draws_per_frame': N_SCENARIOS, 'seed': SEED,
                                           'distribution': 'Independent uniform disks centred on each saved projected point; outside-court draws discarded.',
                                           'interpretation': 'Sensitivity scenario, not measured annotation or calibration error.'},
              'frames': rows, 'use_for_final_outcome_comparison': False}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    lines = '\n'.join(
        f"| {r['frame']} | {r['nominal_candidate_metrics']['mean_pairwise_spacing_m']:.3f} | "
        f"{r['nominal_candidate_metrics']['convex_hull_area_m2']:.3f} | "
        f"{r['nominal_candidate_metrics']['centroid_dispersion_m']:.3f} | "
        f"{r['hypothetical_0_2m_perturbation']['accepted_scenarios']}/{N_SCENARIOS} |"
        for r in rows)
    REPORT.write_text(f'''# R2 provisional team-metric demonstration

The [machine-readable demonstration](../data/processed/honours_r2_provisional_metric_demo.json) applies the three prespecified formulas to saved, **unreviewed** six-point candidates on frames 78050, 78100 and 78400. The [source screen](HONOURS_R2_CANDIDATE_SOURCE_REVIEW.md) makes the boxes plausible, but it does not independently verify every shoe-floor click or approve the court transform for final metrics. ProVolley won this point; UTS is near side. These values are **not** a losing-team outcome observation.

| Frame | Pairwise spacing (m) | Hull area (m²) | Centroid dispersion (m) | In-court sensitivity draws |
| ---: | ---: | ---: | ---: | ---: |
{lines}

Only **{len(rows)}/{result['saved_interval_frames']} frames ({100 * result['candidate_fraction_of_saved_interval']:.2f}%)** of the saved point interval meet the nominal six-in-court geometry check. This fraction describes candidate availability, not validated tracking coverage. No rally median or win/loss comparison is published from it.

The JSON also gives 5th–95th percentile scenarios after independently perturbing each projected point within a **0.2 m radius** ({N_SCENARIOS} seeded draws per frame, excluding out-of-court draws). Those ranges are a hypothetical sensitivity check; they are not empirical error bars. The strict [final calculator](HONOURS_METRIC_INPUT.md) remains gated and has zero accepted R2 frames.

At frame 78100, {N_SCENARIOS - rows[1]['hypothetical_0_2m_perturbation']['accepted_scenarios']} of {N_SCENARIOS} perturbations put at least one player outside the strict court boundary. Its quoted quantiles are conditional on staying inside and should not be read as the full uncertainty range.
''', encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
