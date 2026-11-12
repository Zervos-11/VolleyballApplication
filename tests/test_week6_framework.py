import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.annotation_qc import run_checks
from scripts.sample_rallies import sample
from scripts.visualize_samples import process_match


class AnnotationChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / 'test_match'
        self.directory.mkdir()
        (self.directory / 'video.mp4').touch()
        self.camera = dict(width=640, height=360, fps=30, frame_count=300, file='video.mp4')
        self.meta = dict(match_id='test_match', camera=dict(width=640, height=360, fps=30),
                         rallies=[dict(rally_id='r1', t_start=0, t_end=10)])
        (self.directory / 'homography.json').write_text(json.dumps(dict(
            points_px=[[0, 0], [640, 0], [640, 360], [0, 360]],
            points_court_m=[[0, 0], [9, 0], [9, 9], [0, 9]], image_size=[640, 360])))
        self.row = dict(match_id='test_match', rally_id='r1', frame_index='30', time_s='1',
                        object_type='player', id_type='player_id', id='home_p01',
                        x1='20', y1='10', x2='100', y2='200', confidence='', occlusion='none',
                        team_id='home', foot_x_px='60', foot_y_px='198', position_status='visible',
                        annotation_source='manual', annotator_id='ann1', review_status='reviewed',
                        reviewer_id='ann2')

    def check(self, rows=None):
        (self.directory / 'metadata.json').write_text(json.dumps(self.meta))
        path = self.directory / 'labels.csv'
        with path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.row))
            writer.writeheader()
            writer.writerows(rows if rows is not None else [self.row])
        with patch('scripts.annotation_qc.probe_video', return_value=self.camera):
            return run_checks(self.directory, path)

    def test_valid_structure_is_not_accuracy_certification(self):
        report = self.check()
        self.assertEqual(report['errors'], 0, report['issues'])
        self.assertEqual(report['review_provenance_rows'], 1)
        self.assertEqual(report['visual_accuracy'], 'not_assessed')
        self.assertNotEqual(report['release_status'], 'approved')

    def test_measured_video_overrides_incorrect_metadata(self):
        self.meta['camera']['width'] = 1920
        self.row['x2'] = '900'
        counts = self.check()['issue_counts']
        self.assertIn('camera_metadata_mismatch', counts)
        self.assertIn('bbox_out_of_bounds', counts)

    def test_unknown_rally_and_wrong_timestamp(self):
        self.row.update(rally_id='R1', time_s='1.2')
        counts = self.check()['issue_counts']
        self.assertIn('unknown_rally_id', counts)
        self.assertIn('timestamp_frame_mismatch', counts)

    def test_end_exclusive_and_video_bounds(self):
        self.row.update(frame_index='300', time_s='10')
        counts = self.check()['issue_counts']
        self.assertIn('frame_out_of_bounds', counts)
        self.assertIn('frame_outside_rally', counts)

    def test_nan_is_rejected(self):
        self.row['foot_x_px'] = 'NaN'
        self.row['confidence'] = 'NaN'
        counts = self.check()['issue_counts']
        self.assertIn('invalid_footpoint', counts)
        self.assertIn('invalid_bbox_or_confidence', counts)

    def test_duplicate_player_is_rejected(self):
        self.assertIn('duplicate_id_same_frame', self.check([self.row, self.row])['issue_counts'])

    def test_self_review_does_not_count_as_independent(self):
        self.row['reviewer_id'] = 'ann1'
        report = self.check()
        self.assertEqual(report['review_provenance_rows'], 0)
        self.assertIn('not_independently_reviewed', report['issue_counts'])

    def test_full_occlusion_has_no_invented_coordinates(self):
        self.row.update(occlusion='full', position_status='occluded', foot_x_px='', foot_y_px='',
                        x1='', y1='', x2='', y2='')
        self.assertEqual(self.check()['errors'], 0)
        self.row['foot_x_px'] = '0'
        self.assertIn('unobservable_footpoint_must_be_empty', self.check()['issue_counts'])

    def test_empty_annotations_fail(self):
        self.assertIn('empty_annotations', self.check([])['issue_counts'])

    def test_missing_video_fails_and_does_not_render_blank_evidence(self):
        with (self.directory / 'annotations_pilot.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.row))
            writer.writeheader()
            writer.writerow(self.row)
        (self.directory / 'video.mp4').unlink()
        self.assertIn('video_missing_or_ambiguous', self.check()['issue_counts'])
        output = self.directory / 'visuals'
        self.assertEqual(process_match('test_match', self.directory, 1, output), 0)
        self.assertFalse(output.exists())


class SamplingChecks(unittest.TestCase):
    def candidates(self):
        return [dict(match_id='m1', rally_id=f'r{i}', start_frame=str(i * 100),
                     end_frame_exclusive=str(i * 100 + 90), eligible='true',
                     dataset_stage='main', split='development', stratum='early' if i < 4 else 'late')
                for i in range(8)]

    def test_reproducible_balanced_sample_and_inclusion_probabilities(self):
        rows = self.candidates()
        result = sample(rows, 4, 42)
        chosen = {r['rally_id'] for r in result if r['selected'] == 'true'}
        reversed_result = sample(list(reversed(rows)), 4, 42)
        self.assertEqual(chosen, {r['rally_id'] for r in reversed_result if r['selected'] == 'true'})
        self.assertEqual(len(chosen), 4)
        self.assertEqual(sum(r['selected'] == 'true' and r['stratum'] == 'early' for r in result), 2)
        self.assertTrue(all(float(r['selection_probability']) == 0.5 for r in result))
        self.assertNotIn('selected', rows[0])

    def test_excluded_rally_never_selected(self):
        rows = self.candidates()
        rows[0]['eligible'] = 'false'
        result = sample(rows, 10)
        self.assertEqual(result[0]['selected'], 'false')
        self.assertEqual(result[0]['selection_probability'], '0')
        self.assertEqual(sum(r['selected'] == 'true' for r in result), 7)

    def test_split_leakage_and_unrepresented_strata_rejected(self):
        rows = self.candidates()
        rows[0]['split'] = 'evaluation'
        with self.assertRaisesRegex(ValueError, 'cannot cross'):
            sample(rows)
        with self.assertRaisesRegex(ValueError, 'Merge strata'):
            sample(self.candidates(), 1)


if __name__ == '__main__':
    unittest.main()
