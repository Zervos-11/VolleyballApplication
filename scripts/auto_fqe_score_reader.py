"""Read the fixed ProVolley broadcast score graphic from sampled video frames.

The template bank is calibrated once from one reviewed frame per displayed
score value. Inference itself reads pixels only. The reviewed state file is used
after inference solely for an in-source agreement audit; no guessed point is
silently added when the graphic is hidden.
"""
import argparse
import csv
import json
from itertools import groupby
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_FqE5pTJqx8g.mp4'
TIMES = ROOT / 'data/processed/fqe_keyframe_times.txt'
REFERENCE = ROOT / 'data/processed/fqe_score_keyframe_states.json'
SOURCE = ROOT / 'data/matches/yt_FqE5pTJqx8g/source_record.json'
PATCHES = ROOT / 'data/processed/fqe_auto_score_patches.npz'
TEMPLATES = ROOT / 'data/processed/fqe_auto_score_templates.npz'
OUTPUT = ROOT / 'data/processed/fqe_auto_score_readings.json'
TIMELINE_OUTPUT = ROOT / 'data/processed/fqe_auto_score_timeline.json'
CSV_OUTPUT = ROOT / 'data/processed/fqe_auto_score_timeline.csv'
FLIPS = ROOT / 'data/processed/fqe_score_flip_frames.json'
TOP = (93, 121, 403, 446)
BOTTOM = (133, 161, 403, 446)


def crop(frame, bounds):
    y0, y1, x0, x1 = bounds
    return frame[y0:y1, x0:x1]


def extract():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    times = np.array([float(t) for t in TIMES.read_text(encoding='utf-8').splitlines()])
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError('Cannot open analysis video')
    frames = np.rint(times * source['camera']['fps']).astype(np.int32)
    pixels = np.empty((len(frames), 2, 28, 43, 3), dtype=np.uint8)
    for i, frame_number in enumerate(frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_number))
        ok, frame = cap.read()
        if not ok or round(cap.get(cv2.CAP_PROP_POS_FRAMES)) != frame_number + 1:
            raise RuntimeError(f'Cannot decode source frame {frame_number}')
        pixels[i, 0] = crop(frame, TOP)
        pixels[i, 1] = crop(frame, BOTTOM)
        if i and i % 100 == 0:
            print(f'Decoded {i}/{len(frames)} score samples', flush=True)
    cap.release()
    np.savez_compressed(PATCHES, pixels=pixels, frames=frames, times=times,
                        source_sha256=source['sha256'])
    return pixels, frames, times, source['sha256']


def load_patches():
    if not PATCHES.exists():
        return extract()
    with np.load(PATCHES) as data:
        source = json.loads(SOURCE.read_text(encoding='utf-8'))
        if str(data['source_sha256']) != source['sha256']:
            raise RuntimeError('Cached score pixels are from a different source')
        return data['pixels'], data['frames'], data['times'], source['sha256']


def blue_fraction(pixels):
    # The panel behind white digits is dark blue in the fixed broadcast layout.
    b, g, r = [pixels[..., i].astype(np.int16) for i in range(3)]
    return np.mean((b > r + 14) & (b > g + 3) & (b > 55), axis=(-2, -1))


def mask(pixels):
    return cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY) > 150


def calibrate(pixels, states):
    values = [sorted({state[side] for state in states if state is not None}) for side in (0, 1)]
    templates = []
    example_indices = []
    for side in (0, 1):
        side_templates = []
        side_indices = []
        for value in values[side]:
            indices = [i for i, state in enumerate(states) if state is not None and state[side] == value]
            # Prefer the longest stable run, then its middle frame.
            runs = []
            current = [indices[0]]
            for index in indices[1:]:
                if index == current[-1] + 1:
                    current.append(index)
                else:
                    runs.append(current)
                    current = [index]
            runs.append(current)
            chosen = max(runs, key=len)[len(max(runs, key=len)) // 2]
            side_indices.append(chosen)
            side_templates.append(mask(pixels[chosen, side]))
        templates.append(np.stack(side_templates))
        example_indices.append(side_indices)
    return values, templates, example_indices


def infer(pixels, values, templates, error_threshold):
    readings = []
    for i, sample in enumerate(pixels):
        fractions = blue_fraction(sample)
        score = []
        margins = []
        errors = []
        for side in (0, 1):
            observed = mask(sample[side])
            distances = np.mean(templates[side] != observed, axis=(1, 2))
            order = np.argsort(distances)
            score.append(int(values[side][order[0]]))
            errors.append(float(distances[order[0]]))
            margins.append(float(distances[order[1]] - distances[order[0]]))
        visible = max(errors) <= error_threshold
        readings.append({'score': score if visible else None, 'panel_blue_fraction': fractions.tolist(),
                         'template_error': errors, 'template_margin': margins,
                         'status': 'automatic_template_read' if visible else 'graphic_not_detected'})
    return readings


def build_timeline(readings, times):
    runs = []
    for index, reading in enumerate(readings):
        state = reading['score']
        if runs and runs[-1]['state'] == state:
            runs[-1]['last'] = index
        else:
            runs.append({'state': state, 'first': index, 'last': index})
    groups = []
    group = []
    for run in runs:
        if run['state'] is None:
            if group:
                groups.append(group)
                group = []
        else:
            group.append(run)
    if group:
        groups.append(group)
    points = []
    corrections = []
    for set_number, group in enumerate(groups, 1):
        if set_number == 1 and group[0]['state'] == [1, 0]:
            points.append({'set': 1, 'point_number': 1, 'score_before': '0-0',
                           'score_after': '1-0', 'winner': 'ProVolley',
                           'evidence': 'first_visible_score_only'})
        for index in range(1, len(group)):
            before, after = group[index - 1]['state'], group[index]['state']
            if index + 1 < len(group) and group[index + 1]['state'] == before:
                corrections.append({'set': set_number, 'from': before, 'temporary': after,
                                    'restored': before, 'visible_from_s': float(times[group[index]['first']])})
                continue
            if index >= 2 and group[index - 2]['state'] == after:
                continue  # Return from a temporary graphic correction.
            delta = [after[0] - before[0], after[1] - before[1]]
            if delta not in ([1, 0], [0, 1]):
                raise RuntimeError(f'Non-point score change in set {set_number}: {before} -> {after}')
            points.append({'set': set_number, 'point_number': sum(after),
                           'score_before': f'{before[0]}-{before[1]}',
                           'score_after': f'{after[0]}-{after[1]}',
                           'winner': 'ProVolley' if delta == [1, 0] else 'UTS',
                           'evidence': 'automatic_broadcast_score_transition',
                           'graphic_change_after_s': float(times[group[index - 1]['last']]),
                           'graphic_change_by_s': float(times[group[index]['first']])})
        if set_number == 1 and group[-1]['state'] == [24, 15]:
            points.append({'set': 1, 'point_number': 40, 'score_before': '24-15',
                           'score_after': '25-15', 'winner': 'ProVolley',
                           'evidence': 'inferred_set_winning_point_not_visible_score'})
    summaries = []
    for set_number, group in enumerate(groups, 1):
        subset = [point for point in points if point['set'] == set_number]
        runs = [(winner, len(list(items))) for winner, items in
                groupby(point['winner'] for point in subset)]
        summaries.append({'set': set_number, 'final_score': subset[-1]['score_after'],
                          'point_count': len(subset),
                          'provolley_points': sum(point['winner'] == 'ProVolley' for point in subset),
                          'uts_points': sum(point['winner'] == 'UTS' for point in subset),
                          'longest_provolley_point_run': max(length for winner, length in runs if winner == 'ProVolley'),
                          'longest_uts_point_run': max(length for winner, length in runs if winner == 'UTS'),
                          'score_status': 'inferred_from_set_transition' if set_number == 1 else 'visible_on_broadcast'})
    return {'set_count': len(groups), 'point_count': len(points), 'set_summaries': summaries,
            'score_corrections': corrections, 'points': points}


def audit_between_samples(values, templates, threshold):
    changes = json.loads(FLIPS.read_text(encoding='utf-8'))['changes']
    cap = cv2.VideoCapture(str(VIDEO))
    results = []
    try:
        for change in changes:
            frame_number = change['first_new_digit_frame'] + 25
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f'Cannot decode holdout frame {frame_number}')
            pixels = np.stack([crop(frame, TOP), crop(frame, BOTTOM)])[None]
            reading = infer(pixels, values, templates, threshold)[0]
            expected = [int(value) for value in change['score_after'].split('-')]
            results.append({'set': change['set'], 'point_number': change['point_number'],
                            'frame': frame_number, 'expected_score': expected,
                            'automatic_score': reading['score'],
                            'agrees': reading['score'] == expected,
                            'template_error': reading['template_error']})
    finally:
        cap.release()
    return {'method': 'Read 25 frames after each of 121 previously located graphic flips; these pixels were not calibration templates. Flip locations and expected scores come from the reviewed timeline, so this remains same-video validation.',
            'count': len(results), 'agreement_count': sum(item['agrees'] for item in results),
            'mismatches': [item for item in results if not item['agrees']],
            'checks': results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reextract', action='store_true')
    parser.add_argument('--calibrate', action='store_true', help='Build the template bank from one reviewed sample per displayed score value')
    parser.add_argument('--audit', action='store_true', help='Compare automatic readings with the saved reviewed score timeline')
    parser.add_argument('--check-flips', action='store_true')
    args = parser.parse_args()
    if args.reextract and PATCHES.exists():
        PATCHES.unlink()
    pixels, frames, times, source_hash = load_patches()
    calibration = None
    if args.calibrate:
        states = json.loads(REFERENCE.read_text(encoding='utf-8'))['states']
        assert len(states) == len(pixels)
        values, templates, example_indices = calibrate(pixels, states)
        visible = np.array([s is not None for s in states])
        best_errors = np.empty((len(pixels), 2), dtype=np.float32)
        for i, sample in enumerate(pixels):
            for side in (0, 1):
                best_errors[i, side] = np.min(np.mean(templates[side] != mask(sample[side]), axis=(1, 2)))
        visible_ceiling = float(np.max(np.max(best_errors[visible], axis=1)))
        hidden_floor = float(np.min(np.max(best_errors[~visible], axis=1)))
        if visible_ceiling >= hidden_floor:
            raise RuntimeError('Visible and hidden score patches do not separate cleanly')
        threshold = (visible_ceiling + hidden_floor) / 2
        calibration = {'visible_error_ceiling': visible_ceiling, 'hidden_error_floor': hidden_floor}
        np.savez_compressed(TEMPLATES, top_values=np.array(values[0]), bottom_values=np.array(values[1]),
                            top_masks=templates[0], bottom_masks=templates[1],
                            top_example_indices=np.array(example_indices[0]),
                            bottom_example_indices=np.array(example_indices[1]),
                            error_threshold=np.array(threshold), source_sha256=np.array(source_hash))
    if not TEMPLATES.exists():
        raise RuntimeError('Score templates are missing; run once with --calibrate')
    with np.load(TEMPLATES) as bank:
        if str(bank['source_sha256']) != source_hash:
            raise RuntimeError('Score templates are from a different source')
        values = [bank['top_values'], bank['bottom_values']]
        templates = [bank['top_masks'], bank['bottom_masks']]
        example_indices = [bank['top_example_indices'].tolist(), bank['bottom_example_indices'].tolist()]
        threshold = float(bank['error_threshold'])
    readings = infer(pixels, values, templates, threshold)
    output = {'match_id': 'yt_FqE5pTJqx8g', 'source_sha256': source_hash,
              'method': 'Fixed-layout nearest binary score-patch template with a template-error gate; one reviewed calibration frame per displayed value. Inference does not read the reviewed score sequence.',
              'reference_use': 'One reviewed frame per score value calibrated the fixed template bank. Optional --audit compares predictions to the saved states; this is not an independent new-video accuracy estimate.',
              'template_error_threshold': threshold,
              'template_example_indices': {'top': example_indices[0], 'bottom': example_indices[1]},
              'sample_count': len(readings),
              'readings': [dict(sample_index=i, frame=int(frames[i]), time_s=float(times[i]), **reading)
                           for i, reading in enumerate(readings)]}
    if calibration:
        output['calibration'] = calibration
    if args.audit:
        states = json.loads(REFERENCE.read_text(encoding='utf-8'))['states']
        disagreements = [i for i, (reading, state) in enumerate(zip(readings, states))
                         if reading['score'] != state]
        output['reviewed_state_audit'] = {'count': len(states),
                                          'agreement_count': len(states) - len(disagreements),
                                          'disagreement_indices': disagreements}
    if args.check_flips:
        output['between_sample_audit'] = audit_between_samples(values, templates, threshold)
    OUTPUT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    timeline = build_timeline(readings, times)
    timeline.update(match_id='yt_FqE5pTJqx8g', source_sha256=source_hash,
                    score_source='automatic_template_readings_with_explicit_opening_and_missing_final_point_inferences',
                    timing_note='Graphic changes are not rally contacts or boundaries.')
    TIMELINE_OUTPUT.write_text(json.dumps(timeline, indent=2) + '\n', encoding='utf-8')
    fields = ['set', 'point_number', 'score_before', 'score_after', 'winner', 'evidence',
              'graphic_change_after_s', 'graphic_change_by_s']
    with CSV_OUTPUT.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(timeline['points'])
    observed = [(p['set'], p['score_before'], p['score_after'], p['winner']) for p in timeline['points']]
    print(f"Automatic point sequence: {len(observed)} points, {timeline['set_count']} sets, {len(timeline['score_corrections'])} broadcast correction")
    if args.audit:
        reference_points = json.loads((ROOT / 'data/processed/fqe_score_timeline.json').read_text(encoding='utf-8'))['points']
        expected = [(p['set'], p['score_before'], p['score_after'], p['winner']) for p in reference_points]
        print(f"Reviewed-state agreement: {output['reviewed_state_audit']['agreement_count']}/{len(readings)}; point-sequence agreement: {observed == expected}")
    if args.check_flips:
        audit = output['between_sample_audit']
        print(f"Between-sample score reads: {audit['agreement_count']}/{audit['count']} agree; first mismatches: {audit['mismatches'][:5]}")
    print(f'Template-error threshold {threshold:.3f}')


if __name__ == '__main__':
    main()
