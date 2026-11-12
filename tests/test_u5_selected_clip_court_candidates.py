import unittest

from scripts.export_u5_selected_clip_court_candidates import classify, grid


class SelectedClipCourtCandidatesTests(unittest.TestCase):
    def test_grid_respects_edited_clip_bounds_without_filling_all_frames(self):
        self.assertEqual(list(grid(1321, 1340)), [1326, 1332, 1338])
        self.assertEqual(list(grid(12, 12)), [])

    def test_missing_and_ambiguous_six_player_states_stay_separate(self):
        self.assertEqual(classify(None), 'not_screened')
        self.assertEqual(classify({'near_floor_side_candidate_count': 5}),
                         'fewer_than_six_candidates')
        self.assertEqual(classify({'near_floor_side_candidate_count': 6}),
                         'exactly_six_candidates_unvalidated')
        self.assertEqual(classify({'near_floor_side_candidate_count': 7}),
                         'more_than_six_candidates_ambiguous')


if __name__ == '__main__':
    unittest.main()
