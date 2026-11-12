"""Post-score diagnostic of which labelled players each frozen filter removed."""

import json
from collections import defaultdict
from pathlib import Path

from evaluate_pilot_tracker import image_to_court, in_target_region, match_boxes, project


MATCH = Path('data/matches/yt_em6zFUxfYpc')
OUT = Path('data/processed/heldout_crossing_eval_em6z/filter_diagnostic.json')


def main():
    raw = json.loads((MATCH / 'pilot/heldout_tracker_predictions.json').read_text())
    court = json.loads((MATCH / 'pilot/heldout_court_filtered_predictions.json').read_text())
    team = json.loads((MATCH / 'pilot/heldout_team_filtered_predictions.json').read_text())
    calibration = json.loads((MATCH / 'pilot/calibration/near_court.json').read_text())
    matrix = image_to_court(calibration)
    rows = {}
    for name in ('cross_a', 'cross_b'):
        labels = json.loads((MATCH / 'pilot/player_annotations' / f'{name}.json').read_text())
        count = defaultdict(lambda: dict(visible=0, raw_matched=0, court_matched=0,
                                         team_matched=0, raw_match_removed_by_court=0,
                                         raw_match_removed_by_jersey=0,
                                         removed_projected_positions=[]))
        first = min(map(int, labels['frames']))
        for frame_string, annotation in labels['frames'].items():
            players = [p for p in annotation['players'] if p['bbox'] is not None]
            frame = int(frame_string)
            for player in players:
                count[player['player_id']]['visible'] += 1
            predictions = {key: source['windows'][name]['predictions'][frame_string]
                           for key, source in [('raw', raw), ('court', court), ('team', team)]}
            matches = {key: match_boxes(players, boxes)
                       for key, boxes in predictions.items()}
            for key, pairs in matches.items():
                for player_index, _, _ in pairs:
                    count[players[player_index]['player_id']][f'{key}_matched'] += 1
            raw_pairs = {i: j for i, j, _ in matches['raw']}
            # Predictions were JSON-loaded separately, so compare stable box/ID tuples.
            court_keys = {(p['track_id'], tuple(p['bbox'])) for p in predictions['court']}
            team_keys = {(p['track_id'], tuple(p['bbox'])) for p in predictions['team']}
            for player_index, pred_index in raw_pairs.items():
                player_id = players[player_index]['player_id']
                prediction = predictions['raw'][pred_index]
                key = (prediction['track_id'], tuple(prediction['bbox']))
                if key not in court_keys:
                    count[player_id]['raw_match_removed_by_court'] += 1
                    x1, _, x2, y2 = prediction['bbox']
                    xy = project([(x1 + x2) / 2, y2], matrix)
                    count[player_id]['removed_projected_positions'].append(
                        [round(float(xy[0]), 2), round(float(xy[1]), 2),
                         in_target_region(xy, frame == first)])
                elif key not in team_keys:
                    count[player_id]['raw_match_removed_by_jersey'] += 1
        rows[name] = dict(count)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2) + '\n')
    for name, players in rows.items():
        print(name)
        for player_id, value in players.items():
            print(player_id, {key: value[key] for key in ('visible', 'raw_matched',
                  'court_matched', 'team_matched', 'raw_match_removed_by_court',
                  'raw_match_removed_by_jersey')})


if __name__ == '__main__':
    main()
