import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class S3P34CalibrationReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pack = Path(self.tmp.name)
        shutil.copy2(pilot_review.S3P34_CALIBRATION_PACK / 'protocol.json',
                     self.pack / 'protocol.json')
        patcher = patch.object(pilot_review, 'S3P34_CALIBRATION_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)
        self.protocol = json.loads((self.pack / 'protocol.json').read_text(encoding='utf-8'))

    def payload(self, revision):
        return {'expected_revision': revision, 'reviewer_code': 'MZ', 'rows': [
            {'code': landmark['code'], 'status': 'marked', 'x_px': 300.5,
             'y_px': 410.5, 'note': ''}
            for landmark in self.protocol['landmarks']]}

    def test_source_hash_revision_and_frozen_export(self):
        base = '/api/u5/s3p34-calibration-review'
        self.assertEqual(self.client.get(base).status_code, 200)
        self.assertEqual(self.client.post(base + '/export').status_code, 409)
        first, last = [item['frame'] for item in self.protocol['frames']]
        bad = self.payload(0)
        bad['rows'][0]['extra'] = 'not allowed'
        self.assertEqual(self.client.put(f'{base}/{first}', json=bad).status_code, 422)
        self.assertEqual(self.client.put(f'{base}/{first}', json=self.payload(0)).status_code, 200)
        self.assertEqual(self.client.put(f'{base}/{last}', json=self.payload(0)).status_code, 409)
        self.assertEqual(self.client.put(f'{base}/{last}', json=self.payload(1)).status_code, 200)
        exported = self.client.post(base + '/export')
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()['rows'], 12)
        with (self.pack / 'completed.csv').open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 12)
        self.assertEqual(self.client.post(base + '/export').status_code, 409)
        self.assertEqual(self.client.put(f'{base}/{first}', json=self.payload(2)).status_code, 409)


if __name__ == '__main__':
    unittest.main()
