import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class S1P6PairedReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        original = pilot_review.S1P6_FIXED_PACK
        self.pack = Path(self.temp.name)
        for name in ('manifest.json', 'completed.csv', 'exact_30fps_candidates.json',
                     'joined_diagnostic.json'):
            shutil.copy2(original / name, self.pack / name)
        manifest = json.loads((self.pack / 'manifest.json').read_text(encoding='utf-8'))
        for item in manifest['images']:
            shutil.copy2(original / item['image'], self.pack / item['image'])
        patcher = patch.object(pilot_review, 'S1P6_FIXED_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)

    def test_explicit_frame_check_and_frozen_export(self):
        base = '/api/u5/s1p6-paired-review'
        state = self.client.get(base)
        self.assertEqual(state.status_code, 200)
        frames = state.json()['frames']
        self.assertEqual(len(frames), 5)
        self.assertEqual(self.client.post(base + '/export').status_code, 409)
        revision = 0
        for item in frames:
            rows = [{'slot': n, 'raw_track_id': None, 'candidate_alignment': 'no_box',
                     'floor_alignment': 'not_applicable', 'note': ''} for n in range(1, 7)]
            payload = {'expected_revision': revision, 'reviewer_code': 'MZ',
                       'checked_source_and_boxes': False, 'rows': rows}
            self.assertEqual(self.client.put(f"{base}/{item['frame']}", json=payload).status_code, 422)
            payload['checked_source_and_boxes'] = True
            pair = item['proximity_pairs'][0]
            rows[pair['slot'] - 1].update(raw_track_id=pair['raw_track_id'],
                                          candidate_alignment='same_player',
                                          floor_alignment='plausible')
            self.assertEqual(self.client.put(f"{base}/{item['frame']}", json=payload).status_code, 200)
            revision += 1
        self.assertEqual(self.client.put(f"{base}/{item['frame']}", json=payload).status_code, 409)
        result = self.client.post(base + '/export')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['rows'], 30)
        self.assertTrue((self.pack / 'paired_completed.csv').exists())
        self.assertEqual(self.client.post(base + '/export').status_code, 409)


if __name__ == '__main__':
    unittest.main()
