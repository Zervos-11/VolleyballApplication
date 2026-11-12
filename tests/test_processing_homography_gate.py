import json
import tempfile
import unittest
from pathlib import Path

from services.api.processing import _court_bounds, _load_homography


class HomographyGateTests(unittest.TestCase):
    def test_staged_calibration_cannot_enable_metres_or_court_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            match = Path(directory)
            calibration = {
                'points_px': [[100, 600], [1100, 600], [900, 500], [300, 500]],
                'points_court_m': [[1, 0], [7, 0], [7, 6], [1, 6]],
                'court_bounds_m': [0, 9, 0, 9],
                'use_for_metrics': False,
            }
            (match / 'homography.json').write_text(json.dumps(calibration))
            self.assertIsNone(_load_homography(match, {}, video_size=(1280, 720)))
            self.assertIsNone(_court_bounds({}, match))
            calibration['use_for_metrics'] = True
            (match / 'homography.json').write_text(json.dumps(calibration))
            self.assertIsNotNone(_load_homography(match, {}, video_size=(1280, 720)))
            self.assertEqual(_court_bounds({}, match), (0.0, 9.0, 0.0, 9.0))


if __name__ == '__main__':
    unittest.main()
