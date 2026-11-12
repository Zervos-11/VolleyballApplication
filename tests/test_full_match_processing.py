import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from services.api.processing import _pick_video, _simultaneous_pairwise_distance, compute_tracking_metrics


class FullMatchProcessingTests(unittest.TestCase):
    def test_pairwise_distance_uses_only_players_visible_together(self):
        points = np.array([[0, 0], [3, 4], [100, 0], [103, 4], [500, 0]], dtype=float)
        frames = np.array([10, 10, 11, 11, 12])
        mean, eligible_frames, pairs = _simultaneous_pairwise_distance(points, frames)
        self.assertEqual((mean, eligible_frames, pairs), (5.0, 2, 2))
        self.assertEqual(_simultaneous_pairwise_distance(points[[0, 2, 4]], frames[[0, 2, 4]]),
                         (None, 0, 0))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.match = Path(self.tmp.name)
        video = cv2.VideoWriter(str(self.match / "source.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
        self.assertTrue(video.isOpened())
        for _ in range(100):
            video.write(np.zeros((48, 64, 3), dtype=np.uint8))
        video.release()

    def test_late_rallies_are_tracked_with_absolute_frames_and_distinct_ids(self):
        calls = []

        def fake_track(_video, **kwargs):
            calls.append((kwargs["start_frame"], kwargs["end_frame_exclusive"]))
            return [(kwargs["start_frame"] + i, 1, 20.0 + i, 30.0) for i in range(2)]

        rallies = [dict(rally_id="early", t_start=1, t_end=2), dict(rally_id="late", t_start=8, t_end=9)]
        with patch("services.inference.yolo_tracker.track_players", side_effect=fake_track):
            result = compute_tracking_metrics(self.match, rallies, {"rally_end_pad_s": 0}, fps=30)
        self.assertEqual(calls, [(10, 20), (80, 90)])
        self.assertEqual([r["rally_id"] for r in result], ["early", "late"])
        self.assertTrue(all(r["coverage"]["cha"] is not None for r in result))
        self.assertTrue(all(r["transition"]["latency_s"] is None for r in result))
        self.assertTrue(all(r["outcome_pred"]["p_win"] is None for r in result))
        self.assertEqual([r["quality"]["start_frame"] for r in result], [10, 80])
        self.assertEqual([r["quality"]["end_frame_exclusive"] for r in result], [20, 90])
        self.assertTrue(all(r["quality"]["frames_with_track_observations"] == 2 for r in result))
        self.assertTrue(all(r["quality"]["frames_without_track_observations"] == 8 for r in result))
        self.assertTrue(all(r["quality"]["team_identity_verified"] is False for r in result))
        self.assertTrue(all(r["quality"]["ground_positions_verified"] is False for r in result))
        self.assertTrue(all(r["coverage"]["mpd"] is None for r in result))
        self.assertTrue(all(r["quality"]["simultaneous_pairs"] == 0 for r in result))
        rows = (self.match / "tracks_centroids.csv").read_text().splitlines()[1:]
        self.assertEqual([row.split(",")[:2] for row in rows], [["10", "1"], ["11", "1"], ["80", "3"], ["81", "3"]])

    def test_frame_limit_fails_before_tracking_or_writing_partial_output(self):
        with patch("services.inference.yolo_tracker.track_players") as tracker:
            with self.assertRaisesRegex(ValueError, "exceeds max_frames"):
                compute_tracking_metrics(self.match, [dict(rally_id="long", t_start=0, t_end=8)],
                                         {"rally_end_pad_s": 0}, fps=10, max_frames=20)
        tracker.assert_not_called()
        self.assertFalse((self.match / "tracks_centroids.csv").exists())

    def test_api_spacing_does_not_mix_detections_from_different_frames(self):
        def fake_track(_video, **kwargs):
            first = kwargs["start_frame"]
            return [(first, 1, 0.0, 0.0), (first, 2, 3.0, 4.0),
                    (first + 1, 1, 100.0, 0.0), (first + 1, 2, 103.0, 4.0)]

        with patch("services.inference.yolo_tracker.track_players", side_effect=fake_track):
            result = compute_tracking_metrics(
                self.match, [dict(rally_id="spacing", t_start=1, t_end=2)],
                {"rally_end_pad_s": 0}, fps=10,
            )[0]
        self.assertEqual(result["coverage"]["mpd"], 5.0)
        self.assertEqual(result["quality"]["simultaneous_pair_frames"], 2)
        self.assertEqual(result["quality"]["simultaneous_pairs"], 2)
        self.assertEqual(result["quality"]["position_source"], "box_bottom_center_px")

    def test_multiple_video_files_require_explicit_source_record(self):
        (self.match / "derivative.mp4").touch()
        with self.assertRaisesRegex(ValueError, "Multiple videos"):
            _pick_video(self.match)
        (self.match / "source_record.json").write_text(json.dumps({"video_file": "source.mp4"}))
        self.assertEqual(_pick_video(self.match), (self.match / "source.mp4").resolve())

    def test_rally_with_no_detections_reports_missing_frames(self):
        def fake_track(_video, **kwargs):
            if kwargs["start_frame"] == 10:
                return [(10, 1, 20.0, 30.0), (11, 1, 21.0, 30.0)]
            return []

        rallies = [dict(rally_id="seen", t_start=1, t_end=2), dict(rally_id="empty", t_start=5, t_end=6)]
        with patch("services.inference.yolo_tracker.track_players", side_effect=fake_track):
            result = compute_tracking_metrics(self.match, rallies, {"rally_end_pad_s": 0}, fps=10)
        empty = result[1]
        self.assertEqual(empty["quality"]["status"], "insufficient_observations")
        self.assertEqual(empty["quality"]["frames_without_track_observations"], 10)
        self.assertEqual(empty["quality"]["raw_track_observations"], 0)
        self.assertIsNone(empty["coverage"]["cha"])

    def test_no_detections_anywhere_returns_explicit_empty_result(self):
        with patch("services.inference.yolo_tracker.track_players", return_value=[]):
            result = compute_tracking_metrics(self.match, [dict(rally_id="empty", t_start=5, t_end=6)],
                                             {"rally_end_pad_s": 0}, fps=10)
        self.assertEqual(result[0]["quality"]["status"], "insufficient_observations")
        self.assertEqual(result[0]["quality"]["frames_without_track_observations"], 10)
        self.assertIsNone(result[0]["coverage"]["cha"])
        self.assertEqual((self.match / "tracks_centroids.csv").read_text(), "frame,track_id,cx,cy\n")
        diagnostics = json.loads((self.match / "processing_diagnostics.json").read_text())
        self.assertIsNone(diagnostics["min_frame"])
