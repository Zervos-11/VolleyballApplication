import unittest

from scripts.analyze_u5_fixed_box_court_proxy import (
    equal_cell_difference, exact_label_reference, fixed_bottom_at, project_xy,
)


class FixedBoxCourtProxyTests(unittest.TestCase):
    def test_fixed_bottom_preserves_anchor_height_offset(self):
        player = {'anchor_bbox_px': [10, 20, 30, 80],
                  'frames': {'101': {'translation_px': [5, -3]}}}
        self.assertEqual(fixed_bottom_at(player, 101), (25, 77))

    def test_homography_projects_floor_point(self):
        identity = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        self.assertEqual(project_xy(4, 8, identity), (4, 8))

    def test_cell_difference_and_exact_reference(self):
        rows = [
            {'set': 1, 'phase': 'defense', 'near_team_won': True,
             'window_median': {'mean_pairwise_spacing_m': 4}},
            {'set': 1, 'phase': 'defense', 'near_team_won': False,
             'window_median': {'mean_pairwise_spacing_m': 2}},
            {'set': 2, 'phase': 'offense', 'near_team_won': True,
             'window_median': {'mean_pairwise_spacing_m': 8}},
            {'set': 2, 'phase': 'offense', 'near_team_won': False,
             'window_median': {'mean_pairwise_spacing_m': 2}},
        ]
        field = 'mean_pairwise_spacing_m'
        self.assertEqual(equal_cell_difference(rows, field), (4, 2))
        self.assertEqual(exact_label_reference(rows, field),
                         {'assignments': 4, 'two_sided_reference_fraction': 0.5})


if __name__ == '__main__':
    unittest.main()
