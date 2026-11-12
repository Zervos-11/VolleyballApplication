import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class S1P6FixedWindowReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        source = pilot_review.S1P6_FIXED_PACK
        self.pack = Path(self.temp.name)
        shutil.copy2(source / 'manifest.json', self.pack / 'manifest.json')
        self.manifest = json.loads((self.pack / 'manifest.json').read_text(encoding='utf-8'))
        for image in self.manifest['images']:
            shutil.copy2(source / image['image'], self.pack / image['image'])
        patcher = patch.object(pilot_review, 'S1P6_FIXED_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)

    def payload(self, revision):
        return {'expected_revision': revision, 'reviewer_code': 'MZ',
                'source_phase': 'live', 'rows': [
                    {'slot': n, 'identity_status': 'sequence_consistent',
                     'ground_status': 'grounded', 'shoe_x_px': None,
                     'shoe_y_px': None, 'note': ''} for n in range(1, 7)]}

    def test_revisioned_source_review_and_frozen_export(self):
        base = '/api/u5/s1p6-fixed-window-review'
        self.assertEqual(self.client.get(base).status_code, 200)
        self.assertEqual(self.client.post(base + '/export').status_code, 409)
        revision = 0
        for item in self.manifest['images']:
            frame = item['source_frame']
            bad = self.payload(revision)
            bad['rows'][0]['extra'] = 'reject'
            self.assertEqual(self.client.put(f'{base}/{frame}', json=bad).status_code, 422)
            saved = self.client.put(f'{base}/{frame}', json=self.payload(revision))
            self.assertEqual(saved.status_code, 200)
            revision += 1
        self.assertEqual(self.client.put(f'{base}/{frame}', json=self.payload(0)).status_code, 409)
        exported = self.client.post(base + '/export')
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()['rows'], 30)
        self.assertTrue((self.pack / 'completed.csv').exists())
        self.assertEqual(self.client.post(base + '/export').status_code, 409)


if __name__ == '__main__':
    unittest.main()
