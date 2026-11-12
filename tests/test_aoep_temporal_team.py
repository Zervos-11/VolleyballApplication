import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_aoep_temporal_team import continuous, team_status
from audit_aoep_id_handoffs import decision
from audit_aoep_duplicate_tracks import suppress_supported_duplicates
from draft_aoep_anchor_interpolation import proposal, court_position_status
from build_aoep_visibility_states import state_for
from audit_aoep_occlusion_hold_v2 import plausible_foreground_occluder, raw_flags
from build_aoep_sam_image_path import build_path


class TemporalTeamGuardrails(unittest.TestCase):
    def test_static_box_beyond_net_stays_unknown(self):
        anchor = {'frame': 100, 'box': [10, 10, 50, 110]}
        self.assertEqual(team_status('beyond_projected_net_unresolved', 101,
                                     [10, 10, 50, 110], anchor), 'unknown')

    def test_rising_box_can_keep_team_without_floor_position(self):
        anchor = {'frame': 100, 'box': [10, 10, 50, 110]}
        self.assertEqual(team_status('beyond_projected_net_unresolved', 101,
                                     [10, 0, 50, 100], anchor),
                         'near_candidate_airborne_image_only')
        self.assertEqual(team_status('beyond_projected_net_unresolved', 132,
                                     [10, 0, 50, 100], anchor), 'unknown')

    def test_same_tracker_id_does_not_override_appearance_break(self):
        hist_a = np.zeros((2, 1), np.float32)
        hist_b = np.zeros((2, 1), np.float32)
        hist_a[0, 0] = 1
        hist_b[1, 0] = 1
        state = {'frame': 100, 'box': [10, 10, 50, 110], 'hist': hist_a}
        self.assertFalse(continuous(state, 101, [11, 11, 51, 111], hist_b))
        self.assertFalse(continuous(state, 107, [11, 11, 51, 111], hist_a))

    def test_real_navy_to_yellow_nearby_box_is_not_a_handoff(self):
        reasons = decision('unknown', [102, 88, 99], [42, 92, 102],
                           [50, 53, 153], 1, .4, .93, .534)
        self.assertIn('source_jersey_unstable', reasons)
        self.assertIn('destination_jersey_mismatch', reasons)

    def test_clear_short_colour_consistent_edge_only_becomes_review_candidate(self):
        self.assertEqual(decision('near_candidate_in_region', [21, 160, 180],
                                  [20, 150, 175], [23, 145, 170],
                                  2, .2, 1.02, .3), [])

    def test_supported_duplicate_removes_only_lower_confidence_copy(self):
        rows = [
            {'track_id': 346, 'bbox': [0, 0, 100, 200], 'confidence': .7},
            {'track_id': 492, 'bbox': [5, 5, 105, 205], 'confidence': .5},
            {'track_id': 29, 'bbox': [250, 0, 350, 200], 'confidence': .3},
        ]
        selected, suppressed = suppress_supported_duplicates(rows, [(346, 492)])
        self.assertEqual([row['track_id'] for row in selected], [346, 29])
        self.assertEqual(suppressed[0]['suppressed_raw_track_id'], 492)
        self.assertEqual(len(rows), 3)  # Frozen input remains intact.

    def test_out_of_frame_entry_is_left_unboxed_between_anchors(self):
        anchors = {
            10: {'bbox_source_px': None, 'visibility': 'out_of_frame'},
            20: {'bbox_source_px': [90, 10, 100, 70], 'visibility': 'partially_occluded_or_truncated'},
        }
        middle = proposal(15, 'yellow_right_entrant', anchors)
        self.assertIsNone(middle['bbox_source_px'])
        self.assertEqual(middle['draft_status'], 'requires_source_frame_review')

    def test_airborne_draft_never_gets_floor_position(self):
        contact = {'visual_player_id': 'yellow_setter_18', 'observations': [
            {'frames_inclusive': [20, 25], 'court_position_status': 'unknown_airborne'},
            {'frames_inclusive': [26, 30], 'court_position_status': 'unknown_landing_transition'},
        ]}
        self.assertEqual(court_position_status(23, 'yellow_setter_18', contact), 'unknown_airborne')
        self.assertEqual(court_position_status(28, 'yellow_setter_18', contact),
                         'unknown_landing_transition')
        self.assertEqual(court_position_status(23, 'navy_libero_10', contact), 'not_estimated')

    def test_visible_gap_keeps_player_slot_without_inventing_raw_box(self):
        draft = {'visual_player_id': 'yellow_right_entrant',
                 'draft_status': 'interpolated_unreviewed', 'visibility': 'unknown_interpolated'}
        navigation = {'navigation_status': 'unresolved_no_box_over_threshold',
                      'candidate_raw_track_id': None}
        self.assertEqual(state_for(75220, draft, navigation),
                         ('visible_at_right_no_usable_full_player_raw_box', None))

    def test_occlusion_hold_requires_foreground_box_and_expires_without_position(self):
        missing = [0, 0, 100, 100]
        elevated = [20, -20, 80, 60]
        foreground = [20, 0, 80, 120]
        self.assertFalse(plausible_foreground_occluder(missing, elevated))
        self.assertTrue(plausible_foreground_occluder(missing, foreground))
        predictions = {'0': [{'track_id': 131, 'bbox': missing}]}
        for frame in range(1, 10):
            predictions[str(frame)] = [{'track_id': 3,
                                        'bbox': elevated if frame == 1 else foreground}]
        flags = raw_flags(predictions, 0, 9, (131,))
        self.assertEqual(flags['1']['131']['status'], 'missing_unknown')
        self.assertEqual(flags['2']['131']['status'], 'possible_foreground_occlusion')
        self.assertIsNone(flags['2']['131']['bbox'])
        self.assertEqual(flags['8']['131']['hold_age_frames'], 8)
        self.assertEqual(flags['9']['131']['status'], 'no_raw_hold')

    def test_image_path_interpolates_short_gap_only_without_crossing_no_box_state(self):
        predictions = {str(frame): [] for frame in range(11)}
        predictions['0'] = [{'track_id': 517, 'bbox': [0, 0, 10, 10]}]
        predictions['10'] = [{'track_id': 517, 'bbox': [100, 0, 110, 10]}]
        long_gap = build_path(predictions, {}, 0, 10, 517, 'Sam')
        self.assertEqual(long_gap['5']['status'], 'unresolved_gap')
        saved = {'2': {'players': [{'player_id': 'Sam', 'bbox': [20, 0, 30, 10]}]},
                 '5': {'players': [{'player_id': 'Sam', 'bbox': None}]}}
        path = build_path(predictions, saved, 0, 10, 517, 'Sam')
        self.assertEqual(path['1']['status'], 'interpolated_image_centre_not_observed')
        self.assertEqual(path['1']['image_point_px'], [15.0, 5.0])
        self.assertEqual(path['2']['status'], 'saved_assisted_box_centre')
        self.assertEqual(path['3']['status'], 'unresolved_gap')
        self.assertEqual(path['5']['status'], 'saved_no_box')
        self.assertTrue(all(row['court_position_m'] is None for row in path.values()))


if __name__ == '__main__':
    unittest.main()
