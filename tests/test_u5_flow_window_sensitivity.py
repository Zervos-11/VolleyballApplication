import unittest

from scripts.audit_u5_flow_window_sensitivity import equal_cell_contrast


class FlowWindowSensitivityTests(unittest.TestCase):
    def test_equal_cell_average_and_dropped_unmatched_cell(self):
        rows = [
            {'set': 1, 'phase': 'defense', 'near_team_won': True,
             'median_image_metrics': {'spacing_px': 20}},
            {'set': 1, 'phase': 'defense', 'near_team_won': False,
             'median_image_metrics': {'spacing_px': 10}},
            {'set': 2, 'phase': 'offense', 'near_team_won': True,
             'median_image_metrics': {'spacing_px': 100}},
            {'set': 2, 'phase': 'offense', 'near_team_won': False,
             'median_image_metrics': {'spacing_px': 70}},
        ]
        self.assertEqual(equal_cell_contrast(rows, 'spacing_px'),
                         {'matched_cells': 2, 'matched_points': 4, 'difference': 20})
        self.assertEqual(equal_cell_contrast(rows[:-2]+rows[-1:], 'spacing_px'),
                         {'matched_cells': 1, 'matched_points': 2, 'difference': 10})


if __name__ == '__main__':
    unittest.main()
