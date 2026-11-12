import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api import pilot_review


class PilotReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.match = self.root / 'data/matches/demo'
        (self.match / 'pilot').mkdir(parents=True)
        (self.match / 'video.mp4').write_bytes(b'x' * 100)
        (self.match / 'source_record.json').write_text(json.dumps(dict(video_file='data/matches/demo/video.mp4', frame_count=300, camera=dict(width=1920,height=1080,fps=50))))
        (self.match / 'pilot/selection.json').write_text(json.dumps(dict(rallies=[dict(rally_id='r1', start_frame=110, end_frame_exclusive=180, window_start_frame=100, window_end_frame_exclusive=200)])))
        (self.match / 'pilot/player_drafts').mkdir()
        (self.match / 'pilot/player_drafts/r1.json').write_text(json.dumps(dict(start_frame=110,end_frame_exclusive=180,frames=[dict(frame_index=110,proposals=[dict(proposal_id='p1')])])))
        for key, value in [('ROOT', self.root), ('MATCHES', self.root / 'data/matches')]:
            patcher = patch.object(pilot_review, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(pilot_review.app)
        self.payload = dict(start_frame=110, end_frame_exclusive=180, annotator_id='ann01', usable=True, notes='Checked boundaries')
        self.url = '/api/demo/rallies/r1'

    def test_saves_history_without_certifying_independent_review(self):
        result = self.client.put(self.url, json=self.payload)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['independent_review_status'], 'pending')
        self.payload['start_frame'] = 111
        self.assertEqual(self.client.put(self.url, json=self.payload).status_code, 200)
        events = [json.loads(p.read_text()) for p in (self.match / 'pilot/review_history').glob('*.json')]
        self.assertEqual(len(events), 2)
        self.assertTrue(any(e['previous'] and e['previous']['start_frame'] == 110 for e in events))
        self.assertEqual(self.client.get('/api/demo/pilot').json()['reviews']['r1']['start_frame'], 111)
        self.assertNotIn('reviews', json.loads((self.match / 'pilot/selection.json').read_text()))

    def test_invalid_intervals_and_fractional_frames_rejected(self):
        for updates in [dict(start_frame=99), dict(start_frame=180), dict(end_frame_exclusive=201), dict(start_frame=110.5), dict(start_frame=True)]:
            self.assertEqual(self.client.put(self.url, json=self.payload | updates).status_code, 422)
        self.assertFalse((self.match / 'pilot/boundary_review.json').exists())

    def test_missing_identity_and_exclusion_reason_rejected(self):
        for updates in [dict(annotator_id='  '), dict(usable=False, notes='')]:
            self.assertEqual(self.client.put(self.url, json=self.payload | updates).status_code, 422)

    def test_cross_origin_write_rejected(self):
        self.assertEqual(self.client.put(self.url, json=self.payload, headers={'Origin':'https://other.example'}).status_code, 403)

    def test_unknown_rally_and_match_rejected(self):
        self.assertEqual(self.client.put('/api/demo/rallies/r2', json=self.payload).status_code, 404)
        self.assertEqual(self.client.get('/api/unknown/pilot').status_code, 404)
        with self.assertRaises(pilot_review.HTTPException):
            pilot_review.load_match('..')

    def test_frozen_sample_draft_is_separate_and_requires_six_for_complete(self):
        primary = self.root / 'data/matches/yt_FqE5pTJqx8g'
        (primary / 'pilot').mkdir(parents=True)
        (primary / 'video.mp4').write_bytes(b'x')
        (primary / 'source_record.json').write_text(json.dumps(dict(
            sha256='source_hash', video_file='data/matches/yt_FqE5pTJqx8g/video.mp4',
            frame_count=300, camera=dict(width=1920, height=1080, fps=50))))
        (primary / 'pilot/selection.json').write_text(json.dumps(dict(rallies=[])))
        workspace = self.root / 'data/processed/honours_annotation_workspace'
        (workspace / 'drafts').mkdir(parents=True)
        sample = self.root / 'data/processed/honours_rally_sample.json'
        sample.write_text('{}')
        (workspace / 'manifest.json').write_text(json.dumps(dict(
            sample_sha256=hashlib.sha256(sample.read_bytes()).hexdigest(),
            points=[dict(rally_id='hs_s1_p2', review_source='honours_workspace')])))
        (workspace / 'drafts/hs_s1_p2.json').write_text(json.dumps(dict(
            sample_point_id='s1_p2', source_sha256='source_hash', start_frame=110,
            end_frame_exclusive=180, annotation_mode='honours_sample_unverified_detector_suggestions',
            frames=[dict(frame_index=120, proposals=[dict(proposal_id='f120_det01')])])) )
        url = '/api/yt_FqE5pTJqx8g/players/hs_s1_p2'
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get('/api/yt_FqE5pTJqx8g/players/hs_s1_p3').status_code, 404)
        payload = dict(annotator_id='ann01', all_players_accounted_for=True, players=[])
        self.assertEqual(self.client.put(url + '/frames/120', json=payload).status_code, 422)
        payload['all_players_accounted_for'] = False
        self.assertEqual(self.client.put(url + '/frames/120', json=payload).status_code, 200)
        self.assertTrue((workspace / 'player_annotations/hs_s1_p2.json').exists())
        self.assertFalse((primary / 'pilot/player_annotations/hs_s1_p2.json').exists())

    def test_frame_bounds_and_identity_header(self):
        self.assertEqual(self.client.get('/api/demo/frame/-1').status_code, 422)
        self.assertEqual(self.client.get('/api/demo/frame/300').status_code, 422)
        with patch.object(pilot_review, 'decode_frame', return_value=b'jpeg'):
            response = self.client.get('/api/demo/frame/111')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['x-frame-index'], '111')

    def test_video_supports_range_requests(self):
        response = self.client.get('/api/demo/video', headers={'Range':'bytes=0-9'})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.content), 10)

    def test_r1_case_study_files_are_read_only_and_preview_supports_range(self):
        case_study = self.root / 'data/processed/fqe_r1_boundary_recheck'
        case_study.mkdir(parents=True)
        (case_study / 'r1_six_slot_visual_candidate.json').write_text('{"rally_id":"r1"}')
        (case_study / 'r1_occlusion_display_holds.json').write_text(
            '{"status":"visual_occlusion_display_aid_not_tracking","holds":{}}')
        (case_study / 'r1_p20_body_shoe_contact_trial.json').write_text(
            '{"status":"body_box_conditioned_white_shoe_contact_cue_trial","frames":[]}')
        (case_study / 'r1_p20_foot_level_center_distance_trial.json').write_text(
            '{"status":"development_foot_level_center_distance_proxy","physical_distance_released":false}')
        (case_study / 'r1_point_summary.json').write_text(
            '{"status":"bounded_single_reviewer_development_point_summary","players":[]}')
        (case_study / 'r1_visual_candidate_preview.mp4').write_bytes(b'x' * 100)
        with patch.object(pilot_review, 'R1_CASE_STUDY', case_study):
            record = self.client.get('/api/case-studies/r1/record')
            self.assertEqual(record.status_code, 200)
            self.assertEqual(record.json()['rally_id'], 'r1')
            self.assertEqual(record.headers['cache-control'], 'no-store')
            holds = self.client.get('/api/case-studies/r1/occlusion-holds')
            self.assertEqual(holds.status_code, 200)
            self.assertEqual(holds.json()['holds'], {})
            self.assertEqual(holds.headers['cache-control'], 'no-store')
            shoes = self.client.get('/api/case-studies/r1/shoe-cues')
            self.assertEqual(shoes.status_code, 200)
            self.assertEqual(shoes.json()['frames'], [])
            self.assertEqual(shoes.headers['cache-control'], 'no-store')
            distance = self.client.get('/api/case-studies/r1/foot-centre-distance')
            self.assertEqual(distance.status_code, 200)
            self.assertFalse(distance.json()['physical_distance_released'])
            self.assertEqual(distance.headers['cache-control'], 'no-store')
            summary = self.client.get('/api/case-studies/r1/point-summary')
            self.assertEqual(summary.status_code, 200)
            self.assertEqual(summary.json()['players'], [])
            self.assertEqual(summary.headers['cache-control'], 'no-store')
            preview = self.client.get('/api/case-studies/r1/preview', headers={'Range': 'bytes=0-9'})
            self.assertEqual(preview.status_code, 206)
            self.assertEqual(len(preview.content), 10)
        with patch.object(pilot_review, 'R1_CASE_STUDY', self.root / 'missing'):
            self.assertEqual(self.client.get('/api/case-studies/r1/record').status_code, 404)
            self.assertEqual(self.client.get('/api/case-studies/r1/occlusion-holds').status_code, 404)
            self.assertEqual(self.client.get('/api/case-studies/r1/shoe-cues').status_code, 404)
            self.assertEqual(self.client.get('/api/case-studies/r1/foot-centre-distance').status_code, 404)
            self.assertEqual(self.client.get('/api/case-studies/r1/point-summary').status_code, 404)

    def test_case_study_catalog_and_aoep_map_are_read_only(self):
        catalog = self.root / 'data/processed/case_studies_catalog.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text('{"schema_version":"local_case_studies_catalog_v1","case_studies":[]}')
        aoep = self.root / 'data/processed/aoep_new_source'
        aoep.mkdir(parents=True)
        (aoep / 'candidate_court_paths_75180_75229_7e8d7ea5cd.jpg').write_bytes(b'jpeg')
        with patch.object(pilot_review, 'CASE_STUDY_CATALOG', catalog), \
             patch.object(pilot_review, 'AOEP_CASE_STUDY', aoep):
            response = self.client.get('/api/case-studies/catalog')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['schema_version'], 'local_case_studies_catalog_v1')
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertEqual(self.client.get('/api/case-studies/aoep/court-map').content, b'jpeg')
        with patch.object(pilot_review, 'CASE_STUDY_CATALOG', self.root / 'missing'):
            self.assertEqual(self.client.get('/api/case-studies/catalog').status_code, 404)

    def test_r1_net_line_comes_from_staged_calibration_manifest(self):
        url = '/api/case-studies/r1/net-line'
        self.assertEqual(self.client.get(url).status_code, 404)
        path = self.root / 'data/matches/yt_FqE5pTJqx8g/pilot/calibration/calibration_manifest.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'match_id': 'yt_FqE5pTJqx8g',
                                    'camera_segments': {'camera_r1': {
                                        'heldout_net_line_px': [175, 769, 1914, 748]}}}))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['net_line_px'], [175, 769, 1914, 748])
        self.assertFalse(response.json()['court_position_certified'])

    def test_r1_floor_contact_draft_validates_and_preserves_revisions(self):
        case_study = self.root / 'data/processed/fqe_r1_boundary_recheck'
        case_study.mkdir(parents=True)
        url = '/api/case-studies/r1/floor-review/21310/20'
        payload = dict(reviewer_id='ann01', state='grounded_contact_visible',
                       footpoint_px=[400.5, 700.0], note='Visible white shoe')
        source = {'camera': {'width': 1920, 'height': 1080}}
        with patch.object(pilot_review, 'R1_CASE_STUDY', case_study), \
                patch.object(pilot_review, 'load_match', return_value=(self.match, source, {}, self.match / 'video.mp4')):
            self.assertEqual(self.client.get('/api/case-studies/r1/floor-review').json()['records'], {})
            self.assertEqual(self.client.put(url, json=payload | {'footpoint_px': None}).status_code, 422)
            self.assertEqual(self.client.put(url, json=payload | {'footpoint_px': [1920, 700]}).status_code, 422)
            self.assertEqual(self.client.put(url, json=payload | {'state': 'airborne'}).status_code, 422)
            self.assertEqual(self.client.put(url, json=payload | {'reviewer_id': ' '}).status_code, 422)
            self.assertEqual(self.client.put(url, json=payload, headers={'Origin': 'https://other.example'}).status_code, 403)
            self.assertEqual(self.client.put('/api/case-studies/r1/floor-review/21464/20', json=payload).status_code, 422)
            self.assertEqual(self.client.put('/api/case-studies/r1/floor-review/21310/99', json=payload).status_code, 422)
            self.assertFalse((case_study / 'r1_floor_contact_review.json').exists())
            self.assertEqual(self.client.put(url, json=payload).status_code, 200)
            self.assertEqual(self.client.put(url, json=payload | {'state': 'feet_hidden', 'footpoint_px': None}).status_code, 200)
            result = self.client.get('/api/case-studies/r1/floor-review').json()
            self.assertEqual(result['records']['21310']['20']['state'], 'feet_hidden')
            self.assertIsNone(result['records']['21310']['20']['footpoint_px'])
            self.assertFalse(result['official_annotations_changed'])
            history = [json.loads(p.read_text()) for p in (case_study / 'r1_floor_contact_history').glob('*.json')]
            self.assertEqual(len(history), 2)
            self.assertTrue(any(event['previous'] and event['previous']['footpoint_px'] == [400.5, 700.0]
                                for event in history))

    def player_payload(self):
        return dict(annotator_id='ann01',all_players_accounted_for=False,notes='',players=[dict(
            player_id='near_p01',team_id='unknown',bbox=[100,100,200,300],occlusion='none',
            position_status='visible',footpoint=[150,298],origin_proposal_id='p1',notes='')])

    def test_player_save_export_and_history_preserve_unreviewed_status(self):
        payload=self.player_payload()
        url='/api/demo/players/r1/frames/110'
        self.assertEqual(self.client.put(url,json=payload).status_code,200)
        payload['players'][0]['footpoint']=[151,298]
        self.assertEqual(self.client.put(url,json=payload).status_code,200)
        state=self.client.get('/api/demo/players/r1').json()
        self.assertEqual(state['saved']['frames']['110']['review_status'],'unreviewed')
        self.assertEqual(len(list((self.match/'pilot/player_annotations/history').glob('*.json'))),2)
        export=self.client.get('/api/demo/players/r1/export.csv')
        self.assertEqual(export.status_code,200)
        self.assertIn('assisted,ann01,unreviewed',export.text)
        self.assertIn('151.0,298.0',export.text)

    def test_review_attestation_updates_export_only_for_matching_label_hash(self):
        url = '/api/demo/players/r1/frames/110'
        self.assertEqual(self.client.put(url, json=self.player_payload()).status_code, 200)
        labels = self.match / 'pilot/player_annotations/r1.json'
        reviews = self.match / 'pilot/player_annotations/reviews'
        reviews.mkdir()
        (reviews / 'r1_near.json').write_text(json.dumps({
            'status': 'reviewed', 'side': 'near', 'first_frame': 110, 'last_frame': 110,
            'reviewer_id': 'ann01', 'annotation_sha256': hashlib.sha256(labels.read_bytes()).hexdigest()}))
        reviewed = self.client.get('/api/demo/players/r1/export.csv')
        self.assertIn('assisted,ann01,reviewed,ann01', reviewed.text)
        self.assertIn('_reviewed.csv', reviewed.headers['content-disposition'])
        self.assertEqual(self.client.get('/api/demo/players/r1').json()['review_attestation']['reviewer_id'], 'ann01')
        updated = self.player_payload()
        updated['players'][0]['footpoint'] = [151, 298]
        self.assertEqual(self.client.put(url, json=updated).status_code, 200)
        stale = self.client.get('/api/demo/players/r1/export.csv')
        self.assertIn('assisted,ann01,unreviewed,', stale.text)
        self.assertIn('_unreviewed.csv', stale.headers['content-disposition'])
        self.assertIsNone(self.client.get('/api/demo/players/r1').json()['review_attestation'])

    def test_invalid_player_geometry_and_visibility_rejected(self):
        variants=[dict(bbox=[-1,0,200,300]),dict(bbox=[200,0,100,300]),dict(footpoint=None),
                  dict(footpoint=[1920,200]),dict(position_status='airborne'),dict(occlusion='full'),
                  dict(origin_proposal_id='invented')]
        for variant in variants:
            payload=self.player_payload();payload['players'][0].update(variant)
            self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,422,variant)

    def test_duplicate_players_and_extra_review_fields_rejected(self):
        payload=self.player_payload();payload['players'].append(payload['players'][0])
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,422)
        payload=self.player_payload();payload['review_status']='reviewed'
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,422)

    def test_fully_occluded_label_can_have_empty_coordinates(self):
        payload=self.player_payload();payload['players'][0].update(bbox=None,occlusion='full',position_status='occluded',footpoint=None)
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,200)

    def test_partly_visible_player_can_have_no_usable_box_without_a_floor_point(self):
        payload=self.player_payload()
        payload['players'][0].update(bbox=None,occlusion='partial',position_status='occluded',footpoint=None)
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,200)
        payload['players'][0]['footpoint']=[150, 299]
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,422)

    def test_out_of_frame_player_has_no_box_or_occlusion(self):
        payload=self.player_payload();payload['players'][0].update(bbox=None,occlusion='none',position_status='out_of_frame',footpoint=None)
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,200)
        payload['players'][0]['bbox']=[100,100,200,300]
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,422)

    def test_boundary_change_blocks_old_player_schedule_and_export(self):
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=self.player_payload()).status_code,200)
        self.client.put(self.url,json=self.payload | {'start_frame':111})
        self.assertTrue(self.client.get('/api/demo/players/r1').json()['stale'])
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=self.player_payload()).status_code,409)
        self.assertEqual(self.client.get('/api/demo/players/r1/export.csv').status_code,409)

    def test_boundary_refresh_preserves_source_only_schedule(self):
        draft_path = self.match / 'pilot/player_drafts/r1.json'
        draft = json.loads(draft_path.read_text())
        draft.update(annotation_mode='independent_manual_no_detector_proposals',
                     frames=[dict(frame_index=110, time_s=2.2, proposals=[])])
        draft_path.write_text(json.dumps(draft))
        self.assertEqual(self.client.put(self.url,json=self.payload | {'start_frame':111, 'end_frame_exclusive':115}).status_code,200)
        response = self.client.post('/api/demo/players/r1/refresh')
        self.assertEqual(response.status_code,200)
        state = response.json()
        self.assertFalse(state['stale'])
        self.assertEqual([f['frame_index'] for f in state['draft']['frames']],list(range(111,115)))
        self.assertTrue(all(f['proposals'] == [] for f in state['draft']['frames']))
        self.assertEqual(state['draft']['annotation_mode'],'independent_manual_no_detector_proposals')
        self.assertEqual(len(list((draft_path.parent/'history').glob('*.json'))),1)

    def test_independent_dense_frame_cannot_be_marked_complete_with_fewer_than_six(self):
        draft_path = self.match / 'pilot/player_drafts/r1.json'
        draft = json.loads(draft_path.read_text())
        draft.update(annotation_mode='independent_manual_no_detector_proposals',
                     frames=[dict(frame_index=110, proposals=[])])
        draft_path.write_text(json.dumps(draft))
        selection_path = self.match / 'pilot/selection.json'
        selection = json.loads(selection_path.read_text())
        selection['dense_review_window'] = dict(first_frame=110, last_frame=159)
        selection_path.write_text(json.dumps(selection))
        state = self.client.get('/api/demo/players/r1').json()
        self.assertEqual(state['dense_review_window']['first_frame'], 110)
        payload = dict(annotator_id='ann01', all_players_accounted_for=True, notes='',
                       players=[dict(player_id=f'near_p{i:02}', bbox=None, occlusion='none',
                                     position_status='out_of_frame') for i in range(1, 6)])
        url = '/api/demo/players/r1/frames/110'
        self.assertEqual(self.client.put(url, json=payload).status_code, 422)
        self.assertFalse((self.match / 'pilot/player_annotations/r1.json').exists())
        payload['players'].append(dict(player_id='near_p06', bbox=None, occlusion='none',
                                       position_status='out_of_frame'))
        self.assertEqual(self.client.put(url, json=payload).status_code, 200)
        self.assertEqual(self.client.get('/api/demo/players/r1').json()['saved']['frames']['110']['review_status'],
                         'unreviewed')

    def test_far_side_labels_are_separate_and_block_schedule_refresh(self):
        draft_path = self.match / 'pilot/player_drafts/r1.json'
        draft = json.loads(draft_path.read_text())
        draft.update(annotation_mode='independent_manual_no_detector_proposals',
                     frames=[dict(frame_index=110, proposals=[])])
        draft_path.write_text(json.dumps(draft))
        self.assertEqual(self.client.get('/api/demo/players/r1?side=far').status_code, 200)
        payload = dict(annotator_id='ann02', all_players_accounted_for=False, notes='',
                       players=[dict(player_id='far_p01', bbox=[100, 100, 200, 300],
                                     occlusion='none', position_status='uncertain')])
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110?side=far', json=payload).status_code, 200)
        self.assertEqual(self.client.get('/api/demo/players/r1').json()['saved']['frames'], {})
        far = self.client.get('/api/demo/players/r1?side=far').json()
        self.assertEqual(far['saved']['annotated_side'], 'far')
        self.assertEqual(far['saved']['frames']['110']['players'][0]['player_id'], 'far_p01')
        export = self.client.get('/api/demo/players/r1/export.csv?side=far')
        self.assertEqual(export.status_code, 200)
        self.assertIn('court_side', export.text)
        self.assertIn(',far\r\n', export.text)
        self.assertEqual(self.client.get('/api/demo/players/r1/export.csv').status_code, 404)
        self.assertEqual(self.client.post('/api/demo/players/r1/refresh').status_code, 409)

    def test_frozen_suggestions_are_optional_and_mark_exposed_frame_assisted(self):
        source_path = self.match / 'source_record.json'
        source = json.loads(source_path.read_text())
        source['sha256'] = 'source_hash'
        source_path.write_text(json.dumps(source))
        selection_path = self.match / 'pilot/selection.json'
        selection = json.loads(selection_path.read_text())
        selection['raw_prediction_sha256'] = 'raw_hash'
        selection_path.write_text(json.dumps(selection))
        folder = self.match / 'pilot/assisted_proposals'
        folder.mkdir()
        (folder / 'r1.json').write_text(json.dumps(dict(source_sha256='source_hash',
            raw_prediction_sha256='raw_hash', rally_id='r1', status='unverified_frozen_tracker_suggestions',
            frames={'110': [dict(proposal_id='raw_110_0', bbox=[100, 100, 200, 300])]})))
        state = self.client.get('/api/demo/players/r1').json()
        self.assertTrue(state['assisted_proposals_available'])
        proposals = self.client.get('/api/demo/players/r1/proposals/110').json()
        self.assertEqual(proposals['proposals'][0]['proposal_id'], 'raw_110_0')
        payload = self.player_payload()
        payload['players'][0]['origin_proposal_id'] = 'raw_110_0'
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110', json=payload).status_code, 200)
        saved = self.client.get('/api/demo/players/r1').json()['saved']['frames']['110']
        self.assertTrue(saved['proposal_displayed'])
        self.assertIn('assisted,ann01,unreviewed', self.client.get('/api/demo/players/r1/export.csv').text)
        payload['players'][0]['origin_proposal_id'] = None
        payload['proposal_displayed'] = True
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110', json=payload).status_code, 200)
        self.assertIn('assisted,ann01,unreviewed', self.client.get('/api/demo/players/r1/export.csv').text)

    def test_unscheduled_frame_and_unexplained_empty_frame_rejected(self):
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/111',json=self.player_payload()).status_code,422)
        payload=self.player_payload();payload.update(players=[],all_players_accounted_for=True)
        self.assertEqual(self.client.put('/api/demo/players/r1/frames/110',json=payload).status_code,422)

    def test_nonfinite_player_coordinates_rejected(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            pilot_review.PlayerLabel(player_id='near_p01',bbox=[0,0,float('nan'),300])

    def test_refresh_before_labelling_calls_generator(self):
        with patch.object(pilot_review,'regenerate_proposals') as regenerate:
            self.assertEqual(self.client.post('/api/demo/players/r1/refresh').status_code,200)
            regenerate.assert_called_once()
            args = regenerate.call_args.args
            self.assertEqual(args[:2], (self.match.resolve(), 'r1'))
            self.assertEqual(args[2]['start_frame'], 110)
            self.assertEqual(args[3]['end_frame_exclusive'], 180)

    def test_refresh_never_overwrites_saved_player_labels(self):
        self.client.put('/api/demo/players/r1/frames/110',json=self.player_payload())
        with patch.object(pilot_review,'regenerate_proposals') as regenerate:
            self.assertEqual(self.client.post('/api/demo/players/r1/refresh').status_code,409)
            regenerate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
