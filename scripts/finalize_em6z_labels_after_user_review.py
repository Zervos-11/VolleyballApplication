"""Apply the user's window-B team correction and complete the reviewed frames.

Window B near_2 was an opposing player. The sixth blue-team player cannot
be separately boxed in these 25 frames; retain the ID with full occlusion.
"""

import json
from pathlib import Path
from urllib.request import Request, urlopen


MATCH = Path('data/matches/yt_em6zFUxfYpc')
API = 'http://127.0.0.1:8010/api/yt_em6zFUxfYpc/players'


def main():
    for name in ('cross_a', 'cross_b'):
        path = MATCH / 'pilot' / 'player_annotations' / f'{name}.json'
        saved = json.loads(path.read_text(encoding='utf-8'))
        if len(saved['frames']) != 25:
            raise ValueError(f'{name}: expected 25 provisional frames')
        if any(frame['all_players_accounted_for'] or
               frame['annotator_id'] != 'codex_mil_draft'
               for frame in saved['frames'].values()):
            raise ValueError(f'{name}: annotations have changed; refusing to overwrite')
        for frame_index, frame in sorted(saved['frames'].items(),
                                         key=lambda pair: int(pair[0])):
            players = frame['players']
            if len(players) != 6:
                raise ValueError(f'{name} {frame_index}: expected six identities')
            if name == 'cross_b':
                mistaken = next(p for p in players if p['player_id'] == 'near_2')
                mistaken.update(bbox=None, occlusion='full',
                                position_status='occluded', footpoint=None,
                                notes='Sixth blue player not separately visible; prior box was on an opposing player.')
            payload = {
                'annotator_id': 'codex_user_confirmed',
                'all_players_accounted_for': True,
                'notes': ('User confirmed the other player boxes. Opposing player removed; '
                          'near_2 kept as fully occluded with no inferred box.'
                          if name == 'cross_b' else
                          'User confirmed the six visible player boxes.'),
                'players': players,
            }
            request = Request(f'{API}/{name}/frames/{frame_index}',
                              data=json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'},
                              method='PUT')
            with urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(f'{name} {frame_index}: HTTP {response.status}')
        print(f'{name}: saved 25 corrected complete frames')


if __name__ == '__main__':
    main()
