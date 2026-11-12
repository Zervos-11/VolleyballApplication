import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_u5_phase_matched_proxy import exact_permutation, project  # noqa: E402
from pilot_u5_box_centre_flow import track_direction  # noqa: E402
from analyze_u5_flow_window_geometry import contrast  # noqa: E402


class PhaseMatchedProxyTests(unittest.TestCase):
    def test_exact_reference_enumerates_within_cell_labels(self):
        values = [1, 2, 3, 4]
        rows = [{'set': 1, 'phase': 'near_defense', 'near_team_won': i >= 2,
                 'proxy_metrics': {'mean_pairwise_spacing_m': value}}
                for i, value in enumerate(values)]
        result = exact_permutation(rows, 'mean_pairwise_spacing_m')
        self.assertEqual(result['conditional_label_assignments'], 6)
        self.assertEqual(result['observed_equal_cell_win_minus_loss'], 2)
        self.assertEqual(result['two_sided_reference_fraction'], 0.3333)

    def test_floor_transform_maps_source_corners(self):
        path = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/near_court_candidate.json'
        calibration = json.loads(path.read_text(encoding='utf-8'))
        h = calibration['homography_image_to_court']
        for source, expected in zip(calibration['points_px'], calibration['points_court_m']):
            x, y = project([source[0], 0, source[0], source[1]], h)
            self.assertAlmostEqual(x, expected[0], places=8)
            self.assertAlmostEqual(y, expected[1], places=8)

    def test_optical_flow_follows_translated_texture(self):
        texture = np.random.default_rng(19).integers(0, 256, (32, 32), dtype=np.uint8)
        grays = {}
        for frame in range(25):
            image = np.zeros((100, 100), np.uint8)
            image[30:62, 20+frame:52+frame] = texture
            grays[frame] = image
        bbox = [32, 30, 64, 62]
        forward, seed_count = track_direction(grays, 12, bbox, 1)
        backward, _ = track_direction(grays, 12, bbox, -1)
        self.assertGreaterEqual(seed_count, 4)
        self.assertAlmostEqual(forward[24]['dx'], 12, delta=.5)
        self.assertAlmostEqual(backward[0]['dx'], -12, delta=.5)

    def test_equal_cell_temporal_contrast(self):
        rows = [
            {'set': 1, 'phase': 'near_defense', 'near_team_won': False, 'value': {'spacing_px': 1}},
            {'set': 1, 'phase': 'near_defense', 'near_team_won': True, 'value': {'spacing_px': 5}},
            {'set': 1, 'phase': 'near_defense', 'near_team_won': True, 'value': {'spacing_px': 7}},
            {'set': 2, 'phase': 'near_offense', 'near_team_won': True, 'value': {'spacing_px': 2}},
            {'set': 2, 'phase': 'near_offense', 'near_team_won': False, 'value': {'spacing_px': 3}},
            {'set': 2, 'phase': 'near_offense', 'near_team_won': False, 'value': {'spacing_px': 5}},
        ]
        self.assertEqual(contrast(rows, 'value', 'spacing_px'), 1.5)


if __name__ == '__main__':
    unittest.main()
