"""Source-bind one short six-player UCLA identity run in set 1 point 37."""
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/matches/yt_u5HnY2aNW14/screening'
TRACKS = BASE / 'dense_live_track_screen.json'
GALLERY = BASE / 's1p37_replacement_review/index.json'
QC = BASE / 'bracketed_candidate_source_qc.json'
OUT = BASE / 's1p37_short_identity_run.json'
ROSTER = {2: 'UCLA_libero_28', 3: 'UCLA_19', 4: 'UCLA_21',
          9: 'UCLA_1', 11: 'UCLA_7', 18: 'UCLA_12'}
FRAMES = list(range(10476, 10531, 6))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracks = json.loads(TRACKS.read_text(encoding='utf-8'))
    gallery = json.loads(GALLERY.read_text(encoding='utf-8'))
    qc = json.loads(QC.read_text(encoding='utf-8'))
    if not (tracks['source_sha256'] == gallery['source_sha256'] == qc['source_sha256']):
        raise ValueError('Source video differs')
    for page in gallery['pages']:
        if sha(GALLERY.parent / page['path']) != page['sha256']:
            raise ValueError('Gallery page changed')
    if not set(FRAMES) <= {f for page in gallery['pages'] for f in page['frames']}:
        raise ValueError('Reviewed gallery does not show entire run')
    selected = next(r for r in qc['rows'] if (r['set'], r['point_number']) == (1, 37))
    if selected['source_frame'] != 10488:
        raise ValueError('Current source-reviewed local candidate changed')
    point = next(p for p in tracks['points'] if (p['set'], p['point_number']) == (1, 37))
    rows = {r['source_frame']: r for r in point['rows']}
    previous = None
    displacements = []
    for frame in FRAMES:
        candidates = [p for p in rows[frame]['proposals']
                      if p['net_side_status'] == 'near_floor_side_candidate']
        if {p['raw_track_id'] for p in candidates} != set(ROSTER):
            raise ValueError(f'Roster mismatch at frame {frame}')
        current = {p['raw_track_id']: p['box_bottom_court_m'] for p in candidates}
        if previous is not None:
            displacements.extend(math.dist(current[i], previous[i]) for i in ROSTER)
        previous = current
    result = {
        'status': 'single_reviewer_short_source_identity_run_not_whole_rally_or_floor_validation',
        'source_sha256': tracks['source_sha256'], 'tracks_sha256': sha(TRACKS),
        'gallery_index_sha256': sha(GALLERY), 'bracketed_qc_sha256': sha(QC),
        'set': 1, 'point_number': 37, 'near_team': 'UCLA',
        'sampled_source_frames': FRAMES, 'sample_rate_hz': 5,
        'duration_between_first_last_sample_s': round((FRAMES[-1] - FRAMES[0]) / 30, 3),
        'source_reviewed_raw_id_to_jersey': {str(k): v for k, v in ROSTER.items()},
        'maximum_consecutive_box_bottom_displacement_m': round(max(displacements), 3),
        'median_consecutive_box_bottom_displacement_m': round(statistics.median(displacements), 3),
        'ground_position_validation': 'pending',
        'interpretation': 'All ten 5 Hz images in the source gallery show the same five blue UCLA players and white libero #28 as near-side players. The detector retains their six raw IDs over this 1.8 s span. Box-bottom movement is a continuity diagnostic, not measured floor displacement. No inference is made for the rest of this point.',
    }
    OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {OUT}: {len(FRAMES)} frames; max step {max(displacements):.3f} m')


if __name__ == '__main__':
    main()
