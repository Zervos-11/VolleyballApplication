import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class S3P34GroundReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pack = Path(self.tmp.name)
        source = pilot_review.S3P34_PACK
        for name in ('single_reviewer_unsampled_blank.csv', 'manifest.json'):
            shutil.copy2(source / name, self.pack / name)
        patcher = patch.object(pilot_review, 'S3P34_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)
        with (self.pack / 'single_reviewer_unsampled_blank.csv').open(newline='', encoding='utf-8') as handle:
            self.reference = list(csv.DictReader(handle))
        self.frames = list(dict.fromkeys(row['source_frame'] for row in self.reference))
        self.jerseys = pilot_review.S3P34_JERSEYS

    def source_payload(self, revision):
        return {'expected_revision': revision, 'reviewer_code': 'MZ', 'rows': [
            {'jersey': jersey, 'identity_status': 'sequence_only', 'ground_status': 'grounded',
             'shoe_midpoint_x_px': None, 'shoe_midpoint_y_px': None,
             'reading_uncertainty_px': None, 'notes': 'Visible ground contact'}
            for jersey in self.jerseys]}

    def paired_payload(self, revision):
        return {'expected_revision': revision, 'rows': [
            {'jersey': jersey, 'candidate_alignment': 'same_player',
             'proxy_floor_alignment': 'plausible'} for jersey in self.jerseys]}

    def test_source_first_revisioned_save_and_frozen_csv_export(self):
        frame = self.frames[0]
        base = f'/api/u5/s3p34-ground-review/{frame}'
        self.assertEqual(self.client.get(f'/api/u5/s3p34-ground-review/paired/{frame}').status_code, 409)
        self.assertEqual(self.client.put(base + '/paired', json=self.paired_payload(0)).status_code, 409)
        self.assertEqual(self.client.post('/api/u5/s3p34-ground-review/export').status_code, 409)
        invalid = self.source_payload(0)
        invalid['rows'][0]['ground_status'] = 'airborne'
        invalid['rows'][0]['shoe_midpoint_x_px'] = 100
        self.assertEqual(self.client.put(base + '/source', json=invalid).status_code, 422)
        self.assertFalse((self.pack / 'single_reviewer_web_draft.json').exists())
        saved = self.client.put(base + '/source', json=self.source_payload(0))
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.put(base + '/source', json=self.source_payload(0)).status_code, 409)
        invalid_paired = self.paired_payload(1) | {'reviewer_code': 'MZ'}
        self.assertEqual(self.client.put(base + '/paired', json=invalid_paired).status_code, 422)
        paired = self.client.put(base + '/paired', json=self.paired_payload(1))
        self.assertEqual(paired.status_code, 200)
        self.assertEqual(self.client.post('/api/u5/s3p34-ground-review/export').status_code, 409)

        revision = 2
        for frame in self.frames[1:]:
            base = f'/api/u5/s3p34-ground-review/{frame}'
            result = self.client.put(base + '/source', json=self.source_payload(revision))
            self.assertEqual(result.status_code, 200)
            revision += 1
            result = self.client.put(base + '/paired', json=self.paired_payload(revision))
            self.assertEqual(result.status_code, 200)
            revision += 1
        exported = self.client.post('/api/u5/s3p34-ground-review/export')
        self.assertEqual(exported.status_code, 200)
        with (self.pack / 'single_reviewer_unsampled_completed.csv').open(newline='', encoding='utf-8') as handle:
            actual = list(csv.DictReader(handle))
        self.assertEqual(len(actual), 180)
        self.assertEqual(actual[0]['image_sha256'], self.reference[0]['image_sha256'])
        self.assertEqual(actual[0]['candidate_alignment'], 'same_player')
        self.assertEqual(actual[-1]['ground_status'], 'grounded')
        self.assertEqual(self.client.post('/api/u5/s3p34-ground-review/export').status_code, 409)
        self.assertEqual(self.client.put(base + '/source', json=self.source_payload(revision)).status_code, 409)
        self.assertEqual(len(list((self.pack / 'single_reviewer_web_history').glob('*.json'))), 60)
        self.assertFalse(json.loads((self.pack / 'single_reviewer_web_draft.json').read_text())['strict_metric_approval'])


if __name__ == '__main__':
    unittest.main()
