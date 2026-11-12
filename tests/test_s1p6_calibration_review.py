import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class S1P6CalibrationReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pack = Path(self.temp.name)
        shutil.copy2(pilot_review.S1P6_CALIBRATION_PACK / 'protocol.json', self.pack / 'protocol.json')
        patcher = patch.object(pilot_review, 'S1P6_CALIBRATION_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)

    def test_source_only_click_form_and_frozen_export(self):
        base = '/api/u5/s1p6-calibration-review'
        state = self.client.get(base)
        self.assertEqual(state.status_code, 200)
        protocol = json.loads((self.pack / 'protocol.json').read_text(encoding='utf-8'))
        self.assertEqual(self.client.post(base + '/export').status_code, 409)
        for revision, frame in enumerate(protocol['frames']):
            rows = [{'code': item['code'], 'status': 'uncertain', 'x_px': None,
                     'y_px': None, 'note': ''} for item in protocol['landmarks']]
            payload = {'expected_revision': revision, 'reviewer_code': 'MZ', 'rows': rows}
            invalid = json.loads(json.dumps(payload))
            invalid['rows'][0]['extra'] = 'reject'
            self.assertEqual(self.client.put(f"{base}/{frame['frame']}", json=invalid).status_code, 422)
            self.assertEqual(self.client.put(f"{base}/{frame['frame']}", json=payload).status_code, 200)
        exported = self.client.post(base + '/export')
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.json()['rows'], 12)
        self.assertTrue((self.pack / 'completed.csv').exists())
        self.assertEqual(self.client.post(base + '/export').status_code, 409)


if __name__ == '__main__':
    unittest.main()
