"""Keep 30-fps person boxes while gating floor positions by source evidence."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review'
SOURCE = PACK / 'completed.csv'
PAIRED = PACK / 'paired_completed.csv'
DETECTOR = PACK / 'exact_30fps_candidates.json'
MANIFEST = PACK / 'manifest.json'
OUT = PACK / 'box_and_floor_ledger.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_S1P6_BOX_AND_FLOOR_LEDGER.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    detection = json.loads(DETECTOR.read_text(encoding='utf-8'))
    source = {(int(r['source_frame']), int(r['slot'])): r for r in read_csv(SOURCE)}
    paired = {(int(r['source_frame']), int(r['slot'])): r for r in read_csv(PAIRED)}
    frames = manifest['five_sample_frames']
    assert len(source) == len(paired) == 30
    assert detection['input_sha256']['source_review'] == sha(SOURCE)
    assert all(r['source_review_sha256'] == sha(SOURCE) and
               r['detector_sha256'] == sha(DETECTOR) for r in paired.values())
    # IDs are frozen from the four frames where each source player was both
    # grounded and explicitly paired. Their later occurrence is a candidate,
    # not a new human identity verdict.
    slot_ids = {}
    for slot in range(1, 7):
        observed = {int(paired[(frame, slot)]['raw_track_id']) for frame in frames[:4]
                    if paired[(frame, slot)]['candidate_alignment'] == 'same_player'}
        assert len(observed) == 1
        slot_ids[slot] = observed.pop()
    assert len(set(slot_ids.values())) == 6

    source_frames = set(frames)
    ledger = []
    exclusion_open = {slot: False for slot in slot_ids}
    for frame_record in detection['rows']:
        frame = frame_record['source_frame']
        assert manifest['window_start_frame_inclusive'] <= frame < manifest['window_end_frame_exclusive']
        boxes = {d['raw_track_id']: d for d in frame_record['detections']}
        players = []
        for slot, raw_id in slot_ids.items():
            box = boxes.get(raw_id)
            reviewed = source.get((frame, slot)) if frame in source_frames else None
            pair = paired.get((frame, slot)) if reviewed else None
            if reviewed and reviewed['ground_status'] == 'airborne':
                exclusion_open[slot] = True
            elif reviewed and reviewed['ground_status'] == 'grounded':
                exclusion_open[slot] = False
            source_ground_status = reviewed['ground_status'] if reviewed else 'unreviewed'
            accepted = bool(reviewed and pair and box and
                            reviewed['ground_status'] == 'grounded' and
                            pair['candidate_alignment'] == 'same_player' and
                            pair['floor_alignment'] == 'plausible' and
                            int(pair['raw_track_id']) == raw_id)
            bbox = box['bbox_px'] if box else None
            players.append({
                'slot': slot,
                'candidate_raw_track_id': raw_id,
                'candidate_bbox_px': bbox,
                'candidate_box_center_px': None if bbox is None else
                    [round((bbox[0] + bbox[2]) / 2, 2), round((bbox[1] + bbox[3]) / 2, 2)],
                'candidate_box_bottom_px': None if bbox is None else
                    [round((bbox[0] + bbox[2]) / 2, 2), bbox[3]],
                'candidate_identity_status': 'paired_same_player' if pair and
                    pair['candidate_alignment'] == 'same_player' else 'raw_id_continuity_only',
                'source_ground_status': source_ground_status,
                'airborne_exclusion_open_until_reviewed_ground_contact': exclusion_open[slot],
                'reviewed_grounded_box_bottom_proxy_px':
                    [round((bbox[0] + bbox[2]) / 2, 2), bbox[3]] if accepted else None,
                'reviewed_shoe_px': [float(reviewed['shoe_x_px']), float(reviewed['shoe_y_px'])]
                    if accepted else None,
                'metric_approved_court_position_m': None,
            })
        ledger.append({'source_frame': frame, 'planned_sample': frame in source_frames,
                       'players': players,
                       'complete_reviewed_grounded_proxy_frame': all(
                           p['reviewed_grounded_box_bottom_proxy_px'] is not None for p in players)})
    assert len(ledger) == 25 and [r['source_frame'] for r in ledger] == list(range(1759, 1784))
    slots = [p for r in ledger for p in r['players']]
    assert len(slots) == 150
    summary = {'candidate_boxes': sum(p['candidate_bbox_px'] is not None for p in slots),
               'reviewed_grounded_proxy_slots': sum(p['reviewed_grounded_box_bottom_proxy_px'] is not None for p in slots),
               'reviewed_airborne_slots': sum(p['source_ground_status'] == 'airborne' for p in slots),
               'unreviewed_ground_slots': sum(p['source_ground_status'] == 'unreviewed' for p in slots),
               'complete_reviewed_grounded_sample_frames': sum(r['complete_reviewed_grounded_proxy_frame'] for r in ledger),
               'metric_approved_court_positions': 0,
               'source_ground_status_counts': dict(Counter(p['source_ground_status'] for p in slots))}
    assert summary['candidate_boxes'] == 150
    assert summary['reviewed_grounded_proxy_slots'] == 28
    assert summary['reviewed_airborne_slots'] == 2
    assert summary['unreviewed_ground_slots'] == 120
    assert summary['complete_reviewed_grounded_sample_frames'] == 4
    result = {'status': 'candidate_box_continuity_separated_from_floor_eligibility',
              'input_sha256': {'manifest': sha(MANIFEST), 'source_review': sha(SOURCE),
                               'paired_review': sha(PAIRED), 'detector': sha(DETECTOR)},
              'source_frame_first': 1759, 'source_frame_last': 1783,
              'slot_to_candidate_raw_id': {str(k): v for k, v in slot_ids.items()},
              'floor_rule': 'Keep every available candidate box and raw ID. Accept a floor proxy only at an explicitly source-reviewed grounded frame with a same-player/plausible paired verdict. At an airborne frame and thereafter, leave the floor point null until a later reviewed grounded contact; unreviewed frames are null regardless.',
              'calibration_status': 'not_approved_for_strict_metric_use',
              'strict_metric_approval': False, 'summary': summary, 'rows': ledger}
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    REPORT.write_text('\n'.join([
        '# S1 P6 box continuity and floor eligibility', '',
        'The [25-frame ledger](../data/matches/yt_u5HnY2aNW14/screening/s1p6_fixed_window_source_review/box_and_floor_ledger.json) '
        'keeps six candidate raw-ID boxes on every source frame from 1759 through 1783: '
        f'**{summary["candidate_boxes"]}/150** frame-player slots. The six IDs were established from '
        'the four human-paired grounded samples; presence of those IDs between samples is '
        'candidate continuity, not a human identity verdict on every frame.', '',
        'Floor eligibility is a separate field. The source and paired forms support '
        f'**{summary["reviewed_grounded_proxy_slots"]}/150** grounded box-bottom proxy slots at '
        'the planned samples and **four** samples eligible for a six-player floor metric. '
        'All five planned samples have six source-reviewed player states. The two blockers '
        'at frame 1783 are source-reviewed **airborne**: their candidate boxes remain in the '
        'ledger, but both reviewed floor-proxy values are **null**. The intervening '
        f'**{summary["unreviewed_ground_slots"]}** player slots have unreviewed ground contact and '
        'also carry null reviewed floor positions. A future extension would keep an airborne '
        'floor exclusion open until a reviewed grounded contact closes it; the current window '
        'ends at frame 1783.', '',
        'No box bottom is silently used as a court position during a jump. A carried-forward '
        'takeoff location could be analysed as a separately labelled imputation scenario, as '
        '[shown here](HONOURS_U5_S1P6_BLOCK_TAKEOFF_SENSITIVITY.md), but it is not an observed '
        'frame-1783 floor point. A later out-of-point court-line check passed its operational '
        'screen, but this ledger still carries no formal strict metric-use approval. The '
        'airborne final sample is a valid state observation with an undefined six-player '
        'floor metric; the 20 intervening source frames also lack ground-contact review.', '',
        'Reproduce with `.\\.venv\\Scripts\\python.exe scripts/build_u5_s1p6_box_and_floor_ledger.py`.',
    ]) + '\n', encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    main()
