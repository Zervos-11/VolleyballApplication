"""Package the exact-frame R2 visual screen without promoting pilot labels."""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
LABELS = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json'
CALIBRATION = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/camera_r2_r5.json'
SHEETS = ROOT / 'data/processed/honours_r2_all_slots_source_sheets'
SPOTCHECK = ROOT / 'data/processed/honours_r2_calibration_spotcheck/spotcheck.json'
OUTPUT = ROOT / 'data/processed/honours_r2_candidate_source_review.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_R2_CANDIDATE_SOURCE_REVIEW.md'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_record(path):
    return {'file': str(path.relative_to(ROOT)), 'sha256': sha(path)}


def main():
    source, labels, spotcheck = read(SOURCE), read(LABELS), read(SPOTCHECK)
    if source['sha256'] != spotcheck['source_sha256'] or sha(CALIBRATION) != spotcheck['calibration_sha256']:
        raise ValueError('Calibration spotcheck does not match current source and transform')
    observations = {
        78050: 'All six saved boxes visually enclose near-side UTS players. Shoe-level markers are broadly plausible, including bent slot 42, but the individual clicks have not been independently measured.',
        78100: 'All six saved boxes visually enclose near-side UTS players. Slots 42 and 36 overlap in the image; slot 42 is the near-side #22 established by the dense identity review. The shoe-level clicks still need independent contact checks.',
        78400: 'The six saved boxes visually follow near-side UTS players. Several players are stepping or partly overlapping near the net, especially slot 42, so a visible shoe is not enough to certify the saved floor-contact point.'
    }
    frames = []
    for number, observation in observations.items():
        row = labels['frames'][str(number)]
        if len(row['players']) != 6 or any(p['footpoint'] is None for p in row['players']):
            raise ValueError(f'Expected six saved footpoint proposals on frame {number}')
        frames.append({'frame': number,
                       'saved_review_status': row['review_status'],
                       'six_saved_near_side_boxes_visual_screen': 'plausible_at_this_frame',
                       'floor_contact_status': 'source_screen_only_not_independently_clicked',
                       'observation': observation,
                       'full_overlay': file_record(SHEETS / f'candidate_{number}_full.jpg'),
                       'shoe_crops': file_record(SHEETS / f'candidate_{number}_foot_crops.jpg'),
                       'court_overlay': spotcheck['frames'][str(number)]})
    residuals = [row['net_depth_residual_m'] for row in spotcheck['heldout_net_line_samples']]
    result = {'status': 'single_analyst_source_screen_not_reviewed_metric_input',
              'source_sha256': source['sha256'],
              'saved_labels_sha256': sha(LABELS),
              'calibration_sha256': sha(CALIBRATION),
              'calibration_spotcheck': file_record(SPOTCHECK),
              'candidate_frames': frames,
              'calibration_observation': 'The staged baseline, attack line and sidelines visually follow the same source court markings on all three exact frames; these lines were used to fit the transform. The independent net-floor line gives the court-depth residual range below. This is a source screen, not player-floor accuracy validation.',
              'heldout_net_depth_residual_m_on_0_to_9_m_width': [min(residuals), max(residuals)],
              'use_for_final_metrics': False,
              'unresolved': ['Individual floor contact clicks and grounded states on all metric frames',
                             'Calibration error against independent player-floor or court landmarks',
                             'Dense six-player positions through a source-reviewed rally interval']}
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text(f'''# R2 exact-frame source and calibration screen

The [source-bound record](../data/processed/honours_r2_candidate_source_review.json) checks the three saved frames with six nominally in-court footpoints. It preserves the original `unreviewed` annotation file. The user's general confirmation of the starting setup is [recorded separately](../data/processed/honours_r2_user_confirmation.json).

| Frame | Source observation | Full overlay | Shoe crops | Court overlay |
| ---: | --- | --- | --- | --- |
''' + '\n'.join(
        f"| {r['frame']} | {r['observation']} | [image](../{r['full_overlay']['file']}) | [image](../{r['shoe_crops']['file']}) | [image](../{r['court_overlay']['file']}) |"
        for r in frames) + f'''

The fitted baseline, attack line and sidelines visually follow their source markings on these exact frames. The held-out net-floor line projects to **{min(residuals):+.3f} to {max(residuals):+.3f} m** of depth residual across court x=0-9 m. See the [calibration spotcheck](../data/processed/honours_r2_calibration_spotcheck/spotcheck.json). This checks one court line and does not establish shoe-floor coordinate accuracy or approve the transform for final metrics.

**Decision:** The six saved boxes look like the intended near-side team on these three frames. Their footpoints are still source-screened proposals, especially for players stepping or overlapping near the net. There are **zero newly validated metric frames**. The next data step is an explicit per-player floor-contact decision and independent landmark error check; uncertain shoes must remain unknown rather than inherited from box bottoms.
''', encoding='utf-8')
    print(f'Wrote {OUTPUT.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
