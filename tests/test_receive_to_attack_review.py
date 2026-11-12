import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class ReceiveToAttackReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pack = Path(self.tmp.name)
        shutil.copy2(pilot_review.TRANSITION_PACK / 'protocol.json', self.pack / 'protocol.json')
        patcher = patch.object(pilot_review, 'TRANSITION_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)

    def test_source_event_save_revision_and_export(self):
        protocol = json.loads((self.pack / 'protocol.json').read_text())
        revision = 0
        for case in protocol['cases']:
            first = case['provisional_interval_inclusive'][0]
            body = {'expected_revision': revision, 'reviewer_code': 'MZ',
                    'near_side_receives': True,
                    'reception_contact_frame_interval': [first + 10, first + 11],
                    'first_near_side_attack_contact_frame_interval': [first + 40, first + 41],
                    'attack_absent': False, 'source_only_before_metric': True, 'note': ''}
            url = f"/api/receive-to-attack-review/{case['match_id']}/{case['rally_id']}"
            self.assertEqual(self.client.put(url, json=body | {'source_only_before_metric': False}).status_code, 422)
            self.assertEqual(self.client.put(url, json=body).status_code, 200)
            self.assertEqual(self.client.put(url, json=body).status_code, 409)
            revision += 1
        response = self.client.post('/api/receive-to-attack-review/export')
        self.assertEqual(response.status_code, 200, response.text)
        completed = json.loads((self.pack / 'completed.json').read_text())
        self.assertEqual(len(completed['cases']), 2)
        self.assertEqual(self.client.post('/api/receive-to-attack-review/export').status_code, 409)


if __name__ == '__main__':
    unittest.main()
