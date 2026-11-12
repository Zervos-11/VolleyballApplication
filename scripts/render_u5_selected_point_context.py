"""Render source-score and play context for the frozen score-only sample."""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14'
VIDEO = BASE / 'source_720p.mp4'
MANIFEST = BASE / 'primary_source_manifest.json'
REGISTER = BASE / 'screening/point_register_candidate.json'
SAMPLE = BASE / 'screening/rally_sample_score_only.json'
OUT = BASE / 'screening/selected_point_review'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def frame_at(cap, second):
    number = second * 30
    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
    ok, image = cap.read()
    if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != number + 1:
        raise RuntimeError(f'Cannot decode frame {number}')
    return image


def label(image, value, x, y, scale=.5):
    cv2.putText(image, value, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (20, 20, 20), 1, cv2.LINE_AA)


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if digest(VIDEO) != manifest['video']['sha256']:
        raise ValueError('Video differs from manifest')
    register = json.loads(REGISTER.read_text(encoding='utf-8'))
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    if sample['point_register_sha256'] != digest(REGISTER):
        raise ValueError('Frozen sample differs from score register')
    events = register['events']
    by_point = {(e['set'], e['point_number']): i for i, e in enumerate(events)}
    cap = cv2.VideoCapture(str(VIDEO))
    OUT.mkdir(exist_ok=True)
    record = []
    try:
        for set_number in (1, 2, 3):
            chosen = [e for e in sample['selected_events'] if e['set'] == set_number]
            context = np.full((6 * 220, 1280, 3), 245, np.uint8)
            scores = np.full((6 * 120, 850, 3), 245, np.uint8)
            for row, event in enumerate(chosen):
                idx = by_point[(set_number, event['point_number'])]
                before = events[idx - 1]['score_change_first_sample_second'] if idx and events[idx - 1]['set'] == set_number else 0
                after = event['score_change_first_sample_second']
                gap = after - before
                picks = sorted(set((before + max(1, gap // 5), before + max(1, gap // 2),
                                    max(before + 1, after - 2), after + 1)))
                while len(picks) < 4:
                    picks.append(picks[-1])
                title = (f"S{set_number} P{event['point_number']} "
                         f"{event['score_before'][0]}-{event['score_before'][1]} to "
                         f"{event['score_after'][0]}-{event['score_after'][1]} "
                         f"winner {event['winner_scoreboard_side']}")
                label(context, title, 5, row * 220 + 19, .55)
                for col, second in enumerate(picks[:4]):
                    image = frame_at(cap, second)
                    context[row * 220 + 26:row * 220 + 206, col * 320:(col + 1) * 320] = \
                        cv2.resize(image, (320, 180), interpolation=cv2.INTER_AREA)
                    label(context, f'{second}s', col * 320 + 4, row * 220 + 218, .45)
                for col, second in enumerate((after - 1, after)):
                    image = frame_at(cap, second)
                    crop = image[0:45, 390:800]
                    scores[row * 120 + 25:row * 120 + 115, col * 425 + 5:col * 425 + 415] = \
                        cv2.resize(crop, (410, 90), interpolation=cv2.INTER_NEAREST)
                    label(scores, f'{title} | {second}s', col * 425 + 4, row * 120 + 18, .37)
                record.append({'set': set_number, 'point_number': event['point_number'],
                               'previous_score_change_s': before, 'score_change_s': after,
                               'context_picks_s': picks[:4]})
            if not cv2.imwrite(str(OUT / f'set_{set_number}_context.jpg'), context,
                               [cv2.IMWRITE_JPEG_QUALITY, 92]):
                raise RuntimeError('Could not write context sheet')
            if not cv2.imwrite(str(OUT / f'set_{set_number}_score_pairs.jpg'), scores,
                               [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError('Could not write score sheet')
    finally:
        cap.release()
    (OUT / 'record.json').write_text(json.dumps({'source_sha256': manifest['video']['sha256'],
                                                 'sample_sha256': digest(SAMPLE),
                                                 'source_seconds': record}, indent=2) + '\n',
                                     encoding='utf-8')
    print(f'Rendered {len(record)} selected point contexts')


if __name__ == '__main__':
    main()
