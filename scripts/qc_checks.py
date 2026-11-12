#!/usr/bin/env python3
"""Validate annotation CSVs against source video, metadata and review provenance."""
import argparse

try:
    from .annotation_qc import run_checks
except ImportError:
    from annotation_qc import run_checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--match_dir', required=True)
    parser.add_argument('--annotations', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--video', help='Explicit source video when multiple MP4s exist')
    args = parser.parse_args()
    report = run_checks(args.match_dir, args.annotations, args.out, args.video)
    print(f"QC {report['structural_status']}: {report['rows_checked']} rows, {report['errors']} errors. {args.out}")
    raise SystemExit(1 if report['errors'] else 0)


if __name__ == '__main__':
    main()
