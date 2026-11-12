"""Join frozen source-only S1 P6 marks to exact-frame detector candidates."""

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review'
MANIFEST = PACK / 'manifest.json'
SOURCE = PACK / 'completed.csv'
CANDIDATES = PACK / 'exact_30fps_candidates.json'
OUT = PACK / 'joined_diagnostic.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S1P6_FIXED_WINDOW_SOURCE_RESULT.md'
PAIR_ALERT_PX = 60.0  # Diagnostic alert, not an accuracy or metric approval threshold.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    candidates = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    with SOURCE.open(newline='', encoding='utf-8') as stream:
        marks = list(csv.DictReader(stream))
    frames = manifest['five_sample_frames']
    assert len(marks) == 30
    assert [int(row['source_frame']) for row in marks] == [frame for frame in frames for _ in range(6)]
    assert [int(row['slot']) for row in marks] == list(range(1, 7)) * 5
    assert candidates['input_sha256']['source_review'] == sha(SOURCE)
    by_frame = {row['source_frame']: row for row in candidates['rows']}
    assert len(by_frame) == 25 and set(frames).issubset(by_frame)
    review = []
    all_distances = []
    for index, frame in enumerate(frames):
        image = manifest['images'][index]
        assert image['source_frame'] == frame and sha(PACK / image['image']) == image['sha256']
        source_rows = marks[index * 6:(index + 1) * 6]
        assert all(row['image_sha256'] == image['sha256'] for row in source_rows)
        frame_row = by_frame[frame]
        detections = frame_row['detections']
        geometric_near_count = sum(bool(d['near_floor_side_candidate']) for d in detections)
        grounded = [row for row in source_rows if row['ground_status'] == 'grounded']
        assert all(row['source_phase'] == source_rows[0]['source_phase'] for row in source_rows)
        for row in grounded:
            assert row['shoe_x_px'] and row['shoe_y_px']
        if grounded and detections:
            costs = [[math.dist((float(row['shoe_x_px']), float(row['shoe_y_px'])),
                                ((det['bbox_px'][0] + det['bbox_px'][2]) / 2,
                                 det['bbox_px'][3])) for det in detections]
                     for row in grounded]
            # Private dummy columns allow a source player to remain unmatched.
            padded = [row + [PAIR_ALERT_PX] * len(grounded) for row in costs]
            indices, proposals = linear_sum_assignment(padded)
            pairings = []
            unmatched = []
            for source_index, proposal_index in zip(indices, proposals):
                mark = grounded[source_index]
                if proposal_index >= len(detections) or costs[source_index][proposal_index] >= PAIR_ALERT_PX:
                    unmatched.append(int(mark['slot']))
                    continue
                det = detections[proposal_index]
                distance = costs[source_index][proposal_index]
                all_distances.append(distance)
                pairings.append({'slot': int(mark['slot']),
                                 'raw_track_id': det['raw_track_id'],
                                 'passes_geometric_near_gate': det['near_floor_side_candidate'],
                                 'shoe_to_box_bottom_px': round(distance, 2),
                                 'bbox_px': det['bbox_px'],
                                 'shoe_px': [float(mark['shoe_x_px']), float(mark['shoe_y_px'])],
                                 'pairing_status': 'proximity_candidate_pending_visual_check'})
        else:
            pairings = []
            unmatched = [int(row['slot']) for row in grounded]
        review.append({'source_frame': frame,
                       'source_phase': source_rows[0]['source_phase'],
                       'ground_status_counts': dict(Counter(row['ground_status'] for row in source_rows)),
                       'geometric_near_candidate_count': geometric_near_count,
                       'all_person_box_count': len(detections),
                       'all_six_grounded_source': len(grounded) == 6,
                       'all_six_grounded_and_six_or_more_candidates': len(grounded) == 6 and geometric_near_count >= 6,
                       'matched_grounded_slots': len(pairings),
                       'unmatched_grounded_slots': sorted(unmatched),
                       'all_six_grounded_and_proximity_pairs': len(grounded) == 6 and len(pairings) == 6,
                       'pairings': sorted(pairings, key=lambda item: item['slot'])})
    result = {'status': 'source_review_joined_to_algorithmic_candidates_not_visual_pair_approval',
              'input_sha256': {'manifest': sha(MANIFEST), 'completed_source_review': sha(SOURCE),
                               'exact_30fps_candidates': sha(CANDIDATES)},
              'source_review_slots': 30,
              'grounded_slots': sum(row['ground_status_counts'].get('grounded', 0) for row in review),
              'airborne_slots': sum(row['ground_status_counts'].get('airborne', 0) for row in review),
              'source_complete_six_grounded_frames': sum(row['all_six_grounded_source'] for row in review),
              'frames_with_six_grounded_and_six_or_more_candidates': sum(
                  row['all_six_grounded_and_six_or_more_candidates'] for row in review),
              'diagnostic_pair_alert_px': PAIR_ALERT_PX,
              'proximity_candidate_pairs': len(all_distances),
              'unmatched_grounded_slots': sum(len(row['unmatched_grounded_slots']) for row in review),
              'frames_with_six_grounded_and_proximity_pairs': sum(row['all_six_grounded_and_proximity_pairs'] for row in review),
              'nearest_unique_pairing_pixel_distance_median': round(statistics.median(all_distances), 2),
              'nearest_unique_pairing_pixel_distance_maximum': round(max(all_distances), 2),
              'strict_metric_approval': False,
              'rows': review,
              'limitations': ['Candidate boxes have not been visually paired to source player slots.',
                              'The original staged court calibration did not pass its frozen operational screen.',
                              'The final sampled frame has airborne near-side players and null floor positions.',
                              'This is one technical window, not an outcome association.']}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text('\n'.join([
        '# S1 P6 fixed-window source review and exact-frame candidate screen', '',
        'The [frozen source-only window](HONOURS_U5_SOURCE_ONLY_FIXED_WINDOWS.md) covers frames '
        '1759–1783, with planned samples 1759, 1765, 1771, 1777 and 1783. The '
        '[five-frame source form](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/completed.csv) '
        'is hash-bound to unboxed frames and was completed by one reviewer who had seen earlier '
        'tracker work. All five frames were marked live and all 30 slots sequence-consistent. '
        f'The reviewer marked {result["grounded_slots"]}/30 grounded and '
        f'{result["airborne_slots"]}/30 airborne; all grounded slots have clicked shoe points.', '',
        'The frozen 25-frame interval was retained. Four planned frames have six source-reviewed '
        'grounded players; frame 1783 has two airborne near-side players and no six-grounded-team '
        'metric under the current rule. The exact-frame 30-fps detector pass returned geometric '
        'near-candidate counts of **6, 7, 7, 7 and 5** on the five planned samples. A count above '
        'six is ambiguous; five is incomplete. These counts are not named player identities.', '',
        f'A one-to-one assignment with a {PAIR_ALERT_PX:g} px diagnostic alert found '
        f'**{result["proximity_candidate_pairs"]}/28** grounded-slot proximity candidates, '
        f'with median shoe-click to box-bottom separation '
        f'**{result["nearest_unique_pairing_pixel_distance_median"]} px** and maximum '
        f'**{result["nearest_unique_pairing_pixel_distance_maximum"]} px** among paired slots. '
        'At frame 1759, source slot 2 has a shoe click at (581.5, 331.2) px. Detector '
        'raw ID 13 is nearby but its box bottom is at row 304, above the crude row-313 '
        'near-side gate. The earlier join excluded this box and forced two false pairings '
        '(246 and 301 px). This is a **geometric gate miss**, not evidence that the '
        'detector omitted that player. The six gated boxes at 1759 still do **not** '
        'represent six reviewed players. Across all detector person boxes, '
        f'**{result["frames_with_six_grounded_and_proximity_pairs"]}/5** planned frames have six '
        'grounded source slots with six nearby box candidates. Proximity is an alert screen, '
        'not a human identity or floor-position verdict. The '
        '[joined diagnostic](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/joined_diagnostic.json) '
        'keeps every slot, box, and distance.', '',
        '**Strict status: zero approved metric frames.** The original staged court transform '
        'missed its frozen operational screen narrowly, the refined transform is post-review '
        'exploratory, and the final planned frame has airborne players. A later '
        '[paired visual result](HONOURS_U5_S1P6_PAIRED_REVIEW_RESULT.md) records the '
        'reviewer box decisions separately. This source review is a bounded technical '
        'check, not a winner-effect estimate.', '',
        'The [paired visual review](http://127.0.0.1:8041/s1p6-paired-review) shows the '
        'frozen source clicks alongside the exact-frame detector boxes. Its verdicts are '
        'stored separately from the source-only annotations; the calibration screen remains '
        'unapproved even if box pairings are confirmed.', '',
        'Reproduce with `.\\.venv\\Scripts\\python.exe scripts/audit_u5_s1p6_fixed_window_review.py`.',
    ]) + '\n', encoding='utf-8')
    print(result['grounded_slots'], result['airborne_slots'], result['frames_with_six_grounded_and_six_or_more_candidates'])


if __name__ == '__main__':
    main()
