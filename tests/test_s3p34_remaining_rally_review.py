import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class RemainingRallyReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pack = Path(self.tmp.name)
        original = pilot_review.S3P34_REMAINING_PACK
        manifest = json.loads((original / 'manifest.json').read_text(encoding='utf-8'))
        self.item = next(row for row in manifest['frames']
                         if row['source_frame'] == 36112)
        manifest['frames'] = [self.item]
        (self.pack / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (self.pack / 'focused_10hz_protocol.json').write_text(
            json.dumps({'new_frames_to_review': [self.item['source_frame']]}), encoding='utf-8')
        shutil.copy2(original / self.item['image'], self.pack / self.item['image'])
        patcher = patch.object(pilot_review, 'S3P34_REMAINING_PACK', self.pack)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)
        self.base = f"/api/u5/s3p34-remaining-rally-review/{self.item['source_frame']}"

    def test_source_first_save_missing_box_and_frozen_export(self):
        state = self.client.get('/api/u5/s3p34-remaining-rally-review').json()
        self.assertEqual(state['frames'][0]['numbered_boxes'], self.item['numbered_boxes'])
        self.assertEqual(self.client.get(
            f"/api/u5/s3p34-remaining-rally-review/image/{self.item['source_frame']}").status_code, 200)
        source = {'expected_revision': 0, 'reviewer_code': 'MZ',
                  'candidate_boxes_shown_before_source': True,
                  'checked_source_frame': True, 'rows': [
                      {'jersey': jersey, 'identity_status': 'sequence_consistent',
                       'ground_status': 'airborne' if jersey == '15' else 'grounded',
                       'shoe_x_px': None, 'shoe_y_px': None, 'note': ''}
                      for jersey in pilot_review.S3P34_JERSEYS]}
        invalid = dict(source, checked_source_frame=False)
        self.assertEqual(self.client.put(self.base + '/source', json=invalid).status_code, 422)
        self.assertEqual(self.client.put(self.base + '/source', json=source).status_code, 200)
        self.assertTrue(self.client.get('/api/u5/s3p34-remaining-rally-review').json()[
            'draft']['frames'][str(self.item['source_frame'])]['candidate_boxes_shown_before_source'])
        paired = {'expected_revision': 1, 'checked_source_and_boxes': True,
                  'rows': [{'jersey': jersey,
                            'candidate_alignment': 'no_box' if box is None else 'same_player',
                            'floor_alignment': 'not_applicable' if box is None or jersey == '15' else 'plausible',
                            'note': ''}
                           for jersey, box in self.item['numbered_boxes'].items()]}
        self.assertEqual(self.client.put(self.base + '/paired', json=paired).status_code, 200)
        response = self.client.post('/api/u5/s3p34-remaining-rally-review/export')
        self.assertEqual(response.status_code, 200, response.text)
        with (self.pack / 'completed.csv').open(newline='', encoding='utf-8') as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 6)
        self.assertEqual(next(r for r in rows if r['jersey'] == '15')['candidate_alignment'], 'no_box')
        self.assertEqual(self.client.post('/api/u5/s3p34-remaining-rally-review/export').status_code, 409)

    def test_focused_export_uses_selected_frames(self):
        state = self.client.get('/api/u5/s3p34-remaining-rally-review').json()
        self.assertEqual(state['mode'], 'focused')
        self.assertEqual(len(state['frames']), 1)
        self.assertEqual(len(self.client.get('/api/u5/s3p34-remaining-rally-review?mode=full').json()['frames']), 1)
        self.assertEqual(self.client.post('/api/u5/s3p34-remaining-rally-review/export-focused').status_code, 409)

    def test_grounded_shoe_clicks_with_airborne_player_save(self):
        marks = {'28': (578.8, 426.3), '15': (678.3, 337.3),
                 '7': (752.6, 335.9), '19': (825.4, 379.8),
                 '21': (601.1, 346.2)}
        body = {'expected_revision': 0, 'reviewer_code': '',
                'checked_source_frame': True, 'rows': [
                    {'jersey': jersey, 'identity_status': 'digit_confirmed' if jersey in ('28', '12', '15') else 'sequence_consistent',
                     'ground_status': 'airborne' if jersey == '12' else 'grounded',
                     'shoe_x_px': marks.get(jersey, (None, None))[0],
                     'shoe_y_px': marks.get(jersey, (None, None))[1], 'note': ''}
                    for jersey in pilot_review.S3P34_JERSEYS]}
        response = self.client.put(self.base + '/source', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['draft']['reviewer_code'], 'MZ')


if __name__ == '__main__':
    unittest.main()
