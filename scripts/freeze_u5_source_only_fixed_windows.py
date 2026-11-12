"""Freeze deterministic live-interior windows before evaluating their tracking."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
SAMPLE = SCREEN / 'rally_sample_score_only.json'
SOURCE_QC = SCREEN / 'event_transition_source_qc.json'
OUTPUT = SCREEN / 'source_only_fixed_window_protocol.json'
REPORT = ROOT / 'DELIVERABLES/HONOURS_U5_SOURCE_ONLY_FIXED_WINDOWS.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(f'Frozen protocol already exists: {OUTPUT}')
    sample = json.loads(SAMPLE.read_text(encoding='utf-8'))
    source = json.loads(SOURCE_QC.read_text(encoding='utf-8'))
    assert sample['source_sha256'] == source['source_sha256']
    by_point = {(int(row['set']), int(row['point_number'])): row for row in source['points']}
    assert len(by_point) == 18 == len(sample['selected_events'])
    rows = []
    for selected in sample['selected_events']:
        key = (int(selected['set']), int(selected['point_number']))
        q = by_point[key]
        start = int(q['conservative_interior_start_frame_inclusive'])
        end = int(q['conservative_interior_end_frame_exclusive'])
        length = end - start
        if length >= 25:
            centre = (start + end - 1) // 2
            window_start = centre - 12
            window_end = centre + 13
            assert start <= window_start < window_end <= end
            frames = list(range(window_start, window_end, 6))
            assert len(frames) == 5 and frames[-1] == window_end - 1
            status = 'frozen_source_navigation_window_pending_frame_review'
        else:
            window_start = window_end = None
            frames = []
            status = 'no_25_frame_window_in_conservative_source_interior'
        rows.append({
            'set': key[0], 'point_number': key[1],
            'winner_scoreboard_side': selected['winner_scoreboard_side'],
            'conservative_interior_start_frame_inclusive': start,
            'conservative_interior_end_frame_exclusive': end,
            'conservative_interior_length_frames': length,
            'window_start_frame_inclusive': window_start,
            'window_end_frame_exclusive': window_end,
            'five_sample_frames': frames,
            'status': status,
            'source_live_phase_certified': False,
            'tracking_or_grounding_certified': False,
        })
    result = {
        'status': 'frozen_source_only_fixed_window_selection_pending_source_frame_review',
        'source_sha256': sample['source_sha256'],
        'input_sha256': {'score_only_sample': sha(SAMPLE), 'source_transition_qc': sha(SOURCE_QC)},
        'selection_rule': ('For each of the 18 score-frozen points, take 25 consecutive source '
                           'frames centred on the arithmetic midpoint of its previously '
                           'source-reviewed conservative live-looking interior; choose the '
                           'earlier centre frame for an even-length interior. If fewer than '
                           '25 frames are available, retain the point as ineligible. Sample '
                           'frames at offsets 0, 6, 12, 18, 24 within each window.'),
        'prior_exposure_limit': ('Prior detector screens of the same 18 points already exist. '
                                'This deterministic rule uses no detector fields, but the '
                                'protocol cannot be described as prospectively blinded.'),
        'metric_status': 'no_windows_source_certified_or_approved_for_strict_metric_input',
        'rows': rows,
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    eligible = [row for row in rows if row['five_sample_frames']]
    excluded = [f"S{row['set']} P{row['point_number']} ({row['conservative_interior_length_frames']} frames)"
                for row in rows if not row['five_sample_frames']]
    REPORT.write_text('\n'.join([
        '# Source-only fixed-window selection for the frozen U5 sample', '',
        'The [machine-readable protocol](../data/matches/yt_u5HnY2aNW14/screening/source_only_fixed_window_protocol.json) '
        'applies one deterministic rule to all 18 score-frozen points. It uses the earlier '
        'source-only conservative live-looking interior, not detector availability. Each '
        'eligible window has 25 consecutive 30-fps frames (0.8 seconds from first to last) '
        'and five planned metric samples six frames apart.', '',
        f'**Selection result:** {len(eligible)}/18 points have a 25-frame interior. '
        f'The remaining point is {", ".join(excluded)}. These points remain in the denominator.', '',
        'This selection was frozen after previous detector screens of these points existed; '
        'it is rule-based and does not read those screens, but it is not prospectively blinded. '
        'The conservative intervals are navigation evidence only. Exact serve/end events, '
        'live phase at each sampled instant, jersey identities, grounded positions and court '
        'mapping for metric use must still be source-reviewed. Every window remains unapproved.', '',
        'The next source review target is S1 P6, the first eligible frozen point after the '
        'two previously deeply audited points (S1 P5 and S3 P34). This review order is an '
        'efficiency choice, not a change to the all-point selection rule or an outcome sample.', '',
        'Reproduce only by verifying the frozen JSON against its two input hashes; the script '
        'refuses to overwrite an existing protocol.',
    ]) + '\n', encoding='utf-8')
    print(f'Frozen {len(eligible)}/18 windows; next S1 P6 {next(row["five_sample_frames"] for row in rows if (row["set"], row["point_number"]) == (1, 6))}')


if __name__ == '__main__':
    main()
