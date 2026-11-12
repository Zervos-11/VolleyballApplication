import unittest

from scripts.analyze_u5_dynamic_error_sensitivity import simulate
from scripts.compute_honours_team_metrics import metrics


class DynamicErrorSensitivityTests(unittest.TestCase):
    def test_zero_radius_preserves_matched_cell_contrasts(self):
        rows = []
        for set_number in (1, 2, 3):
            for won, scale in ((True, 1.2), (False, 1.0)):
                points = [(0, 0), (scale, 0), (0, scale), (scale, scale),
                          (scale / 2, scale / 2), (scale / 2, scale)]
                rows.append({'set': set_number, 'phase': 'defense',
                             'near_team_won': won,
                             'frames': [{'court_proxy_m': points}],
                             'window_median': metrics(points)})
        result = simulate(rows, radius=0, draws=5, seed=7)
        for field in result:
            self.assertEqual(result[field]['minimum'], result[field]['maximum'])
            self.assertEqual(result[field]['fraction_positive'], 1.0)


if __name__ == '__main__':
    unittest.main()
