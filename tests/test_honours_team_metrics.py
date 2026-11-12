import unittest

from scripts.compute_honours_team_metrics import compute, hull_area, metrics


class TeamMetricsTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(hull_area([(0, 0), (9, 0), (9, 9), (0, 9), (4, 4), (5, 5)]), 81)
        self.assertEqual(metrics([(2, 3)] * 6), {
            'mean_pairwise_spacing_m': 0.0,
            'convex_hull_area_m2': 0.0,
            'centroid_dispersion_m': 0.0,
        })

    def test_missing_player_blocks_frame_and_near_team_is_checked(self):
        sample = {'match_id': 'm', 'source_sha256': 'source',
                  'selected_points': [{'set': 1, 'point_number': 2, 'winner': 'UTS'}]}
        players = {str(i): {'status': 'reviewed_floor_contact', 'x_m': i, 'y_m': i}
                   for i in range(6)}
        missing = {k: dict(v) for k, v in players.items()}
        missing['5'] = {'status': 'occluded', 'x_m': None, 'y_m': None}
        data = {'match_id': 'm', 'source_sha256': 'source', 'set': 1, 'point_number': 2,
                'winner': 'UTS', 'near_team': 'UTS', 'near_team_evidence_status': 'source_reviewed',
                'near_roster_review_status': 'source_reviewed_near_six',
                'calibration_status': 'validated_for_metric_use', 'rally_boundary_status': 'source_reviewed',
                'start_frame': 100, 'end_frame_exclusive': 103,
                'near_player_ids': list(players),
                'frames': [{'frame': 100, 'players': players}, {'frame': 101, 'players': missing}]}
        result = compute(data, sample)
        self.assertTrue(result['near_team_won'])
        self.assertEqual(result['eligible_frame_count'], 1)
        self.assertEqual(result['interval_type'], 'source_reviewed_full_rally')
        self.assertEqual(result['eligible_fraction_of_submitted_frames'], 1 / 2)
        self.assertEqual(result['eligible_fraction_of_interval'], 1 / 3)
        self.assertEqual(result['position_method'], 'reviewed_floor_contact')
        self.assertIsNone(result['frames'][1]['metrics'])
        self.assertEqual(result['frames'][1]['reasons'], ['5:occluded'])
        data['near_team_evidence_status'] = 'unknown'
        with self.assertRaises(ValueError):
            compute(data, sample)
        data['near_team_evidence_status'] = 'source_reviewed'
        data['near_roster_review_status'] = 'candidate'
        with self.assertRaisesRegex(ValueError, 'roster'):
            compute(data, sample)
        data['near_roster_review_status'] = 'source_reviewed_near_six'
        data['rally_boundary_status'] = 'navigation_only'
        with self.assertRaisesRegex(ValueError, 'fixed analysis window'):
            compute(data, sample)
        data['analysis_window_status'] = 'source_reviewed_fixed_window'
        self.assertEqual(compute(data, sample)['interval_type'],
                         'source_reviewed_fixed_analysis_window')

    def test_grounded_box_bottom_is_explicit_and_airborne_is_missing(self):
        sample = {'match_id': 'm', 'source_sha256': 'source',
                  'selected_points': [{'set': 1, 'point_number': 2, 'winner': 'UTS'}]}
        players = {str(i): {'status': 'reviewed_grounded_box_bottom_proxy',
                            'x_m': i, 'y_m': i} for i in range(6)}
        airborne = {k: dict(v) for k, v in players.items()}
        airborne['5'] = {'status': 'airborne', 'x_m': None, 'y_m': None}
        data = {'match_id': 'm', 'source_sha256': 'source', 'set': 1, 'point_number': 2,
                'winner': 'UTS', 'near_team': 'UTS', 'near_team_evidence_status': 'source_reviewed',
                'near_roster_review_status': 'source_reviewed_near_six',
                'calibration_status': 'validated_for_metric_use', 'rally_boundary_status': 'source_reviewed',
                'position_method': 'reviewed_grounded_box_bottom_proxy',
                'start_frame': 100, 'end_frame_exclusive': 102,
                'near_player_ids': list(players),
                'frames': [{'frame': 100, 'players': players},
                           {'frame': 101, 'players': airborne}]}
        result = compute(data, sample)
        self.assertEqual(result['position_method'], 'reviewed_grounded_box_bottom_proxy')
        self.assertEqual(result['eligible_frame_count'], 1)
        self.assertEqual(result['frames'][1]['reasons'], ['5:airborne'])
        data['frames'][0]['players']['5'] = {'status': 'reviewed_floor_contact',
                                            'x_m': 5, 'y_m': 5}
        self.assertEqual(compute(data, sample)['eligible_frame_count'], 0)

    def test_u5_score_only_sample_keeps_strict_review_gates(self):
        sample = {'video_id': 'u5HnY2aNW14', 'source_sha256': 'u5-source',
                  'selected_events': [{'set': 2, 'point_number': 14,
                                       'winner_scoreboard_side': 'right'}]}
        players = {str(i): {'status': 'reviewed_grounded_box_bottom_proxy',
                            'x_m': i, 'y_m': i} for i in range(6)}
        data = {'match_id': 'yt_u5HnY2aNW14', 'source_sha256': 'u5-source',
                'set': 2, 'point_number': 14, 'winner': 'Concordia',
                'near_team': 'Concordia', 'near_team_evidence_status': 'source_reviewed',
                'near_roster_review_status': 'source_reviewed_near_six',
                'calibration_status': 'validated_for_metric_use',
                'rally_boundary_status': 'source_reviewed',
                'position_method': 'reviewed_grounded_box_bottom_proxy',
                'start_frame': 100, 'end_frame_exclusive': 101,
                'near_player_ids': list(players),
                'frames': [{'frame': 100, 'players': players}]}
        self.assertEqual(compute(data, sample)['eligible_frame_count'], 1)
        data['winner'] = 'UCLA'
        with self.assertRaisesRegex(ValueError, 'Winner'):
            compute(data, sample)
        data['winner'] = 'Concordia'
        data['calibration_status'] = 'staged'
        with self.assertRaisesRegex(ValueError, 'calibration'):
            compute(data, sample)


if __name__ == '__main__':
    unittest.main()
