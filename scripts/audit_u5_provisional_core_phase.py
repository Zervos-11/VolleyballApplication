"""Record source-visible phase failures in the anonymous six-box core screen.

This is a small, single-reviewer counterexample audit, not exhaustive phase QC.
"""
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
CANDIDATES = BASE / 'cut_bounded_provisional_rally_metrics.json'
REVIEW = BASE / 'provisional_core_review'
OUT = BASE / 'provisional_core_phase_counterexamples.json'

# Reviewed on the source-image contact sheets. Frame numbers are exact 30 fps
# source positions; no automatic phase label is inferred from these examples.
DECISIONS = (
    (2, 26, 19152, 'after_point', 'Players have gathered at the net after the exchange.'),
    (2, 28, 19500, 'before_serve', 'Near-side players are in static serve-receive formation before the serve.'),
    (2, 28, 19584, 'after_point', 'Players are walking and regrouping after the exchange.'),
    (3, 34, 36174, 'after_point', 'Line judge has raised the flag and players are dispersing.'),
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    candidates = json.loads(CANDIDATES.read_text(encoding='utf-8'))
    review = json.loads((REVIEW / 'index.json').read_text(encoding='utf-8'))
    if review['metrics_sha256'] != digest(CANDIDATES):
        raise ValueError('Review sheets do not match the candidate screen')
    if review['source_sha256'] != candidates['source_sha256']:
        raise ValueError('Source video differs')
    point_lookup = {(r['set'], r['point_number']): r for r in candidates['points']}
    sheet_lookup = {}
    for page in review['pages']:
        if digest(REVIEW / page['path']) != page['sha256']:
            raise ValueError(f"Review sheet changed: {page['path']}")
        for point in page['points']:
            sheet_lookup[point['set'], point['point_number']] = page
    rows = []
    for set_no, point_no, frame_no, phase, evidence in DECISIONS:
        point = point_lookup[set_no, point_no]
        if frame_no not in {f['source_frame'] for f in point['frames']}:
            raise ValueError(f'Counterexample missing from candidates: {(set_no, point_no, frame_no)}')
        page = sheet_lookup[set_no, point_no]
        rows.append({'set': set_no, 'point_number': point_no,
                     'source_frame': frame_no, 'source_second': round(frame_no / 30, 3),
                     'source_visible_phase': phase, 'visual_evidence': evidence,
                     'review_sheet': page['path'], 'review_sheet_sha256': page['sha256']})
    result = {
        'status': 'single_reviewer_source_visible_counterexamples_not_exhaustive_phase_review',
        'source_sha256': candidates['source_sha256'],
        'candidate_screen_sha256': digest(CANDIDATES),
        'review_index_sha256': digest(REVIEW / 'index.json'),
        'candidate_frames': candidates['summary']['provisional_candidate_frames'],
        'confirmed_non_live_candidate_frames': len(rows),
        'distinct_affected_points': len({(r['set'], r['point_number']) for r in rows}),
        'decision': 'Quarantine clip-wide and winner-stratified medians; inspected counterexamples prove the current gate admits non-live frames.',
        'limitations': 'Only these four illustrated frames were phase-adjudicated here; the other candidate frames have not been cleared.',
        'counterexamples': rows,
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Confirmed {len(rows)} non-live candidates in {result['distinct_affected_points']} points")


if __name__ == '__main__':
    main()
