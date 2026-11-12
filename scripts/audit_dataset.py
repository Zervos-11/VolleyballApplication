#!/usr/bin/env python3
"""Inventory existing Week 6 evidence without modifying source annotations or metadata."""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from .annotation_qc import run_checks
except ImportError:
    from annotation_qc import run_checks


def audit(root, output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    sources = defaultdict(list)
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        report = run_checks(directory, directory / 'annotations_pilot.csv',
                            output / f'{directory.name}_qc_report.json')
        info = report['measured_video'] or {}
        filename = info.get('file', '')
        source_hint = Path(filename).stem.removeprefix('youtube_') if filename.startswith('youtube_') else ''
        if source_hint:
            sources[source_hint].append(directory.name)
        records.append({
            'match_id': directory.name, 'video_file': filename,
            'source_id_hint': source_hint,
            'width': info.get('width', ''), 'height': info.get('height', ''),
            'fps': info.get('fps', ''), 'frame_count': info.get('frame_count', ''),
            'meets_resolution_rule': bool(info and info['width'] >= 1280 and info['height'] >= 720),
            'meets_fps_rule': bool(info and info['fps'] >= 25),
            'annotation_rows': report['rows_checked'],
            'review_provenance_rows': report['review_provenance_rows'],
            'qc_errors': report['errors'], 'structural_status': report['structural_status'],
            'eligibility': 'pending_manual_screening', 'rights_status': 'not_recorded_in_audit',
        })
    if records:
        with (output / 'dataset_inventory.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    summary = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'match_folders': len(records),
        'folders_with_readable_video': sum(bool(r['video_file']) for r in records),
        'annotation_rows': sum(r['annotation_rows'] for r in records),
        'review_provenance_rows': sum(r['review_provenance_rows'] for r in records),
        'folders_passing_structural_qc': sum(r['structural_status'] == 'pass' for r in records),
        'possible_duplicate_sources': {k: v for k, v in sources.items() if len(v) > 1},
        'limitations': [
            'Source hints come from filenames; confirm source URLs and parent matches manually.',
            'Video properties come from the decoder; constant frame rate is not independently verified.',
            'No label accuracy, consent, licence or independent review is inferred from file existence.',
            'Legacy annotations_pilot.csv files are audited; reviewed releases must be checked separately.',
        ],
    }
    (output / 'dataset_audit.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('data/matches'))
    parser.add_argument('--out', type=Path, default=Path('data/processed/week6_audit'))
    args = parser.parse_args()
    audit(args.root, args.out)
