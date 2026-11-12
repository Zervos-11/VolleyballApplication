"""Check that raw-ID continuity never bridges missing candidate observations."""

import unittest

from scripts.analyze_u5_full_clip_tracklets import longest_six_run, tracklets


def row(frame, ids, core=True):
    return {
        'source_frame': frame,
        'in_conservative_core': core,
        'proposals': [
            {'raw_track_id': item, 'net_side_status': 'near_floor_side_candidate',
             'box_bottom_court_m': [float(item), 1.0]}
            for item in ids
        ],
    }


class FullClipTrackletTests(unittest.TestCase):
    def test_missing_sample_splits_reappearing_id(self):
        segments = tracklets([row(0, [1]), row(6, []), row(12, [1])])
        self.assertEqual([(t['first_frame'], t['last_frame']) for t in segments],
                         [(0, 0), (12, 12)])

    def test_frame_jump_splits_even_when_id_is_present(self):
        segments = tracklets([row(0, [1]), row(12, [1])])
        self.assertEqual(len(segments), 2)

    def test_six_run_requires_distinct_ids_and_consecutive_frames(self):
        six = [1, 2, 3, 4, 5, 6]
        rows = [row(0, six), row(6, six), row(12, [1, 2, 3, 4, 5, 5]),
                row(18, six), row(24, six, core=False), row(36, six)]
        self.assertEqual(longest_six_run(rows)['sampled_frames'], 2)
        self.assertEqual(longest_six_run(rows, core_only=True)['last_frame'], 6)


if __name__ == '__main__':
    unittest.main()
