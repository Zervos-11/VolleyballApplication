"""Check gap grouping and first-frame box matching helpers."""

import unittest

from scripts.audit_u5_two_long_runs_30fps import intervals, iou


class DenseRunAuditTests(unittest.TestCase):
    def test_missing_frames_keep_separate_gaps(self):
        self.assertEqual(intervals([36015, 36026, 36030, 36031, 36047]),
                         [[36015, 36015], [36026, 36026],
                          [36030, 36031], [36047, 36047]])

    def test_box_overlap_uses_union_area(self):
        self.assertAlmostEqual(iou([0, 0, 2, 2], [1, 1, 3, 3]), 1 / 7)
        self.assertEqual(iou([0, 0, 1, 1], [2, 2, 3, 3]), 0)


if __name__ == '__main__':
    unittest.main()
