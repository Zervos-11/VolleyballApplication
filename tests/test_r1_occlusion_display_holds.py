import unittest

from scripts.build_r1_occlusion_display_holds import build_holds


def slot(box, status="raw_box_candidate"):
    return {"bbox_px": box, "box_status": status, "court_position_m": None}


class R1OcclusionDisplayHoldTests(unittest.TestCase):
    def test_crossing_creates_short_display_hold_then_clears_on_return(self):
        rows = [
            {"frame": 0, "players": {"a": slot([0, 0, 100, 100]), "b": slot([80, 0, 180, 105])}},
            {"frame": 1, "players": {"a": slot(None, "missing"), "b": slot([45, 0, 145, 105])}},
            {"frame": 2, "players": {"a": slot([10, 0, 110, 100]), "b": slot([90, 0, 190, 105])}},
        ]
        holds = build_holds(rows)
        self.assertEqual(list(holds), ["1"])
        held = holds["1"]["a"]
        self.assertEqual(held["display_anchor_px"], [50.0, 50.0])
        self.assertEqual(held["candidate_occluder_players"], ["b"])
        self.assertIsNone(held["court_position_m"])
        self.assertIsNone(held["bbox_px"])
        self.assertFalse(held["motion_observed"])
        self.assertFalse(held["current_position_inferred"])

    def test_no_foreground_overlap_or_invalid_box_is_never_held(self):
        rows = [
            {"frame": 0, "players": {"a": slot([0, 0, 100, 100]), "b": slot([200, 0, 300, 100])}},
            {"frame": 1, "players": {"a": slot(None, "missing"), "b": slot([200, 0, 300, 100])}},
            {"frame": 2, "players": {"a": slot(None, "invalid_truncated"), "b": slot([0, 0, 100, 100])}},
            {"frame": 3, "players": {"a": slot(None, "missing"), "b": slot([0, 0, 100, 60])}},
        ]
        self.assertEqual(build_holds(rows), {})

    def test_hold_expires_after_eight_frames(self):
        rows = [{"frame": 0, "players": {"a": slot([0, 0, 100, 100]), "b": slot([0, 0, 100, 100])}}]
        rows.extend({"frame": frame, "players": {"a": slot(None, "missing"),
                                                   "b": slot([0, 0, 100, 100])}}
                    for frame in range(1, 11))
        holds = build_holds(rows)
        self.assertEqual(sorted(map(int, holds)), list(range(1, 9)))


if __name__ == "__main__":
    unittest.main()
