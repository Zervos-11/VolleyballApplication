"""Compare source-only visual anchors with frozen AoEP boxes on six frames.

This is a development identity ledger. Approximate sampled anchors and prior
tracker exposure make it unsuitable for accuracy or IDF1 reporting.
"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'data/processed/aoep_new_source'
ANCHORS = DIR / 'visual_anchors_75180_75229.json'
RAW = DIR / 'raw_74880_75540.json'
OUT = DIR / 'visual_anchor_id_ledger.json'
MIN_IOU = .35
AMBIGUITY_MARGIN = .12


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0.0


def compare_frame(anchors, raw_rows):
    visible = [a for a in anchors if a['bbox_source_px'] is not None]
    candidates = {a['visual_player_id']: sorted(
        [{'raw_track_id': int(r['track_id']), 'iou': round(iou(a['bbox_source_px'], r['bbox']), 3)}
         for r in raw_rows if iou(a['bbox_source_px'], r['bbox']) >= MIN_IOU],
        key=lambda r: (-r['iou'], r['raw_track_id']))
        for a in visible}
    # Each detector box can explain at most one visible source anchor.
    edges = sorted(((r['iou'], a['visual_player_id'], r['raw_track_id'])
                    for a in visible for r in candidates[a['visual_player_id']]), reverse=True)
    selected = {}
    taken = set()
    for score, player_id, track_id in edges:
        if player_id not in selected and track_id not in taken:
            selected[player_id] = (track_id, score)
            taken.add(track_id)
    result = []
    for anchor in anchors:
        player_id = anchor['visual_player_id']
        options = candidates.get(player_id, [])
        chosen = selected.get(player_id)
        close_competitor = (chosen is not None and any(
            r['raw_track_id'] != chosen[0] and r['iou'] >= chosen[1] - AMBIGUITY_MARGIN
            for r in options))
        result.append({
            'visual_player_id': player_id,
            'visibility': anchor['visibility'],
            'raw_track_id_one_to_one': chosen[0] if chosen else None,
            'iou_for_navigation_only': chosen[1] if chosen else None,
            'association_status': ('out_of_frame' if anchor['bbox_source_px'] is None else
                                   'ambiguous_close_boxes' if close_competitor else
                                   'single_box_candidate' if chosen else
                                   'unresolved_no_box_over_threshold'),
            'raw_box_options': options[:4],
        })
    return result


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    anchors = json.loads(ANCHORS.read_text(encoding='utf-8'))
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    if anchors['source_sha256'] != raw['source_sha256']:
        raise ValueError('Source hash mismatch')
    frames = {frame: compare_frame(rows, raw['predictions'][frame])
              for frame, rows in anchors['frames'].items()}
    payload = {
        'status': 'sampled_development_id_ledger_not_accuracy',
        'source_sha256': raw['source_sha256'],
        'raw_sha256': sha256(RAW),
        'visual_anchors_sha256': sha256(ANCHORS),
        'thresholds': {'minimum_navigation_iou': MIN_IOU,
                       'close_box_ambiguity_iou_margin': AMBIGUITY_MARGIN},
        'interpretation': 'One-to-one raw box overlap on approximate source-only development anchors. A raw ID at two sampled frames is not proof of the same person between them. Empty/ambiguous associations are review targets, not detector accuracy counts.',
        'frames': frames,
    }
    OUT.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    for frame, rows in frames.items():
        print(frame, [(r['visual_player_id'], r['raw_track_id_one_to_one'],
                       r['association_status']) for r in rows])


if __name__ == '__main__':
    main()
