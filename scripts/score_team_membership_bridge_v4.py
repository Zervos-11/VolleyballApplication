"""Score the separate team-only jump bridge on available labels."""

import hashlib
import json
from pathlib import Path

from score_heldout_team_status import match_frame


MATCH = Path('data/matches/yt_em6zFUxfYpc')
PILOT = MATCH / 'pilot'
EVAL = Path('data/processed/heldout_crossing_eval_em6z')
BASE = Path('data/processed/pilot_tracker_evaluation/team_uncertainty_trial')
TRIAL = BASE / 'team_membership_bridge_trial_v4.json'
OUT = BASE / 'team_membership_bridge_score_v4.json'


def counts_on_boxes(labels, baseline, rescued):
    counts = {'visible_labels': 0, 'baseline_matches': 0, 'bridge_matches': 0,
              'baseline_extras': 0, 'bridge_extras': 0}
    for frame, record in labels['frames'].items():
        players = [p for p in record['players'] if p.get('bbox') is not None]
        base_boxes = baseline[frame]
        bridged = base_boxes + rescued[frame]
        bm, _, bb = match_frame(players, base_boxes)
        cm, _, cb = match_frame(players, bridged)
        counts['visible_labels'] += len(players)
        counts['baseline_matches'] += len(bm)
        counts['bridge_matches'] += len(cm)
        counts['baseline_extras'] += len(base_boxes) - len(bb)
        counts['bridge_extras'] += len(bridged) - len(cb)
    return counts


def event_counts(segment, trial, track_id, airborne_ranges, grounded_ranges):
    result = {}
    for name, ranges in (('airborne', airborne_ranges), ('grounded', grounded_ranges)):
        frames = [frame for first, last in ranges for frame in range(first, last + 1)]
        raw = sum(any(r['track_id'] == track_id for r in segment['raw_predictions'][str(f)]) for f in frames)
        base = sum(any(r['track_id'] == track_id for r in segment['court_jersey_predictions'][str(f)]) for f in frames)
        added = sum(any(r['track_id'] == track_id for r in trial['rescued'][str(f)]) for f in frames)
        result[name] = {'labelled_frames': len(frames), 'raw_track_present': raw,
                        'baseline_track_present': base, 'bridge_added': added,
                        'total_track_present_after_bridge': base + added}
    return result


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    trial = json.loads(TRIAL.read_text())
    baseline = json.loads((PILOT / 'heldout_team_filtered_predictions.json').read_text())
    windows = {}
    for name in ('cross_a', 'cross_b'):
        labels = json.loads((PILOT / 'player_annotations' / f'{name}.json').read_text())
        windows[name] = counts_on_boxes(
            labels, baseline['windows'][name]['predictions'], trial['windows'][name]['rescued'])
    events = {}
    for name, filename, label_file, track_id in (
            ('jump_150_239', 'frozen_jump_segment_150_239.json', 'jump_event_labels_150_239.json', 179),
            ('block_860_960', 'frozen_block_segment_860_960.json', 'block_event_labels_860_960.json', 96)):
        segment = json.loads((EVAL / filename).read_text())
        labels = json.loads((EVAL / label_file).read_text())
        events[name] = event_counts(segment, trial['windows'][name], track_id,
                                    labels['clearly_airborne_ranges_inclusive'],
                                    labels['clearly_grounded_ranges_inclusive'])
    OUT.write_text(json.dumps({
        'status': 'development_score',
        'trial_sha256': hashlib.sha256(TRIAL.read_bytes()).hexdigest(),
        'window_matching': 'one-to-one greedy IoU >= 0.5 on visible near-player boxes',
        'event_matching': 'source-reviewed single-player raw track ID; no boxes for all players',
        'windows': windows, 'events': events,
    }, indent=2) + '\n', encoding='utf-8')
    print(windows)
    print(events)


if __name__ == '__main__':
    main()
