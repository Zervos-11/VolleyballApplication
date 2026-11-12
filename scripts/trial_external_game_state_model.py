"""Evaluate the public volleyball VideoMAE weights on source-reviewed frames.

This is a local transfer trial. It does not change annotations or make model
predictions eligible as ground truth for the honours outcome analysis.
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
PHASE = ROOT / 'data/processed/honours_candidate_phase_qc.json'
MODEL = ROOT / 'external_sources/volleyball-game-state'
OUT = ROOT / 'data/processed/honours_external_game_state_trial.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_EXTERNAL_GAME_STATE_TRIAL.md'
HALF_WIDTH_FRAMES = 25
CLIP_FRAMES = 16
MODEL_REPOSITORY = 'https://github.com/masouduut94/volleyball-ml-models'
WEIGHT_URL = 'https://drive.google.com/file/d/18vtJSLIpaRHOlvXNmwvSd9stYYAEsMcK/view'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def frame_indices(center):
    return np.rint(np.linspace(center - HALF_WIDTH_FRAMES,
                              center + HALF_WIDTH_FRAMES, CLIP_FRAMES)).astype(int).tolist()


def decode_clip(cap, indices):
    frames = []
    for index in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != index + 1:
            raise RuntimeError(f'Could not decode exact frame {index}')
        # Match the repository wrapper: BGR -> RGB, then square resize.
        frames.append(cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                                 (224, 224), interpolation=cv2.INTER_LINEAR))
    return frames


def main():
    source, reference = read(SOURCE), read(PHASE)
    if reference['source_sha256'] != source['sha256']:
        raise ValueError('Reference phase labels belong to another source')
    weights = MODEL / 'model.safetensors'
    if not weights.is_file():
        raise FileNotFoundError(f'Missing public game-state weights: {weights}')
    processor = VideoMAEImageProcessor.from_pretrained(str(MODEL), local_files_only=True)
    model = VideoMAEForVideoClassification.from_pretrained(str(MODEL),
                                                           local_files_only=True)
    model.eval()
    torch.set_num_threads(4)
    cap = cv2.VideoCapture(str(ROOT / source['video_file']))
    if not cap.isOpened():
        raise RuntimeError('Source video unavailable')
    rows = []
    try:
        for item in reference['rows']:
            center = item['frame']
            indices = frame_indices(center)
            rgb_frames = decode_clip(cap, indices)
            inputs = processor(rgb_frames, return_tensors='pt')
            with torch.inference_mode():
                probabilities = torch.softmax(model(**inputs).logits[0], dim=-1)
            probs = {model.config.id2label[i]: round(float(v), 6)
                     for i, v in enumerate(probabilities)}
            predicted = max(probs, key=probs.get)
            reference_binary = None if item['phase'] == 'uncertain_end_phase' else (
                'play' if item['phase'] == 'live_play' else 'not_play')
            predicted_binary = 'play' if predicted == 'play' else 'not_play'
            rows.append({'set': item['set'], 'point_number': item['point_number'],
                         'candidate_frame': center, 'clip_frames': indices,
                         'reference_phase': item['phase'],
                         'reference_binary': reference_binary,
                         'predicted_class': predicted, 'predicted_binary': predicted_binary,
                         'probabilities': probs,
                         'binary_agreement': None if reference_binary is None
                         else predicted_binary == reference_binary})
            print(f'{len(rows)}/{len(reference["rows"])} frame {center}: {predicted} '
                  f'P(play)={probs.get("play", 0):.3f}', flush=True)
    finally:
        cap.release()
    scored = [r for r in rows if r['binary_agreement'] is not None]
    live = [r for r in scored if r['reference_binary'] == 'play']
    inactive = [r for r in scored if r['reference_binary'] == 'not_play']
    tp = sum(r['predicted_binary'] == 'play' for r in live)
    tn = sum(r['predicted_binary'] == 'not_play' for r in inactive)
    result = {'status': 'external_model_transfer_trial_not_validated_phase_automation',
              'source_sha256': source['sha256'], 'phase_reference_sha256': sha(PHASE),
              'model_repository': MODEL_REPOSITORY,
              'weights_url': WEIGHT_URL, 'model_weights_sha256': sha(weights),
              'model_config_sha256': sha(MODEL / 'config.json'),
              'processor_config_sha256': sha(MODEL / 'preprocessor_config.json'),
              'clip_definition': {'centered_half_width_frames': HALF_WIDTH_FRAMES,
                                  'source_fps': source['camera']['fps'],
                                  'uniformly_sampled_frames': CLIP_FRAMES,
                                  'image_preprocessing': 'BGR to RGB; 224x224 square resize; repository VideoMAE image processor'},
              'evaluation': {'source_reviewed_examples': len(scored),
                             'uncertain_reference_excluded': len(rows) - len(scored),
                             'live_play_recall_numerator': tp, 'live_play_recall_denominator': len(live),
                             'nonplay_specificity_numerator': tn,
                             'nonplay_specificity_denominator': len(inactive),
                             'binary_agreement_numerator': tp + tn,
                             'binary_agreement_denominator': len(scored)},
              'rows': rows,
              'limitations': ['Only 12 certain source-reviewed candidate instants are scored; these are not independent random video clips.',
                              'A one-second centred clip can straddle a serve or point end.',
                              'The pretrained model was not calibrated on this local gym broadcast.',
                              'Service and no-play are both non-play for this binary screen; neither certifies an exact rally boundary.',
                              'Predictions do not replace source phase labels, player identity or floor-contact review.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    table = '\n'.join(f"| {r['set']} | {r['point_number']} | {r['candidate_frame']} | "
                      f"{r['reference_phase']} | {r['predicted_class']} | "
                      f"{r['probabilities'].get('play', 0):.3f} |"
                      for r in rows)
    e = result['evaluation']
    REPORT.write_text(f'''# External volleyball game-state model transfer trial

The [public volleyball-ml-models repository]({MODEL_REPOSITORY}) provides a three-state VideoMAE model, with weights linked from the [project's dataset page](https://github.com/masouduut94/volleyball_analytics/wiki/Datasets-and-Weights). We downloaded only its game-state checkpoint and loaded its safetensors weights locally. The [machine-readable trial](../data/processed/honours_external_game_state_trial.json) records the source, model and reference-label hashes.

The parent project's [README data-source statement](https://github.com/masouduut94/volleyball_analytics#-data-sources) says its training and testing clips came from [Volleyball Watchdog](https://www.youtube.com/@VolleyballWatchdog/videos), featuring international matches. It does not identify the exact games or disclose a video-level train/test split for this checkpoint. Our primary recording is local gym footage, so differences in camera view, lighting, broadcast graphics and play level may affect transfer. The model therefore needs a local source-reviewed check before its predictions can be used even as phase suggestions.

Each prediction uses 16 source frames uniformly sampled over a one-second interval centred on one of the 13 previously [source-reviewed candidate instants](HONOURS_CANDIDATE_PHASE_QC.md). The uncertain end-of-play instant is listed but excluded from scoring. For the binary screen, model `play` is positive; `service` and `no-play` are non-play.

**Transfer check:** {e['binary_agreement_numerator']}/{e['binary_agreement_denominator']} agreement; live-play recall {tp}/{len(live)}; non-play specificity {tn}/{len(inactive)}. This is a small domain-transfer diagnostic, not an accuracy estimate for the full match or an independent test of the training dataset.

The disagreement is set-one point 23, frame 36366: source context shows the ball and players in continuing play, while the one-second model clip is classified `service`. The very sharp model probabilities below are not calibrated confidence estimates on this gym footage. Human source judgments take precedence in navigation and analysis.

| Set | Point | Centre frame | Source-review phase | Model class | P(play) |
| ---: | ---: | ---: | --- | --- | ---: |
{table}

The model should only propose additional live-play windows if this local transfer check is convincing. It cannot create six-player shoe positions or resolve team identity. Its output must remain separate from the source-reviewed phase record and cannot be counted as validated rally metrics without those checks.
''', encoding='utf-8')
    print(result['evaluation'])


if __name__ == '__main__':
    main()
