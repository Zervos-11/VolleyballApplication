"""Calculate an exploratory same-set three-snapshot image-box metric example."""
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

from compute_honours_team_metrics import hull_area


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
SCREEN = ROOT / 'data/processed/honours_missing_outcome_box_screen.json'
SAMPLE = ROOT / 'data/processed/honours_rally_sample.json'
OUT = ROOT / 'data/processed/honours_set3_image_proxy_demo.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_SET3_IMAGE_PROXY_DEMO.md'
SELECTIONS = [
    {'point_number': 5, 'frame': 155799, 'winner': 'ProVolley',
     'basis': 'saved_annotator_boxes_visual_screen'},
    {'point_number': 11, 'frame': 162695, 'winner': 'UTS',
     'basis': 'detector_boxes_visual_screen', 'detector_indices': [0, 1, 2, 3, 4, 6],
     'airborne_present': True},
    {'point_number': 37, 'frame': 204263, 'winner': 'UTS',
     'basis': 'detector_boxes_visual_screen', 'detector_indices': [0, 1, 2, 3, 5, 6]},
]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_metrics(boxes):
    if len(boxes) != 6:
        raise ValueError('Exactly six boxes required')
    points = [((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for b in boxes]
    pairs = [math.dist(a, b) for a, b in combinations(points, 2)]
    center = (sum(p[0] for p in points) / 6, sum(p[1] for p in points) / 6)
    return {'mean_pairwise_spacing_px': sum(pairs) / 15,
            'convex_hull_area_px2': hull_area(points),
            'centroid_dispersion_px': sum(math.dist(p, center) for p in points) / 6}


def main():
    source, audit, screen, sample = map(read, (SOURCE, AUDIT, SCREEN, SAMPLE))
    if len({source['sha256'], audit['source_sha256'], screen['source_sha256'],
            sample['source_sha256']}) != 1:
        raise ValueError('Inputs belong to different videos')
    frozen = {(p['set'], p['point_number']): p['winner'] for p in sample['selected_points']}
    audit_points = {(p['set'], p['point_number']): p for p in audit['points']}
    screen_points = {(p['set'], p['point_number']): p for p in screen['points']}
    rows = []
    for selected in SELECTIONS:
        number, frame = selected['point_number'], selected['frame']
        if frozen[(3, number)] != selected['winner']:
            raise ValueError('Outcome differs from frozen sample')
        if selected['basis'].startswith('saved_'):
            point = audit_points[(3, number)]
            path = ROOT / point['label_file']
            if sha(path) != point['label_sha256']:
                raise ValueError('Saved player labels changed since audit')
            saved = read(path)['frames'][str(frame)]['players']
            boxes = [p['bbox'] for p in saved]
            if any(b is None for b in boxes) or len(boxes) != 6:
                raise ValueError('Saved candidate lacks six boxes')
            references = [p['player_id'] for p in saved]
        else:
            point = screen_points[(3, number)]
            frame_row = next(r for r in point['rows'] if r['frame'] == frame)
            boxes = [frame_row['candidates'][i]['bbox_px'] for i in selected['detector_indices']]
            references = selected['detector_indices']
        values = {k: round(v, 3) for k, v in image_metrics(boxes).items()}
        rows.append({'set': 3, 'point_number': number, 'frame': frame,
                     'winner': selected['winner'], 'near_side_team_visual_candidate': 'ProVolley',
                     'basis': selected['basis'], 'box_references': references,
                     'airborne_present': selected.get('airborne_present', False),
                     'source_context_status': 'visual_screen_live_play',
                     'boxes_px': boxes, 'metrics': values})
    result = {'status': 'exploratory_selected_snapshot_image_proxy_not_rally_outcome_analysis',
              'source_sha256': source['sha256'], 'sample_sha256': sha(SAMPLE),
              'completed_audit_sha256': sha(AUDIT), 'detector_screen_sha256': sha(SCREEN),
              'selection_rule': 'Three visually screened live set-three snapshots with six distinct near-side boxes; one ProVolley-won and two UTS-won points. Selected after reviewing box availability; not a representative rally sample.',
              'position_definition': 'Full player bounding-box centre (x midpoint, y midpoint) in encoded 1920x1080 source pixels.',
              'metric_definition': 'Mean of 15 pairwise pixel distances, convex hull area in pixel squared, and mean distance to the six-point centroid in pixels.',
              'rows': rows,
              'limitations': ['One frame per point cannot measure rally movement or a rally-level median.',
                              'Image-plane pixels are perspective distorted and are not court metres.',
                              'Box centres change with posture, jumping and fit as well as physical location.',
                              'The three snapshots were selected by visible-box availability after outcome sampling; no statistical winner association is estimated.',
                              'Near-team visual identity has not been independently roster-validated.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(f"| {r['point_number']} | {r['winner']} | {r['frame']} | "
                      f"{r['metrics']['mean_pairwise_spacing_px']:.1f} | "
                      f"{r['metrics']['convex_hull_area_px2']:.0f} | "
                      f"{r['metrics']['centroid_dispersion_px']:.1f} |"
                      for r in rows)
    REPORT.write_text(f'''# Exploratory set-three image-box metric example

The [source-bound record](../data/processed/honours_set3_image_proxy_demo.json) applies the same three geometric formulas to box **centres** in source-image pixels for three visually screened live snapshots. The frame contexts show ball and continuing play: [ProVolley-won point 5](../data/processed/honours_missing_outcome_box_candidates/s3_p5_f155799_context.jpg), [UTS-won point 11](../data/processed/honours_missing_outcome_box_candidates/s3_p11_f162695_context.jpg), and [UTS-won point 37](../data/processed/honours_missing_outcome_box_candidates/s3_p37_f204263_context.jpg). Point 5 uses the [saved six boxes](../data/processed/honours_missing_outcome_box_candidates/s3_p5_f155799_saved.jpg); the [visual screen](HONOURS_MISSING_OUTCOME_VISUAL_SCREEN.md) records the detector choices for points 11 and 37. Point 11 has an airborne player. The same visual screen excludes a saved point-27 box on a far-side player.

| Set-three point | Winner | Frame | Mean spacing (px) | Hull area (px²) | Centroid dispersion (px) |
| ---: | --- | ---: | ---: | ---: | ---: |
{table}

This proves the user's simpler box-centre position rule can be implemented without six manually clicked shoes at these snapshots. The units are **image pixels**, not metres; perspective and posture can change them. The frames were selected by box availability after outcomes were known, and there is only one frame per point with unequal 1-versus-2 groups. No rally-level movement, effect size, significance test or association with winning is inferred. The strict court-coordinate calculator and its zero validated-frame denominator are unchanged.
''', encoding='utf-8')
    print(f'Wrote {OUT} and {REPORT}: {len(rows)} snapshot rows')


if __name__ == '__main__':
    main()
