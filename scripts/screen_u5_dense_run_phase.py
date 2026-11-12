"""Suggest phase at each U5 longest stable raw-ID run using local VideoMAE.

This is a navigation screen only. Predictions do not replace source review.
"""
import hashlib
import json
from pathlib import Path

import cv2
import torch
from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor

from trial_external_game_state_model import decode_clip, frame_indices


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
AUDIT = BASE / 'screening/dense_live_continuity_audit.json'
MODEL = ROOT / 'external_sources/volleyball-game-state'
OUT = BASE / 'screening/dense_run_phase_screen.json'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    processor = VideoMAEImageProcessor.from_pretrained(str(MODEL), local_files_only=True)
    model = VideoMAEForVideoClassification.from_pretrained(str(MODEL), local_files_only=True)
    model.eval()
    torch.set_num_threads(4)
    cap = cv2.VideoCapture(str(VIDEO))
    rows = []
    try:
        for point in audit['points']:
            run = point['longest_consecutive_exact_six_same_raw_ids']
            center = (run['first_frame'] + run['last_frame']) // 2
            indices = frame_indices(center)
            inputs = processor(decode_clip(cap, indices), return_tensors='pt')
            with torch.inference_mode():
                probabilities = torch.softmax(model(**inputs).logits[0], dim=-1)
            probs = {model.config.id2label[i]: round(float(v), 6)
                     for i, v in enumerate(probabilities)}
            rows.append({'set': point['set'], 'point_number': point['point_number'],
                         'run_center_frame': center, 'clip_frame_indices': indices,
                         'run_length_sampled_frames': run['frames'],
                         'predicted_class': max(probs, key=probs.get),
                         'probabilities': probs})
            print(f"S{point['set']} P{point['point_number']}: {rows[-1]['predicted_class']}",
                  flush=True)
    finally:
        cap.release()
    OUT.write_text(json.dumps({
        'status': 'model_phase_suggestions_not_source_reviewed',
        'source_sha256': digest(VIDEO), 'continuity_audit_sha256': digest(AUDIT),
        'model_weights_sha256': digest(MODEL / 'model.safetensors'),
        'method': 'VideoMAE 16 frames over 1-second centred clip, same preprocessing as prior transfer trial',
        'rows': rows,
        'limitations': ['Model was not validated on this source.',
                        'A clip can straddle a serve or dead ball.',
                        'Predictions do not validate six near players or ground positions.']
    }, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
