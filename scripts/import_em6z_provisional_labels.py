"""Save independently initialized MIL boxes as incomplete review drafts.

These frames must remain incomplete until every box and identity is corrected
against the source video. Frozen YOLO/ByteTrack predictions are never read.
"""

import json
from pathlib import Path
from urllib.request import Request, urlopen


MATCH = Path('data/matches/yt_em6zFUxfYpc')
API = 'http://127.0.0.1:8010/api/yt_em6zFUxfYpc/players'


def interpolate(first, last, frame, beginning, ending):
    ratio = (frame - first) / (last - first)
    return [round(a + (b - a) * ratio) for a, b in zip(beginning, ending)]


def main():
    existing = [MATCH / 'pilot' / 'player_annotations' / f'{name}.json'
                for name in ('cross_a', 'cross_b')]
    if any(path.exists() for path in existing):
        raise FileExistsError('Saved labels already exist; refusing to overwrite annotation work')
    for name in ('cross_a', 'cross_b'):
        positions = json.loads((MATCH / 'pilot' / f'{name}_mil_draft.json').read_text())
        for frame_string, boxes in positions.items():
            frame = int(frame_string)
            if name == 'cross_a':
                # The hitter folds forward as he lands; fixed-size MIL boxes lag.
                boxes['near_6'] = interpolate(243, 267, frame,
                                              [1368, 465, 1500, 680],
                                              [1335, 530, 1450, 745])
            else:
                # The right-side #3 moves little; MIL drifted toward #7.
                boxes['near_5'] = interpolate(754, 778, frame,
                                              [1154, 575, 1245, 803],
                                              [1168, 584, 1280, 805])
                boxes['near_6'] = interpolate(754, 778, frame,
                                              [1170, 583, 1320, 877],
                                              [1310, 605, 1465, 870])
            players = []
            for player_id, box in boxes.items():
                if box is None:
                    continue
                ambiguity = (name == 'cross_b' and player_id == 'near_2')
                players.append({
                    'player_id': player_id,
                    'team_id': 'unknown',
                    'bbox': box,
                    'occlusion': 'partial' if ambiguity else 'none',
                    'position_status': 'uncertain',
                    'footpoint': None,
                    'origin_proposal_id': None,
                    'notes': ('Identity/visible body uncertain behind teammate; verify.'
                              if ambiguity else 'Independent MIL propagation draft; verify box.'),
                })
            payload = {
                'annotator_id': 'codex_mil_draft',
                'all_players_accounted_for': False,
                'notes': 'Provisional image-tracker boxes. Verify all six players, visible-body edges, and occlusion before marking complete.',
                'players': players,
            }
            request = Request(f'{API}/{name}/frames/{frame}',
                              data=json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'},
                              method='PUT')
            with urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(f'{name} {frame}: HTTP {response.status}')
        print(f'{name}: saved {len(positions)} provisional frames')


if __name__ == '__main__':
    main()
