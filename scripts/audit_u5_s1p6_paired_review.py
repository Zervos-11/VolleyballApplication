"""Score the frozen S1 P6 source/box comparison without promoting candidates."""

import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review'
SOURCE = PACK / 'completed.csv'
PAIRED = PACK / 'paired_completed.csv'
DETECTOR = PACK / 'exact_30fps_candidates.json'
MANIFEST = PACK / 'manifest.json'
CALIBRATION = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s3p34_calibration_review/score.json'
OUTPUT = PACK / 'paired_score.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S1P6_PAIRED_REVIEW_RESULT.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main():
    source = read_csv(SOURCE)
    paired = read_csv(PAIRED)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    detector = json.loads(DETECTOR.read_text(encoding='utf-8'))
    calibration = json.loads(CALIBRATION.read_text(encoding='utf-8'))
    frames = manifest['five_sample_frames']
    assert len(source) == len(paired) == 30
    assert [(int(row['source_frame']), int(row['slot'])) for row in source] == [
        (frame, slot) for frame in frames for slot in range(1, 7)]
    assert [(int(row['source_frame']), int(row['slot'])) for row in paired] == [
        (frame, slot) for frame in frames for slot in range(1, 7)]
    assert all(row['source_review_sha256'] == sha(SOURCE) for row in paired)
    assert all(row['detector_sha256'] == sha(DETECTOR) for row in paired)
    assert all(row['source_image_sha256'] == src['image_sha256'] for row, src in zip(paired, source))
    by_frame = {row['source_frame']: row for row in detector['rows']}
    assert set(frames).issubset(by_frame)
    rows = []
    prior_ids = {}
    for verdict in paired:
        if (int(verdict['source_frame']) != frames[-1] and
                verdict['candidate_alignment'] == 'same_player' and verdict['raw_track_id']):
            prior_ids[int(verdict['slot'])] = int(verdict['raw_track_id'])
    for src, verdict in zip(source, paired):
        frame = int(src['source_frame'])
        raw_id = int(verdict['raw_track_id']) if verdict['raw_track_id'] else None
        candidates = [det for det in by_frame[frame]['detections'] if det['raw_track_id'] == raw_id]
        assert len(candidates) == (0 if raw_id is None else 1)
        assert verdict['ground_status'] == src['ground_status']
        if verdict['candidate_alignment'] == 'no_box':
            assert raw_id is None and verdict['floor_alignment'] == 'not_applicable'
        else:
            assert raw_id is not None
        if verdict['floor_alignment'] == 'plausible':
            assert src['ground_status'] == 'grounded' and verdict['candidate_alignment'] == 'same_player'
        distance = None
        if src['ground_status'] == 'grounded' and raw_id is not None:
            box = candidates[0]['bbox_px']
            distance = math.dist((float(src['shoe_x_px']), float(src['shoe_y_px'])),
                                 ((box[0] + box[2]) / 2, box[3]))
        hidden_id = None
        if frame == frames[-1] and src['ground_status'] == 'airborne' and raw_id is None:
            candidate_id = prior_ids.get(int(src['slot']))
            candidate = next((det for det in by_frame[frame]['detections']
                              if det['raw_track_id'] == candidate_id), None)
            if candidate is not None and not candidate['near_floor_side_candidate']:
                hidden_id = candidate_id
        rows.append({'source_frame': frame, 'slot': int(src['slot']),
                     'ground_status': src['ground_status'], 'raw_track_id': raw_id,
                     'candidate_alignment': verdict['candidate_alignment'],
                     'floor_alignment': verdict['floor_alignment'],
                     'shoe_to_box_bottom_px': None if distance is None else round(distance, 2),
                     'passes_geometric_near_gate': None if raw_id is None else candidates[0]['near_floor_side_candidate'],
                     'previously_paired_id_hidden_by_page_filter': hidden_id,
                     'note': verdict['note']})
    distances = [row['shoe_to_box_bottom_px'] for row in rows if row['floor_alignment'] == 'plausible']
    frame_results = []
    for frame in frames:
        group = [row for row in rows if row['source_frame'] == frame]
        frame_results.append({'source_frame': frame,
                              'grounded_source_slots': sum(row['ground_status'] == 'grounded' for row in group),
                              'same_player_plausible_slots': sum(row['candidate_alignment'] == 'same_player' and
                                                                 row['floor_alignment'] == 'plausible' for row in group),
                              'six_plausible_grounded_slots': all(row['ground_status'] == 'grounded' and
                                                                  row['candidate_alignment'] == 'same_player' and
                                                                  row['floor_alignment'] == 'plausible' for row in group)})
    result = {'status': 'frozen_single_reviewer_paired_diagnostic',
              'input_sha256': {'source_review': sha(SOURCE), 'paired_review': sha(PAIRED),
                               'detector': sha(DETECTOR), 'manifest': sha(MANIFEST),
                               'calibration_score': sha(CALIBRATION)},
              'source_grounded_slots': sum(row['ground_status'] == 'grounded' for row in rows),
              'paired_verdict_counts': dict(Counter(row['candidate_alignment'] for row in rows)),
              'floor_verdict_counts': dict(Counter(row['floor_alignment'] for row in rows)),
              'plausible_paired_slots': len(distances),
              'airborne_no_box_verdicts_with_hidden_detector_candidates': sum(
                  row['previously_paired_id_hidden_by_page_filter'] is not None for row in rows),
              'plausible_pair_pixel_distance_median': round(statistics.median(distances), 2),
              'plausible_pair_pixel_distance_maximum': round(max(distances), 2),
              'six_plausible_grounded_sample_frames': sum(row['six_plausible_grounded_slots'] for row in frame_results),
              'calibration_operational_screen_passed': calibration['operational_screen_passed'],
              'strict_approved_metric_frames': 0,
              'strict_complete_fixed_window_result': False,
              'frame_results': frame_results, 'rows': rows,
              'limitations': ['Single reviewer previously exposed to tracker output; suggested boxes were prefilled.',
                              'The paired page hid two above-cutoff candidate boxes on the final airborne frame. Its no-box defaults there are not evidence of detector omission or verified absence.',
                              'Only five planned instants were paired by a reviewer; intervening source frames remain provisional.',
                              'The fifth planned instant includes airborne players, so the five-sample window is incomplete.',
                              'The original frozen court-calibration screen did not pass.']}
    assert result['calibration_operational_screen_passed'] is False
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text('\n'.join([
        '# S1 P6 frozen paired source and detector review', '',
        'The [frozen source-only form](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/completed.csv) '
        'and [subsequent paired form](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/paired_completed.csv) '
        'cover the same five planned frames and 30 stable player slots. The same reviewer completed both stages '
        'after prior exposure to tracker output. Suggested box IDs and floor-proxy statuses were prefilled in the '
        'paired page, and each frame required an explicit visual-check confirmation.', '',
        f'The reviewer marked **{result["source_grounded_slots"]}/30** slots grounded, '
        f'**{result["plausible_paired_slots"]}/30** as same-player boxes with plausible floor proxies, '
        'and two final-frame airborne slots as having no floor point. The paired form '
        'records “no box” for those two slots, but the page hid two above-cutoff candidate '
        'boxes carrying their earlier raw IDs. Those final-frame box-identity decisions '
        'are **unassessed**, not evidence of detector omission. '
        f'All six slots were grounded and paired in **{result["six_plausible_grounded_sample_frames"]}/5** '
        'planned frames (1759, 1765, 1771 and 1777). Across the 28 plausible pairs, the '
        f'shoe-click-to-box-bottom distance has median **{result["plausible_pair_pixel_distance_median"]} px** '
        f'and largest observed value **{result["plausible_pair_pixel_distance_maximum"]} px**. '
        'These are image-coordinate discrepancies, not independent court-position errors.', '',
        'At frame 1759, the reviewer paired source slot 2 with detector raw ID 13. This box was excluded '
        'by the crude row-313 near-side gate but is present in the detector output. The paired verdict '
        'resolves the earlier gated-box ambiguity for that sampled frame. All six paired player IDs '
        'in the first four frames are distinct and stable in the reviewed samples. Raw IDs '
        'also appear in the intervening detector frames, but those source frames have no paired human verdict.', '',
        '**Strict status at this paired-review stage: zero formally approved metric frames.** '
        'All five planned samples have six reviewed player states. The fifth has two observed '
        'airborne players with structurally null floor positions, so its six-player team metric '
        'is undefined. The original frozen '
        '[calibration operational screen](HONOURS_U5_S3P34_CALIBRATION_REVIEW.md) did not pass '
        '(maximum 0.2037 m against 0.200 m). A later '
        '[out-of-point check](HONOURS_U5_S1P6_CALIBRATION_CHECK.md) passed for the refined '
        'transform. The [calibrated sample diagnostic](HONOURS_U5_S1P6_CALIBRATED_SAMPLES.md) '
        'reports four metric-eligible sampled frames. The intervening 20 source frames lack '
        'ground-contact review; this paired review alone does not establish a continuous '
        '25-frame floor-coordinate series or an outcome effect.', '',
        'The [machine-readable score](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/paired_score.json) '
        'preserves each slot verdict and its source hashes. Reproduce with '
        '`.\\.venv\\Scripts\\python.exe scripts/audit_u5_s1p6_paired_review.py`.',
    ]) + '\n', encoding='utf-8')
    print(result['plausible_paired_slots'], result['six_plausible_grounded_sample_frames'])


if __name__ == '__main__':
    main()
