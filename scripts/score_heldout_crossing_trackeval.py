"""Score raw and frozen-filter ByteTrack outputs with TrackEval 1.3.0.

The six-player target annotation has no box for a fully occluded player.
DO_PREPROC=False keeps all predictions submitted by each variant, including
other teams in the raw output, so unmatched detections count against the task.
"""

import json
from pathlib import Path

import trackeval


ROOT = Path('data/processed/heldout_crossing_eval_em6z/mot_challenge').resolve()
RESULTS = ROOT / 'results'


def main():
    eval_config = trackeval.Evaluator.get_default_eval_config()
    eval_config.update(PRINT_CONFIG=False, PRINT_RESULTS=True,
                       PRINT_ONLY_COMBINED=False, PLOT_CURVES=False,
                       TIME_PROGRESS=False)
    dataset_config = trackeval.datasets.MotChallenge2DBox.get_default_dataset_config()
    dataset_config.update(
        GT_FOLDER=str(ROOT / 'gt/mot_challenge'),
        TRACKERS_FOLDER=str(ROOT / 'trackers/mot_challenge'),
        OUTPUT_FOLDER=str(RESULTS),
        TRACKERS_TO_EVAL=['bytetrack', 'bytetrack_court_filter',
                          'bytetrack_team_filter', 'bytetrack_airborne_grace'],
        BENCHMARK='VolleyHoldout', SPLIT_TO_EVAL='train',
        CLASSES_TO_EVAL=['pedestrian'],
        DO_PREPROC=False,
        PRINT_CONFIG=False,
    )
    evaluator = trackeval.Evaluator(eval_config)
    dataset = trackeval.datasets.MotChallenge2DBox(dataset_config)
    metrics = [trackeval.metrics.HOTA(), trackeval.metrics.CLEAR(),
               trackeval.metrics.Identity()]
    results, messages = evaluator.evaluate([dataset], metrics)
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary = {
        'trackeval_version': '1.3.0',
        'dataset_config': dataset_config,
        'evaluation_config': eval_config,
        'notes': ('Raw and frozen court/jersey-filtered ByteTrack predictions, '
                  'plus an exploratory airborne-grace variant, '
                  'scored against the near-court blue-team visible boxes. '
                  'Unmatched other-team predictions count as false positives. '
                  'Window B near_2 is fully occluded throughout and has no GT box.'),
        'messages': messages,
    }
    (RESULTS / 'run_config.json').write_text(json.dumps(summary, indent=2, default=str) + '\n')
    print(f'Saved TrackEval output under {RESULTS}')


if __name__ == '__main__':
    main()
