"""Make a versioned R2 draft for two source-visible, floor-unknown players."""
import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
ORIGINAL = ROOT / 'data/matches/yt_FqE5pTJqx8g/pilot/player_annotations/r2.json'
SCREEN = ROOT / 'data/processed/honours_r2_saved_label_source_screen.json'
DRAFT = ROOT / 'data/processed/honours_r2_visibility_draft.json'
MANIFEST = ROOT / 'data/processed/honours_r2_visibility_draft_manifest.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source, original, screen = read(SOURCE), read(ORIGINAL), read(SCREEN)
    if source['sha256'] != screen['source_sha256']:
        raise ValueError('Source screen does not match current video')
    draft = copy.deepcopy(original)
    changes = []
    for frame, player_id, observation in (
        (78500, '42', 'UTS #22 is visible in the source frame, but the saved upper-body box gives no reliable floor point.'),
        (78521, '7', 'The saved short box is in a crowded visible area; out-of-frame is unsupported and the floor point remains unknown.'),
    ):
        saved = next(p for p in original['frames'][str(frame)]['players'] if p['player_id'] == player_id)
        target = next(p for p in draft['frames'][str(frame)]['players'] if p['player_id'] == player_id)
        if saved['position_status'] != 'out_of_frame' or saved['footpoint'] is not None:
            raise ValueError(f'Unexpected original state for frame {frame} slot {player_id}')
        target['position_status'] = 'uncertain'
        target['occlusion'] = 'partial'
        target['notes'] = observation
        changes.append({'frame': frame, 'player_id': player_id,
                        'old_position_status': saved['position_status'],
                        'new_position_status': target['position_status'],
                        'old_occlusion': saved['occlusion'],
                        'new_occlusion': target['occlusion'],
                        'footpoint_px': None, 'reason': observation})
    if any(row.get('review_status') != 'unreviewed' for row in draft['frames'].values()):
        raise ValueError('Draft must not promote unscreened annotation frames')
    DRAFT.write_text(json.dumps(draft, indent=2) + '\n', encoding='utf-8')
    manifest = {'status': 'source_screened_visibility_correction_draft_not_metric_input',
                'source_sha256': source['sha256'],
                'original_annotations_sha256': sha(ORIGINAL),
                'source_screen_sha256': sha(SCREEN),
                'draft_file': str(DRAFT.relative_to(ROOT)),
                'draft_sha256': sha(DRAFT),
                'changes': changes,
                'review_status': 'all_12_frames_still_unreviewed',
                'floor_points_added': 0,
                'use_for_final_metrics': False}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {DRAFT.relative_to(ROOT)} and {MANIFEST.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
