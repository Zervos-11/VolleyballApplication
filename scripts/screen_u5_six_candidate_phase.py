"""Screen one six-candidate frame per second for phase navigation on U5."""
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
TRACKS = BASE / 'screening/dense_live_track_screen.json'
MODEL = ROOT / 'external_sources/volleyball-game-state'
OUT = BASE / 'screening/six_candidate_phase_screen.json'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    processor = VideoMAEImageProcessor.from_pretrained(str(MODEL), local_files_only=True)
    model = VideoMAEForVideoClassification.from_pretrained(str(MODEL), local_files_only=True)
    model.eval()
    torch.set_num_threads(4)
    cap = cv2.VideoCapture(str(VIDEO))
    results = []
    try:
        for point in tracks['points']:
            by_second = {}
            for row in point['rows']:
                if row['near_floor_side_candidate_count'] < 6:
                    continue
                second = row['source_frame'] // 30
                prior = by_second.get(second)
                if prior is None or abs(row['source_frame'] - (second * 30 + 15)) < abs(
                        prior['source_frame'] - (second * 30 + 15)):
                    by_second[second] = row
            rows = []
            for second, source in sorted(by_second.items()):
                center = source['source_frame']
                indices = frame_indices(center)
                inputs = processor(decode_clip(cap, indices), return_tensors='pt')
                with torch.inference_mode():
                    probabilities = torch.softmax(model(**inputs).logits[0], dim=-1)
                probs = {model.config.id2label[i]: round(float(v), 6)
                         for i, v in enumerate(probabilities)}
                rows.append({'source_second': second, 'source_frame': center,
                             'six_geometric_candidate_count': source['near_floor_side_candidate_count'],
                             'predicted_class': max(probs, key=probs.get),
                             'probabilities': probs})
            results.append({'set': point['set'], 'point_number': point['point_number'],
                            'candidate_seconds': len(rows), 'rows': rows})
            print(f"S{point['set']} P{point['point_number']}: "
                  f"{sum(r['predicted_class'] == 'play' for r in rows)}/{len(rows)} play suggestions",
                  flush=True)
    finally:
        cap.release()
    OUT.write_text(json.dumps({
        'status': 'phase_navigation_suggestions_not_source_reviewed',
        'source_sha256': digest(VIDEO), 'dense_track_screen_sha256': digest(TRACKS),
        'model_weights_sha256': digest(MODEL / 'model.safetensors'),
        'selection_rule': 'one six-geometric-candidate frame closest to half second per source second',
        'results': results,
        'limitations': ['Six geometric candidates may contain opponents or duplicates.',
                        'The phase model is not validated on this source.',
                        'A one-second clip may cross play boundaries.']
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}', flush=True)


if __name__ == '__main__':
    main()
