"""Use the trialled VideoMAE model to propose live frames in saved sample slots."""
import json
from pathlib import Path

import cv2
import torch
from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor

from trial_external_game_state_model import (MODEL, ROOT, SOURCE, decode_clip,
                                             frame_indices, read, sha)


AUDIT = ROOT / 'data/processed/honours_completed_sample_audit.json'
TRIAL = ROOT / 'data/processed/honours_external_game_state_trial.json'
OUT = ROOT / 'data/processed/honours_saved_game_state_scan.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_SAVED_GAME_STATE_SCAN.md'


def main():
    source, audit, trial = read(SOURCE), read(AUDIT), read(TRIAL)
    if source['sha256'] != audit['source_sha256'] or source['sha256'] != trial['source_sha256']:
        raise ValueError('The source-bound inputs disagree')
    if trial['model_weights_sha256'] != sha(MODEL / 'model.safetensors'):
        raise ValueError('Model weights differ from the transfer trial')
    checked = {r['candidate_frame']: r for r in trial['rows']}
    previous = read(OUT) if OUT.exists() else None
    cached = ({r['frame']: r for r in previous['rows']}
              if previous and previous.get('source_sha256') == source['sha256']
              and previous.get('model_weights_sha256') == trial['model_weights_sha256']
              and previous.get('completed_audit_sha256') == sha(AUDIT) else {})
    processor = VideoMAEImageProcessor.from_pretrained(str(MODEL), local_files_only=True)
    model = VideoMAEForVideoClassification.from_pretrained(str(MODEL), local_files_only=True)
    model.eval()
    torch.set_num_threads(4)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    rows = []
    try:
        for point in audit['points']:
            for frame in point['frame_rows']:
                center = frame['frame']
                if center in checked:
                    pred = checked[center]
                    probabilities = pred['probabilities']
                    predicted = pred['predicted_class']
                    reference_phase = pred['reference_phase']
                elif center in cached:
                    pred = cached[center]
                    probabilities = pred['model_probabilities']
                    predicted = pred['model_class']
                    reference_phase = None
                else:
                    inputs = processor(decode_clip(cap, frame_indices(center)),
                                       return_tensors='pt')
                    with torch.inference_mode():
                        probs = torch.softmax(model(**inputs).logits[0], dim=-1)
                    probabilities = {model.config.id2label[i]: round(float(v), 6)
                                     for i, v in enumerate(probs)}
                    predicted = max(probabilities, key=probabilities.get)
                    reference_phase = None
                if reference_phase == 'live_play':
                    navigation_play = True
                    navigation_basis = 'source_review'
                elif reference_phase in ('pre_serve', 'between_points'):
                    navigation_play = False
                    navigation_basis = 'source_review'
                elif reference_phase == 'uncertain_end_phase':
                    navigation_play = None
                    navigation_basis = 'source_review_uncertain'
                else:
                    navigation_play = predicted == 'play'
                    navigation_basis = 'model_proposal'
                rows.append({'set': point['set'], 'point_number': point['point_number'],
                             'winner': point['winner'], 'frame': center,
                             'model_class': predicted,
                             'model_probabilities': probabilities,
                             'source_review_phase': reference_phase,
                             'navigation_play': navigation_play,
                             'navigation_basis': navigation_basis,
                             'six_visible_contacts': frame['six_visible_contacts'],
                             'six_nominal_in_court': frame['projection_in_court'],
                             'team_fields_consistent_with_provisional_map':
                                 frame['team_ids_consistent_with_provisional_side_map']})
                print(f'{len(rows)}/61 {center}: {predicted}', flush=True)
    finally:
        cap.release()
    if len(rows) != audit['summary']['saved_frames']:
        raise ValueError('Scan omitted a saved frame')
    by_point = []
    for point in audit['points']:
        group = [r for r in rows if r['set'] == point['set'] and r['point_number'] == point['point_number']]
        play = [r for r in group if r['model_class'] == 'play']
        navigation = [r for r in group if r['navigation_play']]
        by_point.append({'set': point['set'], 'point_number': point['point_number'],
                         'winner': point['winner'], 'saved_frames': len(group),
                         'model_play_frames': len(play),
                         'play_frame_indices': [r['frame'] for r in play],
                         'play_frames_with_six_visible_contacts': sum(r['six_visible_contacts'] for r in play),
                         'play_frames_with_six_nominal_in_court': sum(r['six_nominal_in_court'] for r in play)})
        by_point[-1]['source_or_model_navigation_frames'] = len(navigation)
        by_point[-1]['source_or_model_navigation_indices'] = [r['frame'] for r in navigation]
    result = {'status': 'unreviewed_game_state_navigation_proposals',
              'source_sha256': source['sha256'], 'completed_audit_sha256': sha(AUDIT),
              'transfer_trial_sha256': sha(TRIAL),
              'model_weights_sha256': trial['model_weights_sha256'],
              'scan_frames': len(rows), 'model_play_frames': sum(r['model_class'] == 'play' for r in rows),
              'points_with_model_play_frame': sum(p['model_play_frames'] > 0 for p in by_point),
              'points_with_source_or_model_navigation_frame': sum(
                  p['source_or_model_navigation_frames'] > 0 for p in by_point),
              'by_point': by_point, 'rows': rows,
              'limitations': ['Only 13 instants have independent source-phase judgments; other model outputs are proposals.',
                              'The 11/12 transfer agreement is not a full-match accuracy estimate.',
                              'Model play classification does not supply player identities, shoe-floor points or correct court projection.',
                              'Do not use model predictions as final metric eligibility without source review.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(f"| {p['set']} | {p['point_number']} | {p['winner']} | "
                      f"{p['model_play_frames']}/{p['saved_frames']} | "
                      f"{p['play_frames_with_six_visible_contacts']} | "
                      f"{p['play_frames_with_six_nominal_in_court']} |"
                      for p in by_point)
    REPORT.write_text(f'''# Model-assisted phase navigation in the saved sample

After the [small source-reviewed transfer trial](HONOURS_EXTERNAL_GAME_STATE_TRIAL.md), the same model classified a centred one-second clip at each of the {len(rows)} saved frame positions. The [source-bound scan](../data/processed/honours_saved_game_state_scan.json) retains the predictions, probabilities, hashes and existing position-availability flags. It does not change the user's annotations.

The model marked **{result['model_play_frames']}/{len(rows)}** saved positions as play, spanning **{result['points_with_model_play_frame']}/18** sampled points. Combining these *proposals* with the existing source-reviewed phase judgments yields at least one navigation candidate in **{result['points_with_source_or_model_navigation_frame']}/18** points. The 13 source-reviewed candidate instants retain their human judgments regardless of model output; in particular, the model calls live frame 36366 `service`.

| Set | Point | Winner | Model play / saved frames | Model play with six visible feet | Model play with six nominal in-court feet |
| ---: | ---: | --- | ---: | ---: | ---: |
{table}

For each missing outcome group, the table separates a *phase problem* from a *position-availability problem*. A model play prediction alone does not create the six checked shoe-floor points needed for court metrics. Before adding frames to the analysis, source-check the phase and identities and inspect the feet; preserve all 18 frozen points and report exclusions.
''', encoding='utf-8')
    print('model play', result['model_play_frames'], 'points', result['points_with_model_play_frame'])


if __name__ == '__main__':
    main()
